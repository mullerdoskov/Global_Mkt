"""
tests/test_api_smoke.py
Smoke tests da API — ISSUE-006.

Cobertura: 1 teste de caminho feliz por endpoint da `api_router` + health + root.
Para 4 endpoints com parâmetros de path (`{symbol}`), também valida o caminho
de erro 404 quando o ativo/empresa não existe.

Estratégia de mock:
- `get_session()` é patched por módulo (cada arquivo `backend/api/*.py` importa
  `get_session` localmente). O mock devolve uma `MagicMock` cuja `.execute(...)`
  é configurada com `side_effect` na ordem exata em que o handler chama.
- Para `/api/market/summary`, `INDICES` é patched para reduzir o loop de 16 para
  2 entradas (os asserts continuam válidos para o schema).
- Sem dependência de PostgreSQL — todos os testes rodam contra o `TestClient`
  com banco SQLite definido em `conftest.py`.
"""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _result(scalar=None, scalar_one_or_none=None, fetchall_rows=None,
            scalars_all=None):
    """
    Cria um MagicMock que se comporta como sqlalchemy Result.
    Cada chamada `session.execute(...)` no handler espera um destes formatos
    de retorno; este helper monta exatamente um deles.
    """
    r = MagicMock()
    r.scalar.return_value = scalar
    r.scalar_one_or_none.return_value = scalar_one_or_none
    r.fetchall.return_value = fetchall_rows or []
    scalars_proxy = MagicMock()
    scalars_proxy.all.return_value = scalars_all or []
    r.scalars.return_value = scalars_proxy
    return r


def _session_with_results(*results):
    """Sessão MagicMock cujo .execute() retorna `results` em ordem."""
    s = MagicMock()
    s.execute.side_effect = list(results)
    return s


def _asset(symbol="PETR4.SA", name="Petrobras", asset_type_value="stock",
           currency="BRL", exchange="B3", is_active=True, asset_id=1,
           company_id=10):
    """Mock de objeto Asset com os atributos lidos pelos handlers."""
    return SimpleNamespace(
        id=asset_id,
        symbol=symbol,
        name=name,
        asset_type=SimpleNamespace(value=asset_type_value),
        currency=currency,
        exchange=exchange,
        is_active=is_active,
        company_id=company_id,
    )


def _company(company_id=10, ticker="PETR4.SA", name="Petrobras SA",
             country_id=1, sector_gics_id=1, market_cap=500_000_000_000,
             employees=45000, currency="BRL", exchange="B3"):
    return SimpleNamespace(
        id=company_id, ticker=ticker, name=name, country_id=country_id,
        sector_gics_id=sector_gics_id, market_cap=market_cap,
        employees=employees, currency=currency, exchange=exchange,
    )


def _country(country_id=1, iso2="BR", iso3="BRA", name="Brazil"):
    return SimpleNamespace(id=country_id, iso2=iso2, iso3=iso3, name=name)


def _sector(sector_id=1, sector="Energy", sector_pt="Energia"):
    return SimpleNamespace(id=sector_id, sector=sector, sector_pt=sector_pt)


def _price(asset_id=1, the_date=None, close=35.50, open_=35.0, high=36.0,
           low=34.5, adj_close=35.50, volume=10_000_000):
    return SimpleNamespace(
        asset_id=asset_id,
        date=the_date or date(2026, 4, 25),
        open=open_, high=high, low=low, close=close,
        adj_close=adj_close, volume=volume,
    )


def _financial(period_end=None, currency="BRL"):
    return SimpleNamespace(
        period_end=period_end or date(2026, 3, 31),
        revenue=100_000.0, cost_of_revenue=60_000.0, gross_profit=40_000.0,
        operating_income=20_000.0, ebitda=25_000.0, net_income=15_000.0,
        total_assets=500_000.0, total_liabilities=200_000.0,
        total_equity=300_000.0, cash=50_000.0, total_debt=80_000.0,
        net_debt=30_000.0, operating_cash_flow=22_000.0, capex=8_000.0,
        free_cash_flow=14_000.0, currency=currency,
    )


def _valuation():
    return SimpleNamespace(
        snapshot_date=date(2026, 4, 25),
        pe_ratio=8.5, pb_ratio=1.2, ps_ratio=0.9, ev_ebitda=4.5,
        ev_revenue=1.1, roe=0.18, roa=0.06, gross_margin=0.40,
        operating_margin=0.20, net_margin=0.15, debt_to_equity=0.27,
        current_ratio=1.5, dividend_yield=0.08, payout_ratio=0.5,
        net_debt_ebitda=1.2,
    )


def _ingestion_log(symbol="PETR4.SA", status_value="success", rows=100):
    return SimpleNamespace(
        symbol=symbol,
        ingestion_type="prices",
        status=SimpleNamespace(value=status_value),
        rows_inserted=rows,
        started_at=datetime(2026, 4, 28, 22, 0, 0),
        finished_at=datetime(2026, 4, 28, 22, 0, 5),
        duration_seconds=5.0,
        error_message=None,
    )


# ════════════════════════════════════════════════════════════════════
# HEALTH + ROOT (sem DB)
# ════════════════════════════════════════════════════════════════════

class TestHealthAndRoot:
    def test_health_retorna_200(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data

    def test_root_retorna_200(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Market Platform Unified"
        assert "api_prefix" in data


# ════════════════════════════════════════════════════════════════════
# ASSETS — 3 endpoints
# ════════════════════════════════════════════════════════════════════

class TestAssetsEndpoints:
    def test_list_assets_retorna_200(self):
        session = _session_with_results(
            _result(scalar=2),                        # count
            _result(scalars_all=[_asset(), _asset(symbol="VALE3.SA", name="Vale", asset_id=2, company_id=11)]),
        )
        with patch("backend.api.assets.get_session", return_value=session):
            r = client.get("/api/assets")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["assets"]) == 2
        assert data["assets"][0]["symbol"] == "PETR4.SA"
        assert data["assets"][0]["asset_type"] == "stock"

    def test_list_assets_filtra_por_asset_type(self):
        session = _session_with_results(
            _result(scalar=1),
            _result(scalars_all=[_asset(asset_type_value="index", symbol="^BVSP")]),
        )
        with patch("backend.api.assets.get_session", return_value=session):
            r = client.get("/api/assets?asset_type=index&page_size=10")
        assert r.status_code == 200
        data = r.json()
        assert data["page_size"] == 10
        assert data["assets"][0]["asset_type"] == "index"

    def test_search_assets_retorna_200(self):
        session = _session_with_results(
            _result(scalar=1),
            _result(scalars_all=[_asset(symbol="PETR4.SA", name="Petrobras")]),
        )
        with patch("backend.api.assets.get_session", return_value=session):
            r = client.get("/api/assets/search?q=PETR")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["assets"][0]["symbol"] == "PETR4.SA"

    def test_get_asset_detail_retorna_200(self):
        # Sequência: asset (scalar_one_or_none), company, country, sector, latest price
        session = _session_with_results(
            _result(scalar_one_or_none=_asset()),
            _result(scalar_one_or_none=_company()),
            _result(scalar_one_or_none=_country()),
            _result(scalar_one_or_none=_sector()),
            _result(scalar_one_or_none=_price()),
        )
        with patch("backend.api.assets.get_session", return_value=session):
            r = client.get("/api/assets/PETR4.SA")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "PETR4.SA"
        assert data["asset_type"] == "stock"
        assert data["company"]["ticker"] == "PETR4.SA"
        assert data["company"]["country_iso2"] == "BR"
        assert data["company"]["sector"] == "Energy"
        assert data["latest_price"] == 35.50
        assert data["latest_date"] == "2026-04-25"

    def test_get_asset_detail_404_quando_nao_existe(self):
        session = _session_with_results(_result(scalar_one_or_none=None))
        with patch("backend.api.assets.get_session", return_value=session):
            r = client.get("/api/assets/INEXISTENTE")
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
# PRICES — 4 endpoints (history, returns, debug, latest já tem suite própria)
# ════════════════════════════════════════════════════════════════════

class TestPricesEndpoints:
    def test_history_retorna_200(self):
        # Sequência: asset, prices
        session = _session_with_results(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=[
                _price(the_date=date(2026, 4, 23), close=34.0),
                _price(the_date=date(2026, 4, 24), close=35.0),
                _price(the_date=date(2026, 4, 25), close=35.5),
            ]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/PETR4.SA/history?period=30d")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "PETR4.SA"
        assert data["period"] == "30d"
        assert data["interval"] == "1d"
        assert data["count"] == 3
        assert len(data["prices"]) == 3
        assert data["prices"][0]["close"] == 34.0

    def test_history_404_quando_simbolo_nao_existe(self):
        session = _session_with_results(_result(scalar_one_or_none=None))
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/INEXISTENTE/history")
        assert r.status_code == 404

    def test_returns_retorna_200(self):
        session = _session_with_results(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=[
                _price(the_date=date(2026, 4, 23), close=100.0),
                _price(the_date=date(2026, 4, 24), close=105.0),
                _price(the_date=date(2026, 4, 25), close=110.0),
            ]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/PETR4.SA/returns?period=30d")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "PETR4.SA"
        assert data["count"] == 3
        # Primeiro retorno diário é NaN -> None; cumulativo do primeiro é 0.0
        assert data["returns"][0]["daily_return"] is None
        assert data["returns"][0]["cumulative_return"] == 0.0
        assert data["returns"][-1]["cumulative_return"] == pytest.approx(10.0)  # (110/100-1)*100

    def test_returns_404_quando_simbolo_nao_existe(self):
        session = _session_with_results(_result(scalar_one_or_none=None))
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/INEXISTENTE/returns")
        assert r.status_code == 404

    def test_debug_retorna_200(self):
        # Sequência: count assets, count prices, sample rows
        session = _session_with_results(
            _result(scalar=360),
            _result(scalar=30043),
            _result(fetchall_rows=[
                ("PETR4.SA", "Petrobras", "stock", 35.50, date(2026, 4, 25)),
                ("VALE3.SA", "Vale", "stock", 65.00, date(2026, 4, 25)),
            ]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/debug")
        assert r.status_code == 200
        data = r.json()
        assert data["assets_count"] == 360
        assert data["prices_count"] == 30043
        assert len(data["sample"]) == 2
        assert data["sample"][0]["symbol"] == "PETR4.SA"


# ════════════════════════════════════════════════════════════════════
# MARKET — 3 endpoints
# ════════════════════════════════════════════════════════════════════

class TestMarketEndpoints:
    def test_summary_retorna_200(self):
        # Reduz o loop de 16 índices para 2 — schema continua igual.
        # Para cada índice: asset (scalar_one_or_none) + price atual + price anterior
        fake_indices = ["^BVSP", "^GSPC"]
        bvsp_asset = _asset(symbol="^BVSP", name="Ibovespa",
                            asset_type_value="index", asset_id=100)
        bvsp_now = _price(asset_id=100, the_date=date(2026, 4, 25), close=130000.0)
        bvsp_prev = _price(asset_id=100, the_date=date(2026, 4, 24), close=128000.0)
        gspc_asset = _asset(symbol="^GSPC", name="S&P 500",
                            asset_type_value="index", asset_id=101)
        gspc_now = _price(asset_id=101, the_date=date(2026, 4, 25), close=5200.0)
        gspc_prev = _price(asset_id=101, the_date=date(2026, 4, 24), close=5180.0)

        session = _session_with_results(
            _result(scalar_one_or_none=bvsp_asset),
            _result(scalar_one_or_none=bvsp_now),
            _result(scalar_one_or_none=bvsp_prev),
            _result(scalar_one_or_none=gspc_asset),
            _result(scalar_one_or_none=gspc_now),
            _result(scalar_one_or_none=gspc_prev),
        )
        with patch("backend.api.market.get_session", return_value=session), \
             patch("backend.api.market.INDICES", fake_indices):
            r = client.get("/api/market/summary")
        assert r.status_code == 200
        data = r.json()
        assert "as_of" in data
        assert len(data["indices"]) == 2
        assert data["indices"][0]["symbol"] == "^BVSP"
        assert data["indices"][0]["close"] == 130000.0
        assert data["indices"][0]["change_pct"] is not None

    def test_sectors_retorna_200(self):
        # Sequência:
        # 1) sectors (scalars.all)
        # Para cada setor: 2) companies; para cada company: 3) assets;
        # 4) preços (se asset_ids)
        session = _session_with_results(
            _result(scalars_all=[_sector()]),
            _result(scalars_all=[_company()]),
            _result(scalars_all=[_asset()]),
            _result(scalars_all=[
                _price(asset_id=1, the_date=date(2026, 1, 25), close=100.0),
                _price(asset_id=1, the_date=date(2026, 4, 25), close=110.0),
            ]),
        )
        with patch("backend.api.market.get_session", return_value=session):
            r = client.get("/api/market/sectors?period=90d")
        assert r.status_code == 200
        data = r.json()
        assert data["period"] == "90d"
        assert len(data["sectors"]) == 1
        assert data["sectors"][0]["sector"] == "Energy"
        assert data["sectors"][0]["sector_pt"] == "Energia"
        assert data["sectors"][0]["asset_count"] == 1
        assert data["sectors"][0]["avg_return_pct"] == pytest.approx(10.0)  # (110/100-1)*100

    def test_countries_retorna_200(self):
        # Sequência: countries; para cada país: companies; para cada company: count
        session = _session_with_results(
            _result(scalars_all=[_country()]),
            _result(scalars_all=[_company()]),
            _result(scalar=5),
        )
        with patch("backend.api.market.get_session", return_value=session):
            r = client.get("/api/market/countries")
        assert r.status_code == 200
        data = r.json()
        assert data["total_countries"] == 1
        assert data["countries"][0]["country_iso2"] == "BR"
        assert data["countries"][0]["asset_count"] == 5


# ════════════════════════════════════════════════════════════════════
# FUNDAMENTALS — 2 endpoints
# ════════════════════════════════════════════════════════════════════

class TestFundamentalsEndpoints:
    def test_get_financials_retorna_200(self):
        session = _session_with_results(
            _result(scalar_one_or_none=_company()),
            _result(scalars_all=[
                _financial(period_end=date(2026, 3, 31)),
                _financial(period_end=date(2025, 12, 31)),
            ]),
        )
        with patch("backend.api.fundamentals.get_session", return_value=session):
            r = client.get("/api/fundamentals/PETR4.SA")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "PETR4.SA"
        assert data["company_name"] == "Petrobras SA"
        assert len(data["quarters"]) == 2
        # Reverso para ordem cronológica: mais antigo primeiro
        assert data["quarters"][0]["period_end"] == "2025-12-31"
        assert data["quarters"][0]["revenue"] == 100_000.0

    def test_get_financials_404_quando_company_nao_existe(self):
        session = _session_with_results(_result(scalar_one_or_none=None))
        with patch("backend.api.fundamentals.get_session", return_value=session):
            r = client.get("/api/fundamentals/INEXISTENTE")
        assert r.status_code == 404

    def test_get_valuation_retorna_200(self):
        session = _session_with_results(
            _result(scalar_one_or_none=_company()),
            _result(scalar_one_or_none=_valuation()),
        )
        with patch("backend.api.fundamentals.get_session", return_value=session):
            r = client.get("/api/fundamentals/PETR4.SA/valuation")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "PETR4.SA"
        assert data["multiples"]["pe_ratio"] == 8.5
        assert data["multiples"]["net_debt_ebitda"] == 1.2

    def test_get_valuation_sem_dados_retorna_multiples_null(self):
        session = _session_with_results(
            _result(scalar_one_or_none=_company()),
            _result(scalar_one_or_none=None),
        )
        with patch("backend.api.fundamentals.get_session", return_value=session):
            r = client.get("/api/fundamentals/PETR4.SA/valuation")
        assert r.status_code == 200
        assert r.json()["multiples"] is None


# ════════════════════════════════════════════════════════════════════
# INGESTION — 1 endpoint
# ════════════════════════════════════════════════════════════════════

class TestIngestionEndpoints:
    def test_status_retorna_200(self):
        session = _session_with_results(
            _result(scalars_all=[
                _ingestion_log(symbol="PETR4.SA", status_value="success"),
                _ingestion_log(symbol="VALE3.SA", status_value="error"),
                _ingestion_log(symbol="ITUB4.SA", status_value="success"),
            ]),
        )
        with patch("backend.api.ingestion.get_session", return_value=session):
            r = client.get("/api/ingestion/status")
        assert r.status_code == 200
        data = r.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 1
        assert len(data["recent_logs"]) == 3
        assert data["total_assets"] == 3

    def test_status_sem_logs_retorna_200(self):
        session = _session_with_results(_result(scalars_all=[]))
        with patch("backend.api.ingestion.get_session", return_value=session):
            r = client.get("/api/ingestion/status")
        assert r.status_code == 200
        data = r.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 0
        assert data["recent_logs"] == []
        assert data["total_assets"] == 0
        assert data["last_update"] is None
