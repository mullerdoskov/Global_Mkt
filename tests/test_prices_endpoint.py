"""
tests/test_prices_endpoint.py
Validação do fix ISSUE-002 — GET /api/prices com DISTINCT ON + paginação.

Executa contra SQLite em memória (conftest seta MARKET_DB_URL).
A query real usa DISTINCT ON (PostgreSQL-nativo) — o mock evita executar
SQL em SQLite. Validação contra PostgreSQL fica pendente de confirmação local.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)

# Linhas simuladas: (symbol, name, asset_type::text, close, date)
SAMPLE_ROWS = [
    ("PETR4.SA", "Petrobras", "stock", 35.50, date(2026, 4, 25)),
    ("VALE3.SA", "Vale", "stock", 65.00, date(2026, 4, 25)),
    ("^BVSP", "Ibovespa", "index", 130000.0, date(2026, 4, 25)),
]


def _mock_session(count_value: int, rows: list) -> MagicMock:
    """Cria mock de session com duas chamadas execute: count e rows."""
    session = MagicMock()
    count_result = MagicMock()
    count_result.scalar.return_value = count_value
    rows_result = MagicMock()
    rows_result.fetchall.return_value = rows
    session.execute.side_effect = [count_result, rows_result]
    return session


class TestGetLatestPrices:
    def test_retorna_200_com_lista_de_precos(self):
        with patch("backend.api.prices.get_session", return_value=_mock_session(3, SAMPLE_ROWS)):
            r = client.get("/api/prices")
        assert r.status_code == 200
        data = r.json()
        assert "prices" in data
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert len(data["prices"]) == 3
        assert data["prices"][0]["symbol"] == "PETR4.SA"
        assert data["prices"][0]["close"] == 35.50
        assert data["prices"][0]["price_date"] == "2026-04-25"

    def test_paginacao_page_e_page_size(self):
        with patch("backend.api.prices.get_session", return_value=_mock_session(3, SAMPLE_ROWS[:2])):
            r = client.get("/api/prices?page=1&page_size=2")
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["prices"]) == 2

    def test_filtro_asset_type_stock(self):
        stock_rows = [r for r in SAMPLE_ROWS if r[2] == "stock"]
        with patch("backend.api.prices.get_session", return_value=_mock_session(2, stock_rows)):
            r = client.get("/api/prices?asset_type=stock")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["prices"]) == 2

    def test_page_size_acima_de_100_retorna_422(self):
        r = client.get("/api/prices?page_size=101")
        assert r.status_code == 422

    def test_page_invalida_retorna_422(self):
        r = client.get("/api/prices?page=0")
        assert r.status_code == 422

    def test_sem_resultados_retorna_lista_vazia(self):
        with patch("backend.api.prices.get_session", return_value=_mock_session(0, [])):
            r = client.get("/api/prices?asset_type=crypto")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["prices"] == []
