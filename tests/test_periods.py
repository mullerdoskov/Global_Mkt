"""
tests/test_periods.py — ISSUE-012

Cobre `backend/api/_periods.py` e a integração com os 3 endpoints que
recebem `period`:
  - `GET /api/prices/{symbol}/history`
  - `GET /api/prices/{symbol}/returns`
  - `GET /api/market/sectors`

Estratégia:
  - Testes unitários de `parse_period`: tabelas de aceitação e rejeição,
    boundaries do range (1d, 10y), conversão correta para `timedelta`.
  - Testes de integração via `TestClient`: cada um dos 3 endpoints com
    `period` inválido deve retornar 422 e nem chegar a tocar o banco.
    Caminho feliz com `period` default (omitido) e com `period` válido
    customizado também é exercitado para garantir que o wiring não
    quebrou.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api._periods import (
    DEFAULT_PERIOD,
    MAX_DAYS,
    MIN_DAYS,
    ParsedPeriod,
    parse_period,
    period_dep,
)
from backend.app import app

client = TestClient(app)


# ════════════════════════════════════════════════════════════════════
# parse_period — unit tests
# ════════════════════════════════════════════════════════════════════


class TestParsePeriodValid:
    @pytest.mark.parametrize(
        "raw,expected_days",
        [
            ("1d", 1),                 # boundary inferior
            ("30d", 30),
            ("90d", 90),               # default histórico
            ("365d", 365),
            ("1w", 7),
            ("4w", 28),
            ("1m", 30),
            ("6m", 180),
            ("12m", 360),
            ("1y", 365),
            ("5y", 1825),
            ("10y", 3650),             # boundary superior (== MAX_DAYS)
        ],
    )
    def test_parse_aceita_formato_valido(self, raw, expected_days):
        result = parse_period(raw)
        assert isinstance(result, ParsedPeriod)
        assert result.raw == raw
        assert result.delta == timedelta(days=expected_days)
        assert result.days == expected_days

    def test_parsed_period_e_frozen_dataclass(self):
        # Necessário para chave de cache estável (fastapi-cache2).
        a = parse_period("90d")
        b = parse_period("90d")
        assert a == b
        assert repr(a) == repr(b)
        with pytest.raises((AttributeError, Exception)):
            a.raw = "30d"  # frozen → não pode mutar

    def test_min_e_max_days_constantes(self):
        # Sentinela: se algum dia mexerem nos bounds, force atualização
        # explícita dos testes acima.
        assert MIN_DAYS == 1
        assert MAX_DAYS == 3650
        assert DEFAULT_PERIOD == "90d"


class TestParsePeriodInvalid:
    @pytest.mark.parametrize(
        "raw",
        [
            "",                # vazio
            "30",              # sem unidade
            "d",               # sem número
            "d30",             # ordem invertida
            "30D",             # unidade maiúscula (estrito: rejeita)
            "30 d",            # com espaço
            " 30d",            # espaço à esquerda
            "30d ",            # espaço à direita
            "30days",          # unidade extensa
            "abc",             # totalmente inválido
            "30dx",            # caractere extra
            "30.5d",           # decimal
            "-5d",             # negativo
            "+5d",             # sinal explícito
            "30d30d",          # duplicado
            "0d",              # zero (fora do range MIN_DAYS=1)
            "0y",              # zero (fora do range)
            "30s",             # unidade não suportada (segundos)
            "30h",             # unidade não suportada (horas)
            "11y",             # 11y = 4015d > MAX_DAYS=3650
            "3651d",           # acima do MAX_DAYS por 1
            "366w",            # 366w = 2562d → ok? 366*7=2562 → ok. Vou usar outro.
        ],
    )
    def test_parse_rejeita_formato_invalido(self, raw):
        # Caso especial: 366w = 2562d (ainda dentro do range), removido
        # do parametrize via skip dinâmico não é elegante — em vez disso,
        # excluo aqui e cubro 366w como caso válido em seu próprio teste.
        if raw == "366w":
            pytest.skip("366w = 2562d está dentro do range; cobrir no teste de range.")
        with pytest.raises(HTTPException) as exc_info:
            parse_period(raw)
        assert exc_info.value.status_code == 422
        assert "period" in exc_info.value.detail

    def test_parse_rejeita_none(self):
        # `parse_period(None)` não deve cair em AttributeError; deve
        # virar HTTPException(422).
        with pytest.raises(HTTPException) as exc_info:
            parse_period(None)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize(
        "raw,days",
        [
            ("3651d", 3651),
            ("11y", 11 * 365),
            ("122m", 122 * 30),    # 3660 dias > 3650
        ],
    )
    def test_parse_rejeita_acima_do_max(self, raw, days):
        with pytest.raises(HTTPException) as exc_info:
            parse_period(raw)
        assert exc_info.value.status_code == 422
        assert "range" in exc_info.value.detail.lower()

    def test_366w_e_aceito_pois_esta_dentro_do_range(self):
        # 366 * 7 = 2562 dias < 3650 → válido.
        result = parse_period("366w")
        assert result.days == 2562


# ════════════════════════════════════════════════════════════════════
# period_dep — integração leve
# ════════════════════════════════════════════════════════════════════


class TestPeriodDep:
    def test_period_dep_propaga_validacao(self):
        with pytest.raises(HTTPException) as exc_info:
            period_dep(period="invalido")
        assert exc_info.value.status_code == 422

    def test_period_dep_aceita_string_valida(self):
        # Chamada direta (fora do FastAPI) com `period` explícito.
        # O default `Query("90d")` só é avaliado pelo injector do FastAPI
        # — para o caminho HTTP-default, ver
        # `TestEndpointsAceitamPeriodValido.test_history_default_period_quando_omitido`.
        result = period_dep(period="6m")
        assert isinstance(result, ParsedPeriod)
        assert result.raw == "6m"
        assert result.days == 180

    def test_default_period_constante_corresponde_ao_query_default(self):
        # Sentinela: `period_dep`'s `Query(DEFAULT_PERIOD, ...)` precisa
        # bater com a constante exposta pelo módulo. Se alguém mudar
        # uma sem mudar a outra, este teste falha.
        import inspect
        sig = inspect.signature(period_dep)
        query_default = sig.parameters["period"].default
        # `Query(...)` instances guardam o default em `.default`.
        assert getattr(query_default, "default", None) == DEFAULT_PERIOD


# ════════════════════════════════════════════════════════════════════
# Endpoints — período inválido devolve 422 sem tocar o banco
# ════════════════════════════════════════════════════════════════════


def _no_db_session():
    """
    Mock que falha se for chamado. Garante que o 422 é retornado pela
    validação de `period`, ANTES de qualquer query sair para o banco.
    """
    s = MagicMock()
    s.execute.side_effect = AssertionError("session.execute() não deveria ser chamado")
    return s


@pytest.mark.parametrize("invalid_period", ["abc", "30days", "30D", "0d", "11y", ""])
class TestEndpointsRejeitamPeriodInvalido:
    def test_history_422(self, invalid_period):
        with patch("backend.api.prices.get_session", return_value=_no_db_session()):
            r = client.get(f"/api/prices/PETR4.SA/history?period={invalid_period}")
        assert r.status_code == 422
        # FastAPI embute `detail` na resposta JSON; nosso parse_period
        # coloca "period" no texto. Aceita ambos os formatos (string
        # plana ou lista de erros do FastAPI default).
        body = r.json()
        assert "detail" in body

    def test_returns_422(self, invalid_period):
        with patch("backend.api.prices.get_session", return_value=_no_db_session()):
            r = client.get(f"/api/prices/PETR4.SA/returns?period={invalid_period}")
        assert r.status_code == 422
        assert "detail" in r.json()

    def test_sectors_422(self, invalid_period):
        with patch("backend.api.market.get_session", return_value=_no_db_session()):
            r = client.get(f"/api/market/sectors?period={invalid_period}")
        assert r.status_code == 422
        assert "detail" in r.json()


# ════════════════════════════════════════════════════════════════════
# Caminho feliz com `period` válido customizado e com default
# ════════════════════════════════════════════════════════════════════


def _asset_mock(symbol="PETR4.SA"):
    from types import SimpleNamespace
    return SimpleNamespace(
        id=1, symbol=symbol, name="Petrobras",
        asset_type=SimpleNamespace(value="stock"),
        currency="BRL", exchange="B3", is_active=True, company_id=10,
    )


def _result(scalar=None, scalar_one_or_none=None, scalars_all=None):
    r = MagicMock()
    r.scalar.return_value = scalar
    r.scalar_one_or_none.return_value = scalar_one_or_none
    sp = MagicMock()
    sp.all.return_value = scalars_all or []
    r.scalars.return_value = sp
    return r


def _session(*results):
    s = MagicMock()
    s.execute.side_effect = list(results)
    return s


class TestEndpointsAceitamPeriodValido:
    def test_history_com_period_5y(self):
        # 5y = 1825d, dentro do range. O handler deve calcular start_date
        # ~ today - 1825 dias e ecoar period="5y" na resposta.
        session = _session(
            _result(scalar_one_or_none=_asset_mock()),
            _result(scalars_all=[]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/PETR4.SA/history?period=5y")
        assert r.status_code == 200
        data = r.json()
        assert data["period"] == "5y"
        assert data["count"] == 0

    def test_history_default_period_quando_omitido(self):
        # Sem ?period=, deve cair no default DEFAULT_PERIOD=90d.
        session = _session(
            _result(scalar_one_or_none=_asset_mock()),
            _result(scalars_all=[]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/PETR4.SA/history")
        assert r.status_code == 200
        assert r.json()["period"] == "90d"

    def test_returns_com_period_4w(self):
        # 4w = 28d. Ecoa "4w" na resposta sem normalizar para "28d".
        session = _session(
            _result(scalar_one_or_none=_asset_mock()),
            _result(scalars_all=[]),
        )
        with patch("backend.api.prices.get_session", return_value=session):
            r = client.get("/api/prices/PETR4.SA/returns?period=4w")
        assert r.status_code == 200
        assert r.json()["period"] == "4w"

    def test_sectors_com_period_1y(self):
        session = _session(_result(scalars_all=[]))  # nenhum setor
        with patch("backend.api.market.get_session", return_value=session):
            r = client.get("/api/market/sectors?period=1y")
        assert r.status_code == 200
        assert r.json()["period"] == "1y"
