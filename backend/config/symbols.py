"""
config/symbols.py
~640 tickers organizados por tipo e mercado: BR/US/EU/Ásia/Oceania + índices,
commodities, FX, cripto. Ásia (JP/HK) e Oceania (AU) adicionados em ISSUE-016.
"""

# ══════════════════════════════════════════════
# AÇÕES BRASIL — B3 (~80)
# ══════════════════════════════════════════════
STOCKS_BR = [
    # Petróleo & Gás
    "PETR3.SA", "PETR4.SA", "PRIO3.SA", "RECV3.SA", "RRRP3.SA", "CSAN3.SA",
    "UGPA3.SA", "VBBR3.SA",
    # Mineração & Siderurgia
    "VALE3.SA", "CSNA3.SA", "GGBR4.SA", "GOAU4.SA", "USIM5.SA", "CBAV3.SA",
    # Bancos & Financeiro
    "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "SANB11.SA", "BPAC11.SA", "ITSA4.SA",
    "B3SA3.SA", "BBSE3.SA", "CIEL3.SA", "IRBR3.SA", "SULA11.SA", "PSSA3.SA",
    # Energia Elétrica
    "ELET3.SA", "ELET6.SA", "CMIG4.SA", "CPFE3.SA", "ENGI11.SA", "EQTL3.SA",
    "TAEE11.SA", "ENBR3.SA", "CPLE6.SA", "AURE3.SA", "NEOE3.SA", "AESB3.SA",
    # Saneamento
    "SBSP3.SA", "SAPR11.SA",
    # Varejo & Consumo
    "MGLU3.SA", "LREN3.SA", "AMER3.SA", "VIIA3.SA", "PETZ3.SA", "ASAI3.SA",
    "CRFB3.SA", "NTCO3.SA", "ABEV3.SA", "JBSS3.SA", "MRFG3.SA", "BEEF3.SA",
    "BRFS3.SA", "MDIA3.SA", "SMTO3.SA",
    # Saúde
    "RDOR3.SA", "HAPV3.SA", "FLRY3.SA", "HYPE3.SA", "RADL3.SA",
    # Indústria & Bens de Capital
    "WEGE3.SA", "EMBR3.SA", "RAIL3.SA", "CCRO3.SA", "ECOR3.SA",
    # Tecnologia & Telecom
    "TOTS3.SA", "VIVT3.SA", "TIMS3.SA",
    # Imobiliário & Construção
    "CYRE3.SA", "MRVE3.SA", "EZTC3.SA", "MULT3.SA", "IGTI11.SA",
    # Papel & Celulose
    "SUZB3.SA", "KLBN11.SA",
    # Educação
    "YDUQ3.SA", "COGN3.SA",
    # Outros
    "RENT3.SA", "LWSA3.SA", "RAIZ4.SA", "ALPA4.SA",
]

# ══════════════════════════════════════════════
# AÇÕES EUA — NYSE/NASDAQ (~120)
# ══════════════════════════════════════════════
STOCKS_US = [
    # Mega-cap Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
    "CRM", "ADBE", "AMD", "INTC", "QCOM", "TXN", "AMAT", "MU", "LRCX", "KLAC",
    "SNPS", "CDNS", "NFLX", "CSCO", "IBM", "NOW", "INTU", "PANW", "CRWD",
    # Financeiro
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "CB",
    "MMC", "PGR", "AON", "ICE", "CME", "SPGI", "MCO", "MSCI",
    # Saúde & Pharma
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "VRTX", "REGN", "ISRG", "MDT", "SYK", "BSX", "ELV",
    # Energia
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES",
    # Consumo
    "PG", "KO", "PEP", "COST", "WMT", "MCD", "NKE", "SBUX", "TGT", "HD",
    "LOW", "TJX", "CL", "MDLZ", "GIS", "KHC", "STZ",
    # Indústria
    "CAT", "DE", "HON", "GE", "RTX", "LMT", "BA", "UPS", "UNP", "MMM",
    "ETN", "ITW", "EMR", "ROK",
    # Telecom & Mídia
    "DIS", "CMCSA", "T", "VZ", "TMUS",
    # Materiais
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX",
    # Real Estate (REITs)
    "PLD", "AMT", "CCI", "EQIX", "SPG",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL",
]

# ══════════════════════════════════════════════
# AÇÕES UK — LSE (~30)
# ══════════════════════════════════════════════
STOCKS_UK = [
    "SHEL.L", "AZN.L", "HSBA.L", "BP.L", "RIO.L", "ULVR.L", "GSK.L",
    "DGE.L", "LSEG.L", "REL.L", "NGG.L", "CRH.L", "AAL.L", "EXPN.L",
    "RKT.L", "ABF.L", "SSE.L", "BATS.L", "IMB.L", "LLOY.L", "BARC.L",
    "NWG.L", "STAN.L", "PRU.L", "ANTO.L", "GLEN.L", "VOD.L", "BT-A.L",
    "AHT.L", "SVT.L",
]

# ══════════════════════════════════════════════
# AÇÕES ALEMANHA — Xetra (~21)
# ══════════════════════════════════════════════
STOCKS_DE = [
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE", "BMW.DE",
    "BAS.DE", "BAYN.DE", "MUV2.DE", "ADS.DE", "IFX.DE", "DB1.DE",
    "HEN3.DE", "VOW3.DE", "PAH3.DE", "AIR.DE", "RWE.DE", "EON.DE",
    "FRE.DE", "BEI.DE", "MTX.DE",
]

# ══════════════════════════════════════════════
# AÇÕES FRANÇA — Euronext (~20)
# ══════════════════════════════════════════════
STOCKS_FR = [
    "MC.PA", "TTE.PA", "AIR.PA", "SAN.PA", "OR.PA", "SU.PA",
    "BNP.PA", "AI.PA", "CS.PA", "DG.PA", "KER.PA", "RI.PA",
    "BN.PA", "CAP.PA", "SGO.PA", "STM.PA", "VIV.PA", "ORA.PA",
    "EN.PA", "HO.PA",
]

# ══════════════════════════════════════════════
# AÇÕES HOLANDA/SUÍÇA — Euronext/SIX (~20)
# ══════════════════════════════════════════════
STOCKS_NL = [
    "ASML.AS", "PHIA.AS", "INGA.AS", "ABN.AS", "WKL.AS", "UNA.AS",
    "HEIA.AS", "AD.AS", "AKZA.AS", "RAND.AS",
]

STOCKS_CH = [
    "NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW", "CSGN.SW", "ZURN.SW",
    "ABBN.SW", "SREN.SW", "GIVN.SW", "LONN.SW",
]

# ══════════════════════════════════════════════
# AÇÕES JAPÃO — TSE (Nikkei 225, ~20)
# ══════════════════════════════════════════════
# Sufixo .T = Tokyo Stock Exchange. Códigos numéricos de 4 dígitos.
STOCKS_JP = [
    # Auto & Indústria
    "7203.T",  # Toyota Motor
    "7267.T",  # Honda Motor
    "6501.T",  # Hitachi
    "6367.T",  # Daikin Industries
    "6594.T",  # Nidec
    # Tech & Eletrônicos
    "6758.T",  # Sony Group
    "7974.T",  # Nintendo
    "6861.T",  # Keyence
    "8035.T",  # Tokyo Electron
    "6981.T",  # Murata Manufacturing
    # Financeiro
    "8306.T",  # Mitsubishi UFJ Financial Group
    "8316.T",  # Sumitomo Mitsui Financial Group
    "8058.T",  # Mitsubishi Corp
    # Telecom
    "9432.T",  # Nippon Telegraph and Telephone (NTT)
    "9433.T",  # KDDI
    "9984.T",  # SoftBank Group
    # Saúde & Consumo
    "4502.T",  # Takeda Pharmaceutical
    "4063.T",  # Shin-Etsu Chemical
    "6098.T",  # Recruit Holdings
    "4661.T",  # Oriental Land (Tokyo Disney)
]

# ══════════════════════════════════════════════
# AÇÕES AUSTRÁLIA — ASX 200 (~10)
# ══════════════════════════════════════════════
# Sufixo .AX = Australian Securities Exchange.
STOCKS_AU = [
    # Mineração
    "BHP.AX",   # BHP Group
    # Bancos
    "CBA.AX",   # Commonwealth Bank of Australia
    "NAB.AX",   # National Australia Bank
    "WBC.AX",   # Westpac Banking
    "ANZ.AX",   # ANZ Group
    "MQG.AX",   # Macquarie Group
    # Saúde
    "CSL.AX",   # CSL Limited
    # Varejo & Consumo
    "WES.AX",   # Wesfarmers
    "WOW.AX",   # Woolworths Group
    # Telecom
    "TLS.AX",   # Telstra
]

# ══════════════════════════════════════════════
# AÇÕES HONG KONG — HKEX (Hang Seng, ~10)
# ══════════════════════════════════════════════
# Sufixo .HK = Hong Kong Stock Exchange. Códigos numéricos de 4 dígitos com zero-pad.
STOCKS_HK = [
    # Internet & Tech
    "0700.HK",  # Tencent Holdings
    "9988.HK",  # Alibaba Group
    # Financeiro
    "0005.HK",  # HSBC Holdings
    "1299.HK",  # AIA Group
    "0939.HK",  # China Construction Bank
    "1398.HK",  # ICBC
    "2318.HK",  # Ping An Insurance
    "0388.HK",  # Hong Kong Exchanges and Clearing
    # Telecom & Energia
    "0941.HK",  # China Mobile
    "0003.HK",  # Hong Kong & China Gas (Towngas)
]

# ══════════════════════════════════════════════
# ÍNDICES GLOBAIS (16)
# ══════════════════════════════════════════════
INDICES = [
    "^GSPC",    # S&P 500
    "^IXIC",    # NASDAQ Composite
    "^DJI",     # Dow Jones
    "^BVSP",    # Ibovespa
    "^FTSE",    # FTSE 100
    "^GDAXI",   # DAX
    "^FCHI",    # CAC 40
    "^AEX",     # AEX Amsterdam
    "^STOXX50E", # Euro Stoxx 50
    "^N225",    # Nikkei 225
    "^HSI",     # Hang Seng
    "000001.SS", # Shanghai Composite
    "^AXJO",    # ASX 200
    "^GSPTSE",  # TSX Composite
    "^VIX",     # VIX (Volatilidade)
    "^RUT",     # Russell 2000
]

# ══════════════════════════════════════════════
# COMMODITIES (15)
# ══════════════════════════════════════════════
COMMODITIES = [
    "GC=F",     # Ouro
    "SI=F",     # Prata
    "PL=F",     # Platina
    "CL=F",     # WTI Crude Oil
    "BZ=F",     # Brent Crude Oil
    "NG=F",     # Gás Natural
    "RB=F",     # Gasolina RBOB
    "HO=F",     # Heating Oil
    "ZC=F",     # Milho
    "ZS=F",     # Soja
    "ZW=F",     # Trigo
    "KC=F",     # Café
    "SB=F",     # Açúcar
    "CT=F",     # Algodão
    "HG=F",     # Cobre
]

# ══════════════════════════════════════════════
# CÂMBIO — FX (16)
# ══════════════════════════════════════════════
FX = [
    "USDBRL=X",  # Dólar / Real
    "EURBRL=X",  # Euro / Real
    "EURUSD=X",  # Euro / Dólar
    "GBPUSD=X",  # Libra / Dólar
    "USDJPY=X",  # Dólar / Iene
    "USDCHF=X",  # Dólar / Franco Suíço
    "AUDUSD=X",  # Dólar Australiano / Dólar
    "USDCAD=X",  # Dólar / Dólar Canadense
    "NZDUSD=X",  # Dólar Neozelandês / Dólar
    "EURGBP=X",  # Euro / Libra
    "EURJPY=X",  # Euro / Iene
    "GBPJPY=X",  # Libra / Iene
    "USDCNY=X",  # Dólar / Yuan
    "USDINR=X",  # Dólar / Rupia Indiana
    "USDMXN=X",  # Dólar / Peso Mexicano
    "DX-Y.NYB",  # Índice DXY (Dollar Index)
]

# ══════════════════════════════════════════════
# CRIPTOMOEDAS (10)
# ══════════════════════════════════════════════
CRYPTO = [
    "BTC-USD",   # Bitcoin
    "ETH-USD",   # Ethereum
    "BNB-USD",   # Binance Coin
    "SOL-USD",   # Solana
    "XRP-USD",   # Ripple
    "ADA-USD",   # Cardano
    "DOGE-USD",  # Dogecoin
    "AVAX-USD",  # Avalanche
    "DOT-USD",   # Polkadot
    "MATIC-USD", # Polygon
]

# ══════════════════════════════════════════════
# AGREGAÇÕES
# ══════════════════════════════════════════════
ALL_STOCKS = (
    STOCKS_BR + STOCKS_US + STOCKS_UK + STOCKS_DE + STOCKS_FR + STOCKS_NL + STOCKS_CH
    + STOCKS_JP + STOCKS_AU + STOCKS_HK
)
ALL_TICKERS = ALL_STOCKS + INDICES + COMMODITIES + FX + CRYPTO

# Mapeamento tipo → lista de símbolos
SYMBOLS_BY_TYPE = {
    "stock": ALL_STOCKS,
    "index": INDICES,
    "commodity": COMMODITIES,
    "fx": FX,
    "crypto": CRYPTO,
}

# Mapeamento símbolo → país (ISO2)
def get_country_for_symbol(symbol: str) -> str:
    """Retorna o código ISO2 do país com base no sufixo do ticker."""
    if symbol.endswith(".SA"):
        return "BR"
    elif symbol.endswith(".L"):
        return "GB"
    elif symbol.endswith(".DE"):
        return "DE"
    elif symbol.endswith(".PA"):
        return "FR"
    elif symbol.endswith(".AS"):
        return "NL"
    elif symbol.endswith(".SW"):
        return "CH"
    elif symbol.endswith(".SS"):
        return "CN"
    elif symbol.endswith(".T"):
        return "JP"
    elif symbol.endswith(".AX"):
        return "AU"
    elif symbol.endswith(".HK"):
        return "HK"
    elif "=X" in symbol or symbol == "DX-Y.NYB":
        return "XX"  # Global / sem país
    elif "=F" in symbol:
        return "US"
    elif symbol.startswith("^"):
        # Mapear índices por nome
        idx_country = {
            "^GSPC": "US", "^IXIC": "US", "^DJI": "US", "^RUT": "US", "^VIX": "US",
            "^BVSP": "BR", "^FTSE": "GB", "^GDAXI": "DE", "^FCHI": "FR",
            "^AEX": "NL", "^STOXX50E": "DE", "^N225": "JP", "^HSI": "CN",
            "^AXJO": "AU", "^GSPTSE": "CA",
        }
        return idx_country.get(symbol, "US")
    elif "-USD" in symbol:
        return "XX"  # Cripto
    else:
        return "US"  # Default: ações sem sufixo = EUA


def get_total_count():
    """Retorna contagem total de tickers."""
    return len(ALL_TICKERS)


if __name__ == "__main__":
    print(f"Total de tickers: {get_total_count()}")
    for tipo, lista in SYMBOLS_BY_TYPE.items():
        print(f"  {tipo}: {len(lista)}")
