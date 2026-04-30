"""
tests/test_net_debt_ebitda.py
ISSUE-013 — `net_debt_ebitda` real (substitui placeholder).

Cobre:
- A função pura `compute_net_debt_ebitda` (todos os caminhos: ok, zero,
  None, NaN/inf, tipos não numéricos).
- O lookup `latest_net_debt_ebitda(session, company_id)` que busca a
  `FinancialStatement` mais recente e aplica a fórmula.
- Wiring no `ingest_financials_for_symbol`: o snapshot persistido em
  `valuation_multiples` ganha `net_debt_ebitda` calculado da última
  demonstração (mesmo quando a chamada de yfinance traz só `info`,
  sem novo income/balance).

Sem dependência de internet — `YFinanceClient.get_info`/`get_financials`
são mockados; banco é SQLite em memória criado via `Base.metadata.create_all`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db.schema import (
    Base,
    Company,
    FinancialStatement,
    PeriodType,
    ValuationMultiple,
)
from backend.ingestion.fundamentals_loader import (
    compute_net_debt_ebitda,
    ingest_financials_for_symbol,
    latest_net_debt_ebitda,
)


# ────────────────────────────────────────────────────────────────────
# 1. compute_net_debt_ebitda — função pura
# ────────────────────────────────────────────────────────────────────


class TestComputeNetDebtEbitda:
    @pytest.mark.parametrize(
        "net_debt, ebitda, expected",
        [
            (1000.0, 500.0, 2.0),                # alavancado clássico
            (-200.0, 800.0, -0.25),              # caixa líquido positivo (net debt < 0)
            (0.0, 100.0, 0.0),                   # sem dívida líquida
            (Decimal("1500"), Decimal("750"), 2.0),  # tipos Decimal (vindos do ORM Numeric)
            (1, 4, 0.25),                        # ints
        ],
    )
    def test_calculo_basico(self, net_debt, ebitda, expected):
        assert compute_net_debt_ebitda(net_debt, ebitda) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "net_debt, ebitda",
        [
            (None, 100.0),
            (1000.0, None),
            (None, None),
        ],
    )
    def test_none_em_qualquer_operando_retorna_none(self, net_debt, ebitda):
        assert compute_net_debt_ebitda(net_debt, ebitda) is None

    def test_ebitda_zero_retorna_none(self):
        # divisão por zero é indefinida — caso documentado pelo diagnóstico
        # ("guard contra ebitda=0").
        assert compute_net_debt_ebitda(1000.0, 0.0) is None
        assert compute_net_debt_ebitda(0.0, 0.0) is None
        assert compute_net_debt_ebitda(-500.0, 0) is None

    def test_nan_e_inf_retornam_none(self):
        assert compute_net_debt_ebitda(float("nan"), 100.0) is None
        assert compute_net_debt_ebitda(100.0, float("nan")) is None
        assert compute_net_debt_ebitda(float("inf"), 100.0) is None
        assert compute_net_debt_ebitda(100.0, float("-inf")) is None

    def test_tipo_nao_numerico_retorna_none(self):
        assert compute_net_debt_ebitda("muito", 100.0) is None
        assert compute_net_debt_ebitda(100.0, object()) is None


# ────────────────────────────────────────────────────────────────────
# 2. latest_net_debt_ebitda — lookup contra DB real (SQLite em memória)
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_company(session: Session, ticker: str = "TEST.SA") -> Company:
    company = Company(ticker=ticker, name=f"Test {ticker}", currency="BRL")
    session.add(company)
    session.commit()
    return company


def _add_financial(
    session: Session,
    company: Company,
    period_end: date,
    net_debt,
    ebitda,
):
    fs = FinancialStatement(
        company_id=company.id,
        period_end=period_end,
        period_type=PeriodType.quarterly,
        net_debt=net_debt,
        ebitda=ebitda,
        currency="BRL",
    )
    session.add(fs)
    session.commit()
    return fs


class TestLatestNetDebtEbitda:
    def test_sem_demonstracao_retorna_none(self, db_session):
        company = _add_company(db_session)
        assert latest_net_debt_ebitda(db_session, company.id) is None

    def test_uma_demonstracao_calcula_corretamente(self, db_session):
        company = _add_company(db_session)
        _add_financial(
            db_session, company,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("2000.00"),
            ebitda=Decimal("500.00"),
        )
        assert latest_net_debt_ebitda(db_session, company.id) == pytest.approx(4.0)

    def test_seleciona_periodo_mais_recente(self, db_session):
        # Mesmo se as inserções vierem fora de ordem, o `ORDER BY
        # period_end DESC` deve pegar o trimestre mais novo.
        company = _add_company(db_session)
        _add_financial(
            db_session, company,
            period_end=date(2025, 12, 31),
            net_debt=Decimal("1000"), ebitda=Decimal("250"),  # 4.0
        )
        _add_financial(
            db_session, company,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("1500"), ebitda=Decimal("500"),  # 3.0 ← mais recente
        )
        _add_financial(
            db_session, company,
            period_end=date(2025, 9, 30),
            net_debt=Decimal("800"), ebitda=Decimal("200"),  # 4.0
        )
        assert latest_net_debt_ebitda(db_session, company.id) == pytest.approx(3.0)

    def test_ebitda_zero_no_periodo_mais_recente_retorna_none(self, db_session):
        # Cenário real: empresa em prejuízo operacional severo no último Q.
        # Não fazemos fallback para um Q anterior — a métrica é "trailing
        # mais recente"; se está indefinida, é melhor sinalizar do que
        # devolver número velho disfarçado.
        company = _add_company(db_session)
        _add_financial(
            db_session, company,
            period_end=date(2025, 12, 31),
            net_debt=Decimal("1000"), ebitda=Decimal("500"),  # 2.0
        )
        _add_financial(
            db_session, company,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("1200"), ebitda=Decimal("0"),
        )
        assert latest_net_debt_ebitda(db_session, company.id) is None

    def test_isola_por_company(self, db_session):
        c1 = _add_company(db_session, ticker="ONE.SA")
        c2 = _add_company(db_session, ticker="TWO.SA")
        _add_financial(
            db_session, c1,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("1000"), ebitda=Decimal("500"),  # 2.0
        )
        _add_financial(
            db_session, c2,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("3000"), ebitda=Decimal("300"),  # 10.0
        )
        assert latest_net_debt_ebitda(db_session, c1.id) == pytest.approx(2.0)
        assert latest_net_debt_ebitda(db_session, c2.id) == pytest.approx(10.0)


# ────────────────────────────────────────────────────────────────────
# 3. Wiring em ingest_financials_for_symbol — snapshot persistido
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def memory_db_with_session(monkeypatch):
    """
    Substitui `get_session` e `IS_SQLITE` no módulo do loader por um
    SQLite em memória compartilhado, para que `ingest_financials_for_symbol`
    leia/escreva no mesmo banco do teste.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def _factory():
        return Session(engine)

    monkeypatch.setattr(
        "backend.ingestion.fundamentals_loader.get_session",
        _factory,
    )
    monkeypatch.setattr(
        "backend.ingestion.fundamentals_loader.IS_SQLITE",
        True,
    )

    inspect_session = Session(engine)
    try:
        yield inspect_session, _factory
    finally:
        inspect_session.close()
        engine.dispose()


class TestSnapshotPersistido:
    def test_snapshot_inclui_net_debt_ebitda_calculado_do_balance_corrente(
        self, memory_db_with_session
    ):
        inspect_session, _ = memory_db_with_session

        company = _add_company(inspect_session, ticker="ABC.SA")

        # Prepara mock do client: get_financials retorna um DataFrame-like
        # mínimo via `_get_field`. Mockamos `_get_field` no nível do módulo
        # para retornar valores diretos por nome do campo, evitando
        # dependência de pandas no teste.
        client = MagicMock()
        client.get_financials.return_value = {
            "income_stmt": _FakeDF(columns=[date(2026, 3, 31)]),
            "balance_sheet": _FakeDF(columns=[date(2026, 3, 31)]),
            "cashflow": _FakeDF(columns=[date(2026, 3, 31)]),
        }
        client.get_info.return_value = {
            "trailingPE": 12.5,
            "priceToBook": 1.2,
            # Campos não relevantes ficam ausentes — `_safe(None)` → None.
        }

        # Substitui `_get_field` para responder com valores conhecidos.
        # Income → ebitda=500; Balance → total_debt=2500, cash=500
        # (net_debt = 2000); resultado esperado: 2000/500 = 4.0.
        field_map = {
            ("Total Revenue", "Revenue"): 10000.0,
            ("EBITDA", "Normalized EBITDA"): 500.0,
            ("Total Debt", "Long Term Debt"): 2500.0,
            ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"): 500.0,
        }

        def _fake_get_field(df, field_names):
            return field_map.get(tuple(field_names))

        with patch(
            "backend.ingestion.fundamentals_loader._get_field",
            side_effect=_fake_get_field,
        ):
            ingest_financials_for_symbol(client, "ABC.SA")

        snapshot = inspect_session.execute(
            select(ValuationMultiple).where(ValuationMultiple.company_id == company.id)
        ).scalar_one()
        assert snapshot.net_debt_ebitda is not None
        assert float(snapshot.net_debt_ebitda) == pytest.approx(4.0)

    def test_snapshot_usa_dados_persistidos_quando_yfinance_so_traz_info(
        self, memory_db_with_session
    ):
        # Cenário real: 1ª run trouxe o income statement do Q1, 2ª run
        # acontece no mesmo dia mas yfinance retorna `financials=None`
        # (ex.: rate-limit). O snapshot ainda deve ter `net_debt_ebitda`
        # calculado a partir do que está no banco.
        inspect_session, _ = memory_db_with_session
        company = _add_company(inspect_session, ticker="XYZ.SA")
        _add_financial(
            inspect_session, company,
            period_end=date(2026, 3, 31),
            net_debt=Decimal("3000"), ebitda=Decimal("1000"),  # 3.0
        )

        client = MagicMock()
        client.get_financials.return_value = None  # sem novos statements
        client.get_info.return_value = {"trailingPE": 8.0}

        ingest_financials_for_symbol(client, "XYZ.SA")

        snapshot = inspect_session.execute(
            select(ValuationMultiple).where(ValuationMultiple.company_id == company.id)
        ).scalar_one()
        assert float(snapshot.net_debt_ebitda) == pytest.approx(3.0)

    def test_snapshot_recebe_none_quando_nao_ha_demonstracao(
        self, memory_db_with_session
    ):
        inspect_session, _ = memory_db_with_session
        company = _add_company(inspect_session, ticker="NEW.SA")

        client = MagicMock()
        client.get_financials.return_value = None
        client.get_info.return_value = {"trailingPE": 20.0}

        ingest_financials_for_symbol(client, "NEW.SA")

        snapshot = inspect_session.execute(
            select(ValuationMultiple).where(ValuationMultiple.company_id == company.id)
        ).scalar_one()
        assert snapshot.net_debt_ebitda is None


class _FakeDF:
    """
    Simula uma fração mínima da API de DataFrame consumida pelo loader:
    `df.empty`, `df.columns`, e `col in df.columns`. Os valores reais são
    fornecidos pelo `_get_field` mockado (não passamos por `df.loc[name]`).
    """

    def __init__(self, columns):
        self.columns = columns
        self.empty = False

    def __getitem__(self, key):
        return self  # retorna ele mesmo — `_get_field` mockado ignora.

    def __contains__(self, key):
        return key in self.columns
