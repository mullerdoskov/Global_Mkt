"""
Classificação setorial GICS + mapeamento de países e tickers.
34 setores (sub-indústrias) + 12 países cobertos.
"""

# ══════════════════════════════════════════════════════════
#  SETORES GICS (Global Industry Classification Standard)
# ══════════════════════════════════════════════════════════

GICS_SECTORS = {
    10: "Energy",
    15: "Materials",
    20: "Industrials",
    25: "Consumer Discretionary",
    30: "Consumer Staples",
    35: "Health Care",
    40: "Financials",
    45: "Information Technology",
    50: "Communication Services",
    55: "Utilities",
    60: "Real Estate",
}

GICS_INDUSTRY_GROUPS = {
    1010: "Energy",
    1510: "Materials",
    2010: "Capital Goods",
    2020: "Commercial & Professional Services",
    2030: "Transportation",
    2510: "Automobiles & Components",
    2520: "Consumer Durables & Apparel",
    2530: "Consumer Services",
    2550: "Retailing",
    2560: "Consumer Discretionary Distribution",
    3010: "Food & Staples Retailing",
    3020: "Food, Beverage & Tobacco",
    3030: "Household & Personal Products",
    3510: "Health Care Equipment & Services",
    3520: "Pharmaceuticals, Biotechnology & Life Sciences",
    4010: "Banks",
    4020: "Diversified Financials",
    4030: "Insurance",
    4040: "Financial Services",
    4510: "Software & Services",
    4520: "Technology Hardware & Equipment",
    4530: "Semiconductors & Semiconductor Equipment",
    5010: "Telecommunication Services",
    5020: "Media & Entertainment",
    5510: "Utilities",
    6010: "Equity Real Estate Investment Trusts",
    6020: "Real Estate Management & Development",
}

# ══════════════════════════════════════════════════════════
#  PAÍSES COBERTOS
# ══════════════════════════════════════════════════════════

COUNTRIES = {
    "BR": {"name": "Brasil", "currency": "BRL", "exchange": "B3"},
    "US": {"name": "Estados Unidos", "currency": "USD", "exchange": "NYSE/NASDAQ"},
    "GB": {"name": "Reino Unido", "currency": "GBP", "exchange": "LSE"},
    "DE": {"name": "Alemanha", "currency": "EUR", "exchange": "XETRA"},
    "FR": {"name": "França", "currency": "EUR", "exchange": "Euronext Paris"},
    "CH": {"name": "Suíça", "currency": "CHF", "exchange": "SIX"},
    "NL": {"name": "Holanda", "currency": "EUR", "exchange": "Euronext Amsterdam"},
    "IT": {"name": "Itália", "currency": "EUR", "exchange": "Borsa Italiana"},
    "ES": {"name": "Espanha", "currency": "EUR", "exchange": "BME"},
    "JP": {"name": "Japão", "currency": "JPY", "exchange": "TSE"},
    "KR": {"name": "Coreia do Sul", "currency": "KRW", "exchange": "KRX"},
    "HK": {"name": "Hong Kong", "currency": "HKD", "exchange": "HKEX"},
    "CN": {"name": "China", "currency": "CNY", "exchange": "SSE/SZSE"},
    "IN": {"name": "Índia", "currency": "INR", "exchange": "NSE/BSE"},
    "AU": {"name": "Austrália", "currency": "AUD", "exchange": "ASX"},
    "MX": {"name": "México", "currency": "MXN", "exchange": "BMV"},
    "AR": {"name": "Argentina", "currency": "ARS", "exchange": "BYMA"},
    "CL": {"name": "Chile", "currency": "CLP", "exchange": "Bolsa de Santiago"},
    "CO": {"name": "Colômbia", "currency": "COP", "exchange": "BVC"},
    "PE": {"name": "Peru", "currency": "PEN", "exchange": "BVL"},
    "EU": {"name": "Europa (zona euro)", "currency": "EUR", "exchange": "Multi"},
    "GLOBAL": {"name": "Global", "currency": "USD", "exchange": "Multi"},
}

# ══════════════════════════════════════════════════════════
#  MAPEAMENTO TICKER → SETOR GICS
# ══════════════════════════════════════════════════════════

TICKER_SECTOR_MAP = {
    # Energia
    "PETR4.SA": 1010, "PRIO3.SA": 1010, "CSAN3.SA": 1010, "VBBR3.SA": 1010,
    "RAIZ4.SA": 1010, "UGPA3.SA": 1010, "ENEV3.SA": 1010,
    "XOM": 1010, "CVX": 1010, "TTE.PA": 1010, "SHEL.L": 1010, "BP.L": 1010,
    "ENI.MI": 1010, "ECOPETL.BVC": 1010, "YPF": 1010,
    # Materiais
    "VALE3.SA": 1510, "SUZB3.SA": 1510, "KLBN11.SA": 1510, "CSNA3.SA": 1510,
    "GGBR4.SA": 1510, "GOAU4.SA": 1510, "BRKM5.SA": 1510, "DXCO3.SA": 1510,
    "RIO.L": 1510, "BHP.AX": 1510, "BAS.DE": 1510, "BVN": 1510,
    "CEMEXCPO.MX": 1510, "SQM-B.SN": 1510,
    # Industriais
    "WEGE3.SA": 2010, "EMBR3.SA": 2010, "RAIL3.SA": 2030, "CCRO3.SA": 2030,
    "CAT": 2010, "DE": 2010, "GE": 2010, "HON": 2010, "BA": 2010,
    "RTX": 2010, "LMT": 2010, "UPS": 2030, "FDX": 2030,
    "SIE.DE": 2010, "AIR.PA": 2010, "SU.PA": 2010,
    # Consumo Discricionário
    "LREN3.SA": 2550, "MGLU3.SA": 2550, "ARZZ3.SA": 2520, "SOMA3.SA": 2520,
    "VIVA3.SA": 2520, "CYRE3.SA": 2520, "MRVE3.SA": 2520, "CVCB3.SA": 2530,
    "PETZ3.SA": 2550, "RENT3.SA": 2030,
    "AMZN": 2550, "TSLA": 2510, "HD": 2550, "DIS": 2530, "NFLX": 5020,
    "ABNB": 2530, "UBER": 2030, "MC.PA": 2520,
    "BMW.DE": 2510, "VOW3.DE": 2510, "MBG.DE": 2510,
    "FALABELLA.SN": 2550, "WALMEX.MX": 2550,
    # Consumo Básico
    "ABEV3.SA": 3020, "JBSS3.SA": 3020, "BRFS3.SA": 3020, "MRFG3.SA": 3020,
    "BEEF3.SA": 3020, "SLCE3.SA": 3020, "SMTO3.SA": 3020,
    "ASAI3.SA": 3010, "CRFB3.SA": 3010, "NTCO3.SA": 3030,
    "PG": 3030, "KO": 3020, "PEP": 3020, "COST": 3010, "WMT": 3010,
    "NESN.SW": 3020, "OR.PA": 3030, "ULVR.L": 3030, "DGE.L": 3020,
    "FEMSAUBD.MX": 3020, "BIMBOA.MX": 3020,
    # Saúde
    "RDOR3.SA": 3510, "HAPV3.SA": 3510, "FLRY3.SA": 3510,
    "QUAL3.SA": 3510, "HYPE3.SA": 3520,
    "JNJ": 3520, "UNH": 3510, "PFE": 3520, "MRK": 3520, "ABT": 3510,
    "TMO": 3520, "LLY": 3520, "AZN.L": 3520, "GSK.L": 3520,
    "ROG.SW": 3520, "NOVN.SW": 3520, "SAN.PA": 3520,
    # Financeiro
    "ITUB4.SA": 4010, "BBDC4.SA": 4010, "BBAS3.SA": 4010,
    "SANB11.SA": 4010, "ITSA4.SA": 4020, "B3SA3.SA": 4020,
    "BPAC11.SA": 4020, "IRBR3.SA": 4030,
    "JPM": 4010, "BAC": 4010, "WFC": 4010, "C": 4010, "GS": 4020,
    "MS": 4020, "BLK": 4020, "SCHW": 4020, "SPGI": 4020,
    "V": 4040, "MA": 4040, "AXP": 4040, "PYPL": 4040,
    "CB": 4030, "MMC": 4030,
    "BNP.PA": 4010, "HSBA.L": 4010, "BARC.L": 4010, "LSEG.L": 4020,
    "ALV.DE": 4030, "INGA.AS": 4010,
    "ISP.MI": 4010, "UCG.MI": 4010, "SAN.MC": 4010, "BBVA.MC": 4010,
    "8306.T": 4010, "HDFCBANK.NS": 4010, "CBA.AX": 4010, "NAB.AX": 4010,
    "GFNORTEO.MX": 4010, "GGAL": 4010, "CREDICORP": 4010,
    "NU": 4040, "STNE": 4040, "PAGS": 4040, "XP": 4020,
    "SQ": 4040, "COIN": 4020,
    # Tecnologia
    "TOTS3.SA": 4510, "LWSA3.SA": 4510, "CASH3.SA": 4510,
    "AAPL": 4520, "MSFT": 4510, "GOOGL": 5020, "META": 5020,
    "NVDA": 4530, "ADBE": 4510, "CRM": 4510, "ORCL": 4510,
    "INTU": 4510, "NOW": 4510, "PANW": 4510,
    "AMD": 4530, "INTC": 4530, "QCOM": 4530, "TXN": 4530,
    "AVGO": 4530, "AMAT": 4530, "LRCX": 4530, "KLAC": 4530,
    "MU": 4530, "MRVL": 4530, "ARM": 4530, "SMCI": 4520,
    "SNPS": 4510, "CDNS": 4510,
    "CSCO": 4520, "IBM": 4510,
    "SNOW": 4510, "DDOG": 4510, "ZS": 4510, "NET": 4510, "PLTR": 4510,
    "SAP.DE": 4510, "ASML.AS": 4530,
    "005930.KS": 4530, "000660.KS": 4530, "035420.KS": 5020,
    "TCS.NS": 4510, "INFY.NS": 4510,
    "MELI": 2550,
    # Comunicações
    "VIVT3.SA": 5010, "TIMS3.SA": 5010, "OIBR3.SA": 5010,
    "DTE.DE": 5010, "TEF.MC": 5010, "TLEVICPO.MX": 5020,
    "9432.T": 5010,
    "0700.HK": 5020, "9988.HK": 2550, "3690.HK": 2550,
    # Utilities
    "ELET3.SA": 5510, "ELET6.SA": 5510, "CPLE6.SA": 5510, "CMIG4.SA": 5510,
    "TAEE11.SA": 5510, "SBSP3.SA": 5510, "EQTL3.SA": 5510,
    "CPFE3.SA": 5510, "ENBR3.SA": 5510, "TRPL4.SA": 5510,
    "AESB3.SA": 5510, "NEOE3.SA": 5510, "AURE3.SA": 5510,
    "NEE": 5510, "DUK": 5510, "SO": 5510, "D": 5510, "SRE": 5510,
    "ENEL.MI": 5510, "IBE.MC": 5510, "COPEC.SN": 1010,
    # Real Estate
    "MULT3.SA": 6010, "IGTI11.SA": 6010, "ALSO3.SA": 6010,
    # Aéreas / Transporte
    "AZUL4.SA": 2030, "GOLL4.SA": 2030,
    # Educação
    "COGN3.SA": 2530, "YDUQ3.SA": 2530,
    # Farmácia / Varejo
    "RADL3.SA": 3010,
    # Portos / Logística
    "STBP3.SA": 2030,
    # Automotive (Asia)
    "7203.T": 2510, "7267.T": 2510,
    # Tech (Asia)
    "6758.T": 2520, "6861.T": 4520, "9984.T": 4020,
    "6902.T": 2510,
    # Insurance (Asia)
    "1299.HK": 4030, "2318.HK": 4030,
    # Banks (Asia)
    "0939.HK": 4010,
    # Conglomerates (India)
    "RELIANCE.NS": 1010,
    # Australia
    "CSL.AX": 3520,
    # Telecom (Mexico)
    "AMXL.MX": 5010,
    # Pharma (NL)
    "PHIA.AS": 3510,
    # Consumer (Japan)
    "035420.KS": 5020,
}


def get_sector_name(gics_code: int) -> str:
    """Retorna o nome do setor GICS dado um código de indústria."""
    sector_code = (gics_code // 100) * 10 if gics_code > 100 else gics_code
    return GICS_SECTORS.get(sector_code, "Unknown")


def get_industry_group_name(gics_code: int) -> str:
    """Retorna o nome do grupo de indústria GICS."""
    return GICS_INDUSTRY_GROUPS.get(gics_code, "Unknown")


def get_ticker_sector(ticker: str) -> dict | None:
    """Retorna info do setor para um ticker específico."""
    code = TICKER_SECTOR_MAP.get(ticker)
    if code is None:
        return None
    return {
        "gics_code": code,
        "sector": get_sector_name(code),
        "industry_group": get_industry_group_name(code),
    }
