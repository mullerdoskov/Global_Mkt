"""
tests/test_export_csv.py
Validação do endpoint `/api/export/{symbol}.csv` — ISSUE-017.

Cobertura:
1. Caminho feliz (200) — headers CSV corretos, Content-Disposition com filename
   sanitizado, e payload CSV com cabeçalho + linhas em ordem cronológica.
2. Asset inexistente (404) — checagem antes de iniciar o streaming.
3. Período inválido (422) — delegado para o `period_dep`/`parse_period`
   compartilhado com os endpoints de prices.
4. Sem preços no range (200 + CSV de cabeçalho-apenas).
5. Filename sanitizado para símbolos com caracteres especiais (`^BVSP`,
   `BRL=X`).
6. Wiring: rota está registrada na `api_router`, settings expõe
   `rate_limit_export`, e o decorador `@limiter.limit(...)` está aplicado
   referenciando esse setting.
7. Streaming: a resposta é uma `StreamingResponse` (não JSONResponse),
   com `text/csv` no Content-Type.

Estratégia de mock idêntica aos demais smoke tests: `get_session` patched
no módulo `backend.api.export`, retornando `MagicMock` cuja `.execute(...)`
devolve um `_result(...)` em sequência (asset lookup, depois price rows).
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from backend.app import app
from backend.api import export as export_mod
from backend.config.settings import settings


client = TestClient(app)


# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════

def _result(scalar_one_or_none=None, scalars_all=None):
    """Mock de `sqlalchemy Result` cobrindo as 2 formas de leitura usadas
    pelo handler: `.scalar_one_or_none()` (asset lookup) e
    `.scalars().all()` (price rows).
    """
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_one_or_none
    scalars_proxy = MagicMock()
    scalars_proxy.all.return_value = scalars_all or []
    r.scalars.return_value = scalars_proxy
    return r


def _session_with(*results):
    s = MagicMock()
    s.execute.side_effect = list(results)
    return s


def _asset(symbol="PETR4.SA", asset_id=1):
    return SimpleNamespace(id=asset_id, symbol=symbol)


def _price(d, open_=None, high=None, low=None, close=None, adj_close=None, volume=None):
    """Mock de PriceDaily com os atributos que o handler lê."""
    return SimpleNamespace(
        date=d,
        open=open_,
        high=high,
        low=low,
        close=close,
        adj_close=adj_close,
        volume=volume,
    )


# ════════════════════════════════════════════════════════════════════
# 1. CAMINHO FELIZ (200)
# ════════════════════════════════════════════════════════════════════

class TestCsvHappyPath:
    def test_retorna_200_com_csv_correto(self):
        prices = [
            _price(date(2026, 4, 23), open_=Decimal("35.10"), high=Decimal("35.80"),
                   low=Decimal("34.90"), close=Decimal("35.50"),
                   adj_close=Decimal("35.50"), volume=12_345_678),
            _price(date(2026, 4, 24), open_=Decimal("35.50"), high=Decimal("36.20"),
                   low=Decimal("35.40"), close=Decimal("36.00"),
                   adj_close=Decimal("36.00"), volume=14_222_333),
        ]
        session = _session_with(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=prices),
        )

        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/PETR4.SA.csv")

        assert r.status_code == 200
        # Content-Type deve ser text/csv
        assert r.headers["content-type"].startswith("text/csv")
        # Filename atrelado a Content-Disposition (default period=90d)
        assert 'attachment;' in r.headers["content-disposition"]
        assert 'filename="PETR4.SA_90d.csv"' in r.headers["content-disposition"]

        body = r.text
        lines = body.strip().split("\n")
        assert lines[0] == "date,open,high,low,close,adj_close,volume"
        assert lines[1] == "2026-04-23,35.10,35.80,34.90,35.50,35.50,12345678"
        assert lines[2] == "2026-04-24,35.50,36.20,35.40,36.00,36.00,14222333"
        assert len(lines) == 3  # 1 header + 2 rows

    def test_period_custom_aparece_no_filename(self):
        session = _session_with(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=[]),
        )
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/PETR4.SA.csv?period=4w")

        assert r.status_code == 200
        assert 'filename="PETR4.SA_4w.csv"' in r.headers["content-disposition"]

    def test_valores_none_viram_string_vazia(self):
        # Quando o yfinance não traz uma coluna (open/volume), o banco persiste
        # NULL. CSV deve refletir isso como célula vazia, não como "None".
        prices = [
            _price(date(2026, 4, 24), close=Decimal("35.50")),  # outras colunas None
        ]
        session = _session_with(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=prices),
        )
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/PETR4.SA.csv")

        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        # date, "", "", "", close, "", ""
        assert lines[1] == "2026-04-24,,,,35.50,,"


# ════════════════════════════════════════════════════════════════════
# 2. ASSET INEXISTENTE (404)
# ════════════════════════════════════════════════════════════════════

class TestCsv404:
    def test_asset_inexistente_retorna_404(self):
        session = _session_with(_result(scalar_one_or_none=None))

        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/INEXISTENTE.csv")

        assert r.status_code == 404
        body = r.json()
        assert "INEXISTENTE" in body["detail"]
        # E não deve ter Content-Disposition de attachment (não é arquivo)
        # — a checagem é antes do StreamingResponse.
        assert "content-disposition" not in {k.lower() for k in r.headers.keys()} \
            or "attachment" not in r.headers.get("content-disposition", "")

    def test_asset_inexistente_nao_consulta_precos(self):
        # Se o asset lookup retorna None, o handler aborta sem chamar a 2ª query.
        # Garante que `session.execute` foi chamado exatamente 1 vez.
        session = _session_with(_result(scalar_one_or_none=None))

        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/XYZ.csv")

        assert r.status_code == 404
        assert session.execute.call_count == 1


# ════════════════════════════════════════════════════════════════════
# 3. PERÍODO INVÁLIDO (422)
# ════════════════════════════════════════════════════════════════════

class TestCsvPeriodValidation:
    @pytest.mark.parametrize("bad_period", [
        "abc",      # não bate o regex
        "0d",       # quantidade não positiva
        "-1d",      # sinal explícito
        "30",       # falta unidade
        "30dd",     # unidade extra
        "30D",      # maiúscula
        "30 d",     # espaço
        "11y",      # acima do MAX_DAYS (10y)
    ])
    def test_period_invalido_retorna_422(self, bad_period):
        # 422 é levantado pelo `period_dep` *antes* do handler tocar a sessão.
        # Mockar a sessão é defensivo (caso a ordem mude um dia).
        session = _session_with()  # nenhum execute chamado
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get(f"/api/export/PETR4.SA.csv?period={bad_period}")

        assert r.status_code == 422
        # `parse_period` levanta HTTPException(422); FastAPI serializa em JSON.
        body = r.json()
        assert "detail" in body


# ════════════════════════════════════════════════════════════════════
# 4. SEM PREÇOS NO RANGE (200, só header)
# ════════════════════════════════════════════════════════════════════

class TestCsvEmptyRange:
    def test_sem_precos_retorna_csv_apenas_com_header(self):
        session = _session_with(
            _result(scalar_one_or_none=_asset()),
            _result(scalars_all=[]),
        )
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/PETR4.SA.csv")

        assert r.status_code == 200
        body = r.text.strip()
        # Apenas o header — sem trailing newline depois do strip.
        assert body == "date,open,high,low,close,adj_close,volume"


# ════════════════════════════════════════════════════════════════════
# 5. FILENAME SANITIZATION
# ════════════════════════════════════════════════════════════════════

class TestCsvFilenameSanitization:
    def test_simbolo_com_circumflexo_no_filename(self):
        # `^BVSP` deve virar `_BVSP` no filename — `^` não é alfanumérico
        # nem `.`/`_`/`-`.
        session = _session_with(
            _result(scalar_one_or_none=_asset(symbol="^BVSP", asset_id=99)),
            _result(scalars_all=[]),
        )
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/^BVSP.csv")

        assert r.status_code == 200
        assert 'filename="BVSP_90d.csv"' in r.headers["content-disposition"]

    def test_simbolo_com_igual_no_filename(self):
        # `BRL=X` (FX yfinance) também precisa sanitização.
        session = _session_with(
            _result(scalar_one_or_none=_asset(symbol="BRL=X", asset_id=42)),
            _result(scalars_all=[]),
        )
        with patch.object(export_mod, "get_session", return_value=session):
            r = client.get("/api/export/BRL=X.csv")

        assert r.status_code == 200
        # `=` substituído por `_`
        assert 'filename="BRL_X_90d.csv"' in r.headers["content-disposition"]


# ════════════════════════════════════════════════════════════════════
# 6. WIRING
# ════════════════════════════════════════════════════════════════════

class TestCsvWiring:
    def test_settings_expoe_rate_limit_export(self):
        # Default 10/minute — string no vocabulário do `limits`.
        assert isinstance(settings.rate_limit_export, str)
        assert settings.rate_limit_export.endswith("/minute") or \
            settings.rate_limit_export.endswith("/second")
        # Range plausível: 1..30/min. 60+ deixa de cumprir o objetivo de
        # ser "mais agressivo que o default".
        # Aqui só checamos default exato.
        assert settings.rate_limit_export == "10/minute"

    def test_rota_registrada_em_api_router(self):
        # O path absoluto registrado no app — varremos as rotas do FastAPI
        # e procuramos o pattern exato.
        paths = {getattr(r, "path", None) for r in app.routes}
        assert "/api/export/{symbol}.csv" in paths

    def test_endpoint_usa_streaming_response(self):
        # Verifica que a resposta é uma StreamingResponse (chunked) e não
        # JSONResponse. O `Transfer-Encoding: chunked` aparece no TestClient
        # quando o Content-Length não foi pré-calculado.
        from starlette.responses import StreamingResponse

        # Inspeção estática: o handler retorna StreamingResponse declarado.
        # Mais robusto que confiar no header (TestClient pode bufferizar).
        import inspect
        src = inspect.getsource(export_mod.export_prices_csv)
        assert "StreamingResponse" in src

    def test_decorador_rate_limit_aplicado(self):
        # `@limiter.limit(...)` atribui um marcador no objeto. Não checamos
        # detalhe interno do slowapi; só garantimos que o handler tem a
        # marcação esperada (existe um atributo relacionado a limites).
        # Forma mais simples: checar que o source code aplica o decorador
        # com a string de settings.
        import inspect
        src = inspect.getsource(export_mod)
        assert "@limiter.limit(settings.rate_limit_export)" in src


# ════════════════════════════════════════════════════════════════════
# 7. ENFORCEMENT REAL DO RATE LIMIT (sub-app dedicado)
# ════════════════════════════════════════════════════════════════════
#
# Mesma estratégia de `test_rate_limiting.py`: como o limiter compartilhado
# está com `enabled=False` em testes (via conftest.py), montamos um sub-app
# isolado com limite tight para provar que o gate funciona quando ligado.
# Este teste documenta o contrato: "10ª chamada passa, 11ª retorna 429"
# generalizado para "Nª passa, (N+1)ª 429" — usamos N=2 para velocidade.

@pytest.fixture
def sub_app_export_tight():
    test_limiter = Limiter(key_func=get_remote_address, enabled=True)

    sub_app = FastAPI()
    sub_app.state.limiter = test_limiter
    sub_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    sub_app.add_middleware(SlowAPIMiddleware)

    @sub_app.get("/export/{symbol}.csv")
    @test_limiter.limit("2/minute")
    def fake_export(request: Request, symbol: str):
        return {"symbol": symbol}

    return sub_app


class TestExportRateLimitEnforcement:
    def test_terceira_chamada_retorna_429_em_endpoint_export_simulado(
        self, sub_app_export_tight,
    ):
        c = TestClient(sub_app_export_tight, raise_server_exceptions=False)
        r1 = c.get("/export/PETR4.SA.csv")
        r2 = c.get("/export/PETR4.SA.csv")
        r3 = c.get("/export/PETR4.SA.csv")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
