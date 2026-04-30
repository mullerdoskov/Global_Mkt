"""
tests/test_asian_assets.py
ISSUE-016 — Adiciona ativos asiáticos (JP/AU/HK) ao universo de ingestão.

Cobre:
- Tamanho mínimo das três listas novas (STOCKS_JP/AU/HK).
- Convenção de sufixo yfinance por exchange (.T, .AX, .HK).
- Inclusão das três listas em `ALL_STOCKS` e em `SYMBOLS_BY_TYPE["stock"]`.
- Mapeamento `get_country_for_symbol` para os novos sufixos.
- Presença dos índices asiáticos (`^N225`, `^HSI`, `^AXJO`) em `INDICES`.
- Hong Kong adicionado a `COUNTRIES` (JP/AU/CN já existiam).
- Ausência de duplicatas entre todas as listas de ações.
- Smoke da rota de ingestão: `ensure_asset_exists` cria company com o país
  correto para um ticker JP/AU/HK quando recebe info do (mockado) yfinance.

Sem dependência de internet ou banco real — yfinance é totalmente mockado e
o teste de ingestão usa SQLite em memória criado via Base.metadata.create_all.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.config.symbols import (
    ALL_STOCKS,
    INDICES,
    STOCKS_AU,
    STOCKS_HK,
    STOCKS_JP,
    SYMBOLS_BY_TYPE,
    get_country_for_symbol,
)
from backend.data.sectors_gics import COUNTRIES


# ════════════════════════════════════════════════════════════════════
# 1. Tamanho mínimo e convenção de sufixo
# ════════════════════════════════════════════════════════════════════


class TestStockListSizes:
    def test_stocks_jp_tem_pelo_menos_20(self):
        assert len(STOCKS_JP) >= 20, (
            f"STOCKS_JP precisa cobrir ~20 do Nikkei 225 (atual: {len(STOCKS_JP)})"
        )

    def test_stocks_au_tem_pelo_menos_10(self):
        assert len(STOCKS_AU) >= 10, (
            f"STOCKS_AU precisa cobrir ~10 do ASX 200 (atual: {len(STOCKS_AU)})"
        )

    def test_stocks_hk_tem_pelo_menos_10(self):
        assert len(STOCKS_HK) >= 10, (
            f"STOCKS_HK precisa cobrir ~10 do HSI (atual: {len(STOCKS_HK)})"
        )


class TestStockSuffixConvention:
    def test_todos_jp_terminam_em_dot_t(self):
        for sym in STOCKS_JP:
            assert sym.endswith(".T"), (
                f"Ticker JP fora da convenção yfinance: {sym} (esperado sufixo .T)"
            )

    def test_todos_au_terminam_em_dot_ax(self):
        for sym in STOCKS_AU:
            assert sym.endswith(".AX"), (
                f"Ticker AU fora da convenção yfinance: {sym} (esperado sufixo .AX)"
            )

    def test_todos_hk_terminam_em_dot_hk(self):
        for sym in STOCKS_HK:
            assert sym.endswith(".HK"), (
                f"Ticker HK fora da convenção yfinance: {sym} (esperado sufixo .HK)"
            )


# ════════════════════════════════════════════════════════════════════
# 2. Inclusão nas agregações
# ════════════════════════════════════════════════════════════════════


class TestAggregationInclusion:
    def test_all_stocks_inclui_jp(self):
        for sym in STOCKS_JP:
            assert sym in ALL_STOCKS

    def test_all_stocks_inclui_au(self):
        for sym in STOCKS_AU:
            assert sym in ALL_STOCKS

    def test_all_stocks_inclui_hk(self):
        for sym in STOCKS_HK:
            assert sym in ALL_STOCKS

    def test_symbols_by_type_stock_inclui_novos(self):
        stocks = SYMBOLS_BY_TYPE["stock"]
        for sym in STOCKS_JP + STOCKS_AU + STOCKS_HK:
            assert sym in stocks

    def test_sem_duplicatas_em_all_stocks(self):
        # Regressão: STOCKS_BR/US/UK/DE/FR/NL/CH/JP/AU/HK não devem ter
        # interseção entre si nem repetições internas.
        seen = set()
        duplicates = []
        for sym in ALL_STOCKS:
            if sym in seen:
                duplicates.append(sym)
            seen.add(sym)
        assert not duplicates, f"Tickers duplicados em ALL_STOCKS: {duplicates}"


# ════════════════════════════════════════════════════════════════════
# 3. Índices asiáticos
# ════════════════════════════════════════════════════════════════════


class TestAsianIndices:
    @pytest.mark.parametrize("idx", ["^N225", "^HSI", "^AXJO"])
    def test_indice_presente(self, idx):
        assert idx in INDICES, f"Índice {idx} ausente da lista INDICES"


# ════════════════════════════════════════════════════════════════════
# 4. get_country_for_symbol — novos sufixos
# ════════════════════════════════════════════════════════════════════


class TestCountryMappingForNewSuffixes:
    @pytest.mark.parametrize(
        "symbol,expected",
        [
            # Stocks reais das listas
            ("7203.T", "JP"),
            ("9984.T", "JP"),
            ("BHP.AX", "AU"),
            ("CBA.AX", "AU"),
            ("0700.HK", "HK"),
            ("9988.HK", "HK"),
            # Sintéticos para garantir que o roteamento é por sufixo, não por nome
            ("XYZ.T", "JP"),
            ("XYZ.AX", "AU"),
            ("XYZ.HK", "HK"),
        ],
    )
    def test_mapeamento_sufixo(self, symbol, expected):
        assert get_country_for_symbol(symbol) == expected

    def test_indices_asiaticos_continuam_mapeando_corretamente(self):
        # Os 3 índices novos do escopo de ISSUE-016 já estavam previstos no
        # dicionário interno de get_country_for_symbol. Garantir que o mapeamento
        # se preserva (regressão se alguém mexer no idx_country).
        assert get_country_for_symbol("^N225") == "JP"
        assert get_country_for_symbol("^HSI") == "CN"  # Hang Seng listado em HK mas tracks Greater China; mapping atual = CN
        assert get_country_for_symbol("^AXJO") == "AU"

    def test_todos_os_jp_resolvem_para_jp(self):
        for sym in STOCKS_JP:
            assert get_country_for_symbol(sym) == "JP", sym

    def test_todos_os_au_resolvem_para_au(self):
        for sym in STOCKS_AU:
            assert get_country_for_symbol(sym) == "AU", sym

    def test_todos_os_hk_resolvem_para_hk(self):
        for sym in STOCKS_HK:
            assert get_country_for_symbol(sym) == "HK", sym


# ════════════════════════════════════════════════════════════════════
# 5. Hong Kong na tabela COUNTRIES
# ════════════════════════════════════════════════════════════════════


class TestCountriesTable:
    def _get_country(self, iso2: str):
        for c in COUNTRIES:
            if c["iso2"] == iso2:
                return c
        return None

    def test_hong_kong_presente(self):
        hk = self._get_country("HK")
        assert hk is not None, "Hong Kong (HK) ausente de COUNTRIES"
        assert hk["iso3"] == "HKG"
        assert hk["yf_suffix"] == ".HK"
        assert hk["currency_code"] == "HKD"
        assert hk["main_exchange"] == "HKEX"
        assert hk["region"] == "Asia"

    def test_japao_existente_continua_correto(self):
        jp = self._get_country("JP")
        assert jp is not None
        assert jp["yf_suffix"] == ".T"

    def test_australia_existente_continua_correto(self):
        au = self._get_country("AU")
        assert au is not None
        assert au["yf_suffix"] == ".AX"

    def test_iso2_unico(self):
        codes = [c["iso2"] for c in COUNTRIES]
        assert len(codes) == len(set(codes)), (
            f"COUNTRIES tem iso2 duplicados: {codes}"
        )


# ════════════════════════════════════════════════════════════════════
# 6. Smoke de ingestão — ensure_asset_exists para JP/AU/HK
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
def in_memory_session():
    """SQLite em memória com schema completo. Inclui as 3 country rows
    necessárias (JP/AU/HK) pré-populadas para que o lookup por iso2 encontre
    o país e o company seja criado com country_id correto."""
    from backend.db.schema import Base, Country

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add_all([
        Country(iso2="JP", iso3="JPN", name="Japan", name_pt="Japão",
                region="Asia", currency_code="JPY",
                main_exchange="TSE", yf_suffix=".T"),
        Country(iso2="AU", iso3="AUS", name="Australia", name_pt="Austrália",
                region="Oceania", currency_code="AUD",
                main_exchange="ASX", yf_suffix=".AX"),
        Country(iso2="HK", iso3="HKG", name="Hong Kong", name_pt="Hong Kong",
                region="Asia", currency_code="HKD",
                main_exchange="HKEX", yf_suffix=".HK"),
    ])
    session.commit()
    yield session
    session.close()


def _fake_yf_client(info: dict) -> MagicMock:
    """Cliente yfinance mockado: get_info() devolve `info`, nada mais."""
    client = MagicMock()
    client.get_info.return_value = info
    return client


class TestEnsureAssetExistsForAsianStocks:
    """Smoke da ingestão: criar company para um ticker de cada região nova
    deve gravar `country_id` apontando para a Country correta. Sem isso
    `ALL_STOCKS` cresce, mas a metadata de localização fica em branco —
    quebra filtros de mercado (`/api/market/sectors?country=JP` etc.)."""

    def test_company_criada_para_ticker_jp(self, in_memory_session):
        from backend.db.schema import Asset, Company, Country
        from backend.ingestion.loader import ensure_asset_exists

        client = _fake_yf_client({
            "longName": "Toyota Motor Corp",
            "currency": "JPY",
            "exchange": "JPX",
            "marketCap": 350_000_000_000,
        })
        asset_id = ensure_asset_exists(
            in_memory_session, "7203.T", "stock", client
        )
        assert asset_id is not None

        asset = in_memory_session.execute(
            select(Asset).where(Asset.symbol == "7203.T")
        ).scalar_one()
        assert asset.company_id is not None

        company = in_memory_session.execute(
            select(Company).where(Company.id == asset.company_id)
        ).scalar_one()
        country = in_memory_session.execute(
            select(Country).where(Country.id == company.country_id)
        ).scalar_one()
        assert country.iso2 == "JP"
        assert company.currency == "JPY"

    def test_company_criada_para_ticker_au(self, in_memory_session):
        from backend.db.schema import Asset, Company, Country
        from backend.ingestion.loader import ensure_asset_exists

        client = _fake_yf_client({
            "longName": "BHP Group Ltd",
            "currency": "AUD",
            "exchange": "ASX",
        })
        asset_id = ensure_asset_exists(
            in_memory_session, "BHP.AX", "stock", client
        )
        asset = in_memory_session.execute(
            select(Asset).where(Asset.symbol == "BHP.AX")
        ).scalar_one()
        company = in_memory_session.execute(
            select(Company).where(Company.id == asset.company_id)
        ).scalar_one()
        country = in_memory_session.execute(
            select(Country).where(Country.id == company.country_id)
        ).scalar_one()
        assert country.iso2 == "AU"
        assert company.currency == "AUD"

    def test_company_criada_para_ticker_hk(self, in_memory_session):
        from backend.db.schema import Asset, Company, Country
        from backend.ingestion.loader import ensure_asset_exists

        client = _fake_yf_client({
            "longName": "Tencent Holdings Ltd",
            "currency": "HKD",
            "exchange": "HKG",
        })
        asset_id = ensure_asset_exists(
            in_memory_session, "0700.HK", "stock", client
        )
        asset = in_memory_session.execute(
            select(Asset).where(Asset.symbol == "0700.HK")
        ).scalar_one()
        company = in_memory_session.execute(
            select(Company).where(Company.id == asset.company_id)
        ).scalar_one()
        country = in_memory_session.execute(
            select(Country).where(Country.id == company.country_id)
        ).scalar_one()
        assert country.iso2 == "HK"
        assert company.currency == "HKD"
