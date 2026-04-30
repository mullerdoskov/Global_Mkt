"""
tests/test_watchlist.py
Validação dos endpoints `/api/watchlist*` e da dependency `ensure_session` —
ISSUE-018.

Estratégia: usa a engine canônica do conftest (SQLite em arquivo). Antes de
cada teste, garante que o schema completo está criado e limpa as tabelas
de watchlist + user_sessions + assets. O TestClient do FastAPI mantém
cookies entre requests automaticamente, então testar isolamento entre
"usuários" requer dois TestClients distintos.

Não monkeypatcha MARKET_DB_URL: o `from backend.app import app` em outras
suítes já bind-ou o engine canônico via PEP 562, e tentar trocar engines
mid-test cria divergência entre o que o app vê e o que o teste vê.

Cobertura:
1. Cookie de sessão set no 1º request, mantido em requests subsequentes.
2. GET /watchlist com sessão nova → 200 + lista vazia, NUNCA 404.
3. POST /watchlist/{symbol} → 200 + insere; POST de novo → 200 idempotente.
4. POST de symbol inexistente → 404 antes de qualquer escrita.
5. DELETE /watchlist/{symbol} → 204; DELETE de item ausente → 204 idempotente.
6. DELETE de symbol inexistente → 404.
7. Isolamento entre cookies distintos (TestClient1 e TestClient2 não se
   veem).
8. Cookie inválido (UUID malformado) é tratado como ausente — nova session
   gerada.
9. Position é atribuído como max+1 (fim da lista).
10. Wiring: settings expõe os 3 settings novos, router registrado, cookie
    config lida do settings.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _ensure_schema_and_cleanup():
    """Garante schema criado e limpa watchlist+sessions+assets antes/depois.

    Usa a engine canônica que conftest.py configurou. Não troca engines.
    """
    from backend.db.connection import get_engine, get_session
    from backend.db.schema import (
        Base, Asset, WatchlistItem, UserSession,
    )

    engine = get_engine()
    Base.metadata.create_all(engine)

    db = get_session()
    try:
        # Limpar em ordem para respeitar FKs
        db.execute(delete(WatchlistItem))
        db.execute(delete(UserSession))
        db.execute(delete(Asset))
        db.commit()
    finally:
        db.close()

    yield

    db = get_session()
    try:
        db.execute(delete(WatchlistItem))
        db.execute(delete(UserSession))
        db.execute(delete(Asset))
        db.commit()
    finally:
        db.close()


@pytest.fixture
def seeded_assets():
    """Insere 3 assets para testar POST/DELETE/GET com dados reais."""
    from backend.db.connection import get_session
    from backend.db.schema import Asset, AssetType

    db = get_session()
    try:
        db.add_all([
            Asset(symbol="PETR4.SA", asset_type=AssetType.stock, name="Petrobras",
                  currency="BRL", exchange="BVSP"),
            Asset(symbol="AAPL", asset_type=AssetType.stock, name="Apple",
                  currency="USD", exchange="NASDAQ"),
            Asset(symbol="^BVSP", asset_type=AssetType.index, name="Bovespa",
                  currency="BRL", exchange="BVSP"),
        ])
        db.commit()
    finally:
        db.close()
    return ["PETR4.SA", "AAPL", "^BVSP"]


@pytest.fixture
def client():
    """TestClient da app real (cookies preservados entre requests)."""
    from backend.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_factory():
    """Cria múltiplos TestClients do mesmo app — cada um tem cookies próprios."""
    from backend.app import app

    def _factory():
        return TestClient(app)
    return _factory


# ─────────────────────────────────────────────────────────────────────
# Settings / wiring
# ─────────────────────────────────────────────────────────────────────

def test_settings_expose_watchlist_rate_limits():
    from backend.config.settings import settings
    assert settings.rate_limit_watchlist_read
    assert settings.rate_limit_watchlist_write


def test_settings_expose_session_cookie_config():
    from backend.config.settings import settings
    assert settings.session_cookie_name == "mdp_session"
    assert isinstance(settings.session_cookie_secure, bool)
    assert settings.session_cookie_max_age_seconds > 0


def test_router_includes_watchlist():
    from backend.app import app
    routes = {r.path for r in app.routes}
    assert "/api/watchlist" in routes
    assert "/api/watchlist/{symbol}" in routes


# ─────────────────────────────────────────────────────────────────────
# Cookie lifecycle
# ─────────────────────────────────────────────────────────────────────

def test_first_request_sets_session_cookie(client):
    """1º GET sem cookie → 200, cookie 'mdp_session' setado na response."""
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    assert "mdp_session" in resp.cookies
    raw = resp.cookies["mdp_session"]
    uuid.UUID(raw)


def test_subsequent_request_carries_cookie(client):
    """Após o 1º GET, o client envia o mesmo cookie nos próximos requests."""
    r1 = client.get("/api/watchlist")
    cookie1 = r1.cookies.get("mdp_session")
    assert cookie1 is not None

    # No 2º request, o cookie do client deve ser o mesmo
    assert client.cookies.get("mdp_session") == cookie1
    r2 = client.get("/api/watchlist")
    assert r2.status_code == 200


def test_invalid_cookie_yields_new_session(client_factory):
    """Cookie com valor não-UUID dispara criação de nova session."""
    c = client_factory()
    c.cookies.set("mdp_session", "not-a-valid-uuid")
    resp = c.get("/api/watchlist")
    assert resp.status_code == 200
    new_uuid = resp.cookies.get("mdp_session")
    assert new_uuid is not None
    uuid.UUID(new_uuid)
    assert new_uuid != "not-a-valid-uuid"


def test_orphan_cookie_yields_new_session(client_factory):
    """UUID válido mas que não está em user_sessions vira nova session."""
    c = client_factory()
    fake = str(uuid.uuid4())
    c.cookies.set("mdp_session", fake)
    resp = c.get("/api/watchlist")
    assert resp.status_code == 200
    new_uuid = resp.cookies.get("mdp_session")
    assert new_uuid is not None and new_uuid != fake


# ─────────────────────────────────────────────────────────────────────
# GET /api/watchlist
# ─────────────────────────────────────────────────────────────────────

def test_get_watchlist_empty_session_returns_empty_list(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


# ─────────────────────────────────────────────────────────────────────
# POST /api/watchlist/{symbol}
# ─────────────────────────────────────────────────────────────────────

def test_post_adds_asset_to_watchlist(client, seeded_assets):
    resp = client.post("/api/watchlist/PETR4.SA")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["symbol"] == "PETR4.SA"
    assert data["in_watchlist"] is True
    assert data["position"] == 0


def test_post_unknown_symbol_returns_404(client):
    resp = client.post("/api/watchlist/UNKNOWN.XX")
    assert resp.status_code == 404


def test_post_idempotent(client, seeded_assets):
    """POST do mesmo símbolo duas vezes → mesma position, sem duplicação."""
    r1 = client.post("/api/watchlist/AAPL")
    assert r1.status_code == 200
    pos1 = r1.json()["position"]

    r2 = client.post("/api/watchlist/AAPL")
    assert r2.status_code == 200
    assert r2.json()["position"] == pos1

    items = client.get("/api/watchlist").json()["items"]
    assert len(items) == 1
    assert items[0]["symbol"] == "AAPL"


def test_post_assigns_increasing_positions(client, seeded_assets):
    """3 POSTs em sequência → positions 0, 1, 2."""
    r1 = client.post("/api/watchlist/PETR4.SA").json()
    r2 = client.post("/api/watchlist/AAPL").json()
    r3 = client.post("/api/watchlist/^BVSP").json()
    assert (r1["position"], r2["position"], r3["position"]) == (0, 1, 2)


def test_get_returns_items_ordered_by_position(client, seeded_assets):
    client.post("/api/watchlist/^BVSP")
    client.post("/api/watchlist/PETR4.SA")
    client.post("/api/watchlist/AAPL")
    items = client.get("/api/watchlist").json()["items"]
    assert [i["symbol"] for i in items] == ["^BVSP", "PETR4.SA", "AAPL"]
    assert [i["position"] for i in items] == [0, 1, 2]


def test_get_enriches_items_with_asset_metadata(client, seeded_assets):
    client.post("/api/watchlist/AAPL")
    items = client.get("/api/watchlist").json()["items"]
    assert items[0]["name"] == "Apple"
    assert items[0]["asset_type"] == "stock"
    assert items[0]["currency"] == "USD"
    assert items[0]["exchange"] == "NASDAQ"


# ─────────────────────────────────────────────────────────────────────
# DELETE /api/watchlist/{symbol}
# ─────────────────────────────────────────────────────────────────────

def test_delete_removes_item(client, seeded_assets):
    client.post("/api/watchlist/AAPL")
    assert len(client.get("/api/watchlist").json()["items"]) == 1

    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 204
    assert client.get("/api/watchlist").json() == {"items": []}


def test_delete_idempotent_when_item_absent(client, seeded_assets):
    """DELETE de asset que existe mas não está na watchlist → 204."""
    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 204


def test_delete_unknown_symbol_returns_404(client):
    """DELETE de asset desconhecido → 404 (input inválido, não estado)."""
    resp = client.delete("/api/watchlist/UNKNOWN.XX")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────
# Isolamento entre sessões
# ─────────────────────────────────────────────────────────────────────

def test_watchlist_isolated_between_sessions(client_factory, seeded_assets):
    """Dois clients = duas sessions, sem leak."""
    from backend.app import app
    with TestClient(app) as c1, TestClient(app) as c2:
        c1.post("/api/watchlist/AAPL")
        c1.post("/api/watchlist/PETR4.SA")
        c2.post("/api/watchlist/^BVSP")

        items1 = c1.get("/api/watchlist").json()["items"]
        items2 = c2.get("/api/watchlist").json()["items"]

        assert {i["symbol"] for i in items1} == {"AAPL", "PETR4.SA"}
        assert {i["symbol"] for i in items2} == {"^BVSP"}


def test_session_uuids_differ_between_clients(client_factory):
    from backend.app import app
    with TestClient(app) as c1, TestClient(app) as c2:
        r1 = c1.get("/api/watchlist")
        r2 = c2.get("/api/watchlist")
        u1 = r1.cookies.get("mdp_session")
        u2 = r2.cookies.get("mdp_session")
        assert u1 and u2 and u1 != u2


# ─────────────────────────────────────────────────────────────────────
# Persistência via Alembic
# ─────────────────────────────────────────────────────────────────────

def test_alembic_head_creates_watchlist_tables(tmp_path, monkeypatch):
    """Verifica que `alembic upgrade head` cria as 2 tabelas novas.

    Usa banco isolado (igual ao test_alembic_migration.py) — não toca
    no banco canônico.
    """
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    db_file = tmp_path / "alembic_wl.db"
    url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("MARKET_DB_URL", url)

    repo_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))

    command.upgrade(cfg, "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "user_sessions" in tables
        assert "watchlist_items" in tables
    finally:
        engine.dispose()


def test_alembic_round_trip_watchlist(tmp_path, monkeypatch):
    """upgrade head → downgrade base → upgrade head sem warning."""
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    db_file = tmp_path / "alembic_rt.db"
    url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("MARKET_DB_URL", url)

    repo_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert "watchlist_items" in tables
    finally:
        engine.dispose()
