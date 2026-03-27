"""
~600 tickers organizados por tipo de ativo e país.
Cada entrada: (symbol, name, asset_type, country)
"""

# ══════════════════════════════════════════════════════════
#  STOCKS — Brasil (.SA)
# ══════════════════════════════════════════════════════════
STOCKS_BR = [
    ("PETR4.SA", "Petrobras PN", "stock", "BR"),
    ("VALE3.SA", "Vale ON", "stock", "BR"),
    ("ITUB4.SA", "Itaú Unibanco PN", "stock", "BR"),
    ("BBDC4.SA", "Bradesco PN", "stock", "BR"),
    ("ABEV3.SA", "Ambev ON", "stock", "BR"),
    ("WEGE3.SA", "WEG ON", "stock", "BR"),
    ("RENT3.SA", "Localiza ON", "stock", "BR"),
    ("BBAS3.SA", "Banco do Brasil ON", "stock", "BR"),
    ("SUZB3.SA", "Suzano ON", "stock", "BR"),
    ("JBSS3.SA", "JBS ON", "stock", "BR"),
    ("ELET3.SA", "Eletrobras ON", "stock", "BR"),
    ("ELET6.SA", "Eletrobras PNB", "stock", "BR"),
    ("B3SA3.SA", "B3 ON", "stock", "BR"),
    ("RADL3.SA", "Raia Drogasil ON", "stock", "BR"),
    ("LREN3.SA", "Lojas Renner ON", "stock", "BR"),
    ("EMBR3.SA", "Embraer ON", "stock", "BR"),
    ("MGLU3.SA", "Magazine Luiza ON", "stock", "BR"),
    ("VIVT3.SA", "Telefônica Brasil ON", "stock", "BR"),
    ("GGBR4.SA", "Gerdau PN", "stock", "BR"),
    ("CSNA3.SA", "CSN ON", "stock", "BR"),
    ("CPLE6.SA", "Copel PNB", "stock", "BR"),
    ("CMIG4.SA", "Cemig PN", "stock", "BR"),
    ("TAEE11.SA", "Taesa UNT", "stock", "BR"),
    ("SBSP3.SA", "Sabesp ON", "stock", "BR"),
    ("ENEV3.SA", "Eneva ON", "stock", "BR"),
    ("PRIO3.SA", "PRIO ON", "stock", "BR"),
    ("CSAN3.SA", "Cosan ON", "stock", "BR"),
    ("UGPA3.SA", "Ultrapar ON", "stock", "BR"),
    ("KLBN11.SA", "Klabin UNT", "stock", "BR"),
    ("TOTS3.SA", "TOTVS ON", "stock", "BR"),
    ("RDOR3.SA", "Rede D'Or ON", "stock", "BR"),
    ("HAPV3.SA", "Hapvida ON", "stock", "BR"),
    ("RAIL3.SA", "Rumo ON", "stock", "BR"),
    ("CCRO3.SA", "CCR ON", "stock", "BR"),
    ("EQTL3.SA", "Equatorial ON", "stock", "BR"),
    ("NTCO3.SA", "Natura ON", "stock", "BR"),
    ("BPAC11.SA", "BTG Pactual UNT", "stock", "BR"),
    ("CYRE3.SA", "Cyrela ON", "stock", "BR"),
    ("MRVE3.SA", "MRV ON", "stock", "BR"),
    ("COGN3.SA", "Cogna ON", "stock", "BR"),
    ("YDUQ3.SA", "Yduqs ON", "stock", "BR"),
    ("GOAU4.SA", "Metalúrgica Gerdau PN", "stock", "BR"),
    ("BRKM5.SA", "Braskem PNA", "stock", "BR"),
    ("STBP3.SA", "Santos Brasil ON", "stock", "BR"),
    ("BRFS3.SA", "BRF ON", "stock", "BR"),
    ("MRFG3.SA", "Marfrig ON", "stock", "BR"),
    ("BEEF3.SA", "Minerva ON", "stock", "BR"),
    ("SLCE3.SA", "SLC Agrícola ON", "stock", "BR"),
    ("SMTO3.SA", "São Martinho ON", "stock", "BR"),
    ("RAIZ4.SA", "Raízen PN", "stock", "BR"),
    ("VBBR3.SA", "Vibra Energia ON", "stock", "BR"),
    ("MULT3.SA", "Multiplan ON", "stock", "BR"),
    ("IGTI11.SA", "Iguatemi UNT", "stock", "BR"),
    ("ALSO3.SA", "Allos ON", "stock", "BR"),
    ("IRBR3.SA", "IRB Brasil ON", "stock", "BR"),
    ("SANB11.SA", "Santander Brasil UNT", "stock", "BR"),
    ("ITSA4.SA", "Itaúsa PN", "stock", "BR"),
    ("FLRY3.SA", "Fleury ON", "stock", "BR"),
    ("QUAL3.SA", "Qualicorp ON", "stock", "BR"),
    ("LWSA3.SA", "Locaweb ON", "stock", "BR"),
    ("CASH3.SA", "Meliuz ON", "stock", "BR"),
    ("PETZ3.SA", "Petz ON", "stock", "BR"),
    ("ASAI3.SA", "Assaí ON", "stock", "BR"),
    ("CRFB3.SA", "Carrefour Brasil ON", "stock", "BR"),
    ("ARZZ3.SA", "Arezzo ON", "stock", "BR"),
    ("SOMA3.SA", "Grupo Soma ON", "stock", "BR"),
    ("VIVA3.SA", "Vivara ON", "stock", "BR"),
    ("AURE3.SA", "Auren Energia ON", "stock", "BR"),
    ("CPFE3.SA", "CPFL Energia ON", "stock", "BR"),
    ("ENBR3.SA", "Energias do Brasil ON", "stock", "BR"),
    ("TRPL4.SA", "Transmissão Paulista PN", "stock", "BR"),
    ("AESB3.SA", "AES Brasil ON", "stock", "BR"),
    ("NEOE3.SA", "Neoenergia ON", "stock", "BR"),
    ("TIMS3.SA", "TIM ON", "stock", "BR"),
    ("OIBR3.SA", "Oi ON", "stock", "BR"),
    ("AZUL4.SA", "Azul PN", "stock", "BR"),
    ("GOLL4.SA", "GOL PN", "stock", "BR"),
    ("CVCB3.SA", "CVC ON", "stock", "BR"),
    ("HYPE3.SA", "Hypera ON", "stock", "BR"),
    ("DXCO3.SA", "Dexco ON", "stock", "BR"),
]

# ══════════════════════════════════════════════════════════
#  STOCKS — EUA
# ══════════════════════════════════════════════════════════
STOCKS_US = [
    ("AAPL", "Apple Inc", "stock", "US"),
    ("MSFT", "Microsoft Corp", "stock", "US"),
    ("AMZN", "Amazon.com Inc", "stock", "US"),
    ("GOOGL", "Alphabet Inc A", "stock", "US"),
    ("META", "Meta Platforms Inc", "stock", "US"),
    ("NVDA", "NVIDIA Corp", "stock", "US"),
    ("TSLA", "Tesla Inc", "stock", "US"),
    ("BRK-B", "Berkshire Hathaway B", "stock", "US"),
    ("JPM", "JPMorgan Chase & Co", "stock", "US"),
    ("V", "Visa Inc", "stock", "US"),
    ("JNJ", "Johnson & Johnson", "stock", "US"),
    ("UNH", "UnitedHealth Group", "stock", "US"),
    ("HD", "Home Depot Inc", "stock", "US"),
    ("PG", "Procter & Gamble", "stock", "US"),
    ("MA", "Mastercard Inc", "stock", "US"),
    ("DIS", "Walt Disney Co", "stock", "US"),
    ("ADBE", "Adobe Inc", "stock", "US"),
    ("CRM", "Salesforce Inc", "stock", "US"),
    ("NFLX", "Netflix Inc", "stock", "US"),
    ("PFE", "Pfizer Inc", "stock", "US"),
    ("KO", "Coca-Cola Co", "stock", "US"),
    ("PEP", "PepsiCo Inc", "stock", "US"),
    ("COST", "Costco Wholesale", "stock", "US"),
    ("TMO", "Thermo Fisher Scientific", "stock", "US"),
    ("AVGO", "Broadcom Inc", "stock", "US"),
    ("CSCO", "Cisco Systems", "stock", "US"),
    ("ABT", "Abbott Laboratories", "stock", "US"),
    ("ACN", "Accenture plc", "stock", "US"),
    ("MRK", "Merck & Co", "stock", "US"),
    ("WMT", "Walmart Inc", "stock", "US"),
    ("XOM", "Exxon Mobil Corp", "stock", "US"),
    ("CVX", "Chevron Corp", "stock", "US"),
    ("LLY", "Eli Lilly and Co", "stock", "US"),
    ("AMD", "Advanced Micro Devices", "stock", "US"),
    ("INTC", "Intel Corp", "stock", "US"),
    ("QCOM", "Qualcomm Inc", "stock", "US"),
    ("TXN", "Texas Instruments", "stock", "US"),
    ("NOW", "ServiceNow Inc", "stock", "US"),
    ("IBM", "IBM Corp", "stock", "US"),
    ("GS", "Goldman Sachs", "stock", "US"),
    ("MS", "Morgan Stanley", "stock", "US"),
    ("BAC", "Bank of America", "stock", "US"),
    ("C", "Citigroup Inc", "stock", "US"),
    ("WFC", "Wells Fargo & Co", "stock", "US"),
    ("AXP", "American Express", "stock", "US"),
    ("BLK", "BlackRock Inc", "stock", "US"),
    ("SCHW", "Charles Schwab", "stock", "US"),
    ("SPGI", "S&P Global", "stock", "US"),
    ("CB", "Chubb Ltd", "stock", "US"),
    ("MMC", "Marsh & McLennan", "stock", "US"),
    ("CAT", "Caterpillar Inc", "stock", "US"),
    ("DE", "Deere & Co", "stock", "US"),
    ("GE", "GE Aerospace", "stock", "US"),
    ("HON", "Honeywell International", "stock", "US"),
    ("BA", "Boeing Co", "stock", "US"),
    ("RTX", "RTX Corp", "stock", "US"),
    ("LMT", "Lockheed Martin", "stock", "US"),
    ("UPS", "United Parcel Service", "stock", "US"),
    ("FDX", "FedEx Corp", "stock", "US"),
    ("NEE", "NextEra Energy", "stock", "US"),
    ("DUK", "Duke Energy", "stock", "US"),
    ("SO", "Southern Co", "stock", "US"),
    ("D", "Dominion Energy", "stock", "US"),
    ("SRE", "Sempra Energy", "stock", "US"),
    ("ORCL", "Oracle Corp", "stock", "US"),
    ("INTU", "Intuit Inc", "stock", "US"),
    ("PANW", "Palo Alto Networks", "stock", "US"),
    ("SNPS", "Synopsys Inc", "stock", "US"),
    ("CDNS", "Cadence Design Systems", "stock", "US"),
    ("AMAT", "Applied Materials", "stock", "US"),
    ("LRCX", "Lam Research", "stock", "US"),
    ("KLAC", "KLA Corp", "stock", "US"),
    ("MU", "Micron Technology", "stock", "US"),
    ("MRVL", "Marvell Technology", "stock", "US"),
    ("UBER", "Uber Technologies", "stock", "US"),
    ("ABNB", "Airbnb Inc", "stock", "US"),
    ("SQ", "Block Inc", "stock", "US"),
    ("PYPL", "PayPal Holdings", "stock", "US"),
    ("COIN", "Coinbase Global", "stock", "US"),
    ("SNOW", "Snowflake Inc", "stock", "US"),
    ("DDOG", "Datadog Inc", "stock", "US"),
    ("ZS", "Zscaler Inc", "stock", "US"),
    ("NET", "Cloudflare Inc", "stock", "US"),
    ("PLTR", "Palantir Technologies", "stock", "US"),
    ("ARM", "Arm Holdings", "stock", "US"),
    ("SMCI", "Super Micro Computer", "stock", "US"),
    ("MELI", "MercadoLibre Inc", "stock", "US"),
    ("NU", "Nu Holdings", "stock", "US"),
    ("STNE", "StoneCo Ltd", "stock", "US"),
    ("PAGS", "PagSeguro Digital", "stock", "US"),
    ("XP", "XP Inc", "stock", "US"),
]

# ══════════════════════════════════════════════════════════
#  STOCKS — Europa
# ══════════════════════════════════════════════════════════
STOCKS_EU = [
    ("NESN.SW", "Nestlé SA", "stock", "CH"),
    ("ROG.SW", "Roche Holding", "stock", "CH"),
    ("NOVN.SW", "Novartis AG", "stock", "CH"),
    ("MC.PA", "LVMH", "stock", "FR"),
    ("OR.PA", "L'Oréal", "stock", "FR"),
    ("TTE.PA", "TotalEnergies SE", "stock", "FR"),
    ("SAN.PA", "Sanofi SA", "stock", "FR"),
    ("AIR.PA", "Airbus SE", "stock", "FR"),
    ("SU.PA", "Schneider Electric", "stock", "FR"),
    ("BNP.PA", "BNP Paribas", "stock", "FR"),
    ("SAP.DE", "SAP SE", "stock", "DE"),
    ("SIE.DE", "Siemens AG", "stock", "DE"),
    ("ALV.DE", "Allianz SE", "stock", "DE"),
    ("DTE.DE", "Deutsche Telekom", "stock", "DE"),
    ("BAS.DE", "BASF SE", "stock", "DE"),
    ("BMW.DE", "BMW AG", "stock", "DE"),
    ("VOW3.DE", "Volkswagen AG", "stock", "DE"),
    ("MBG.DE", "Mercedes-Benz Group", "stock", "DE"),
    ("AZN.L", "AstraZeneca plc", "stock", "GB"),
    ("SHEL.L", "Shell plc", "stock", "GB"),
    ("HSBA.L", "HSBC Holdings", "stock", "GB"),
    ("ULVR.L", "Unilever plc", "stock", "GB"),
    ("GSK.L", "GSK plc", "stock", "GB"),
    ("RIO.L", "Rio Tinto plc", "stock", "GB"),
    ("BP.L", "BP plc", "stock", "GB"),
    ("DGE.L", "Diageo plc", "stock", "GB"),
    ("BARC.L", "Barclays plc", "stock", "GB"),
    ("LSEG.L", "London Stock Exchange", "stock", "GB"),
    ("ASML.AS", "ASML Holding", "stock", "NL"),
    ("INGA.AS", "ING Group", "stock", "NL"),
    ("PHIA.AS", "Koninklijke Philips", "stock", "NL"),
    ("ISP.MI", "Intesa Sanpaolo", "stock", "IT"),
    ("ENI.MI", "Eni SpA", "stock", "IT"),
    ("ENEL.MI", "Enel SpA", "stock", "IT"),
    ("UCG.MI", "UniCredit SpA", "stock", "IT"),
    ("SAN.MC", "Banco Santander", "stock", "ES"),
    ("IBE.MC", "Iberdrola SA", "stock", "ES"),
    ("TEF.MC", "Telefónica SA", "stock", "ES"),
    ("BBVA.MC", "BBVA SA", "stock", "ES"),
]

# ══════════════════════════════════════════════════════════
#  STOCKS — Ásia & Oceania
# ══════════════════════════════════════════════════════════
STOCKS_ASIA = [
    ("7203.T", "Toyota Motor", "stock", "JP"),
    ("6758.T", "Sony Group", "stock", "JP"),
    ("6861.T", "Keyence Corp", "stock", "JP"),
    ("9984.T", "SoftBank Group", "stock", "JP"),
    ("8306.T", "Mitsubishi UFJ Financial", "stock", "JP"),
    ("6902.T", "Denso Corp", "stock", "JP"),
    ("9432.T", "Nippon Telegraph", "stock", "JP"),
    ("7267.T", "Honda Motor", "stock", "JP"),
    ("005930.KS", "Samsung Electronics", "stock", "KR"),
    ("000660.KS", "SK Hynix", "stock", "KR"),
    ("035420.KS", "Naver Corp", "stock", "KR"),
    ("0700.HK", "Tencent Holdings", "stock", "HK"),
    ("9988.HK", "Alibaba Group", "stock", "HK"),
    ("3690.HK", "Meituan", "stock", "HK"),
    ("1299.HK", "AIA Group", "stock", "HK"),
    ("2318.HK", "Ping An Insurance", "stock", "CN"),
    ("0939.HK", "CCB", "stock", "CN"),
    ("RELIANCE.NS", "Reliance Industries", "stock", "IN"),
    ("TCS.NS", "Tata Consultancy", "stock", "IN"),
    ("INFY.NS", "Infosys Ltd", "stock", "IN"),
    ("HDFCBANK.NS", "HDFC Bank", "stock", "IN"),
    ("BHP.AX", "BHP Group", "stock", "AU"),
    ("CBA.AX", "Commonwealth Bank", "stock", "AU"),
    ("CSL.AX", "CSL Ltd", "stock", "AU"),
    ("NAB.AX", "National Australia Bank", "stock", "AU"),
]

# ══════════════════════════════════════════════════════════
#  STOCKS — Latam (exceto Brasil)
# ══════════════════════════════════════════════════════════
STOCKS_LATAM = [
    ("AMXL.MX", "América Móvil", "stock", "MX"),
    ("WALMEX.MX", "Walmart de México", "stock", "MX"),
    ("FEMSAUBD.MX", "FEMSA", "stock", "MX"),
    ("GFNORTEO.MX", "Banorte", "stock", "MX"),
    ("CEMEXCPO.MX", "Cemex", "stock", "MX"),
    ("TLEVICPO.MX", "Televisa", "stock", "MX"),
    ("BIMBOA.MX", "Grupo Bimbo", "stock", "MX"),
    ("FALABELLA.SN", "Falabella", "stock", "CL"),
    ("COPEC.SN", "Empresas Copec", "stock", "CL"),
    ("SQM-B.SN", "SQM", "stock", "CL"),
    ("ECOPETL.BVC", "Ecopetrol", "stock", "CO"),
    ("BVN", "Buenaventura Mining", "stock", "PE"),
    ("CREDICORP", "Credicorp Ltd", "stock", "PE"),
    ("YPF", "YPF SA", "stock", "AR"),
    ("GGAL", "Grupo Financiero Galicia", "stock", "AR"),
]

# ══════════════════════════════════════════════════════════
#  ÍNDICES
# ══════════════════════════════════════════════════════════
INDICES = [
    ("^BVSP", "Ibovespa", "index", "BR"),
    ("^GSPC", "S&P 500", "index", "US"),
    ("^DJI", "Dow Jones Industrial", "index", "US"),
    ("^IXIC", "NASDAQ Composite", "index", "US"),
    ("^RUT", "Russell 2000", "index", "US"),
    ("^VIX", "CBOE Volatility Index", "index", "US"),
    ("^FTSE", "FTSE 100", "index", "GB"),
    ("^GDAXI", "DAX", "index", "DE"),
    ("^FCHI", "CAC 40", "index", "FR"),
    ("^STOXX50E", "Euro Stoxx 50", "index", "EU"),
    ("^N225", "Nikkei 225", "index", "JP"),
    ("^HSI", "Hang Seng", "index", "HK"),
    ("000001.SS", "Shanghai Composite", "index", "CN"),
    ("^NSEI", "Nifty 50", "index", "IN"),
    ("^BSESN", "BSE Sensex", "index", "IN"),
    ("^AXJO", "ASX 200", "index", "AU"),
    ("^KS11", "KOSPI", "index", "KR"),
    ("^MXX", "IPC México", "index", "MX"),
    ("^MERV", "MERVAL", "index", "AR"),
    ("^IPSA", "IPSA Chile", "index", "CL"),
]

# ══════════════════════════════════════════════════════════
#  COMMODITIES
# ══════════════════════════════════════════════════════════
COMMODITIES = [
    ("CL=F", "Crude Oil WTI", "commodity", "GLOBAL"),
    ("BZ=F", "Brent Crude Oil", "commodity", "GLOBAL"),
    ("GC=F", "Gold", "commodity", "GLOBAL"),
    ("SI=F", "Silver", "commodity", "GLOBAL"),
    ("PL=F", "Platinum", "commodity", "GLOBAL"),
    ("PA=F", "Palladium", "commodity", "GLOBAL"),
    ("HG=F", "Copper", "commodity", "GLOBAL"),
    ("NG=F", "Natural Gas", "commodity", "GLOBAL"),
    ("ZC=F", "Corn", "commodity", "GLOBAL"),
    ("ZS=F", "Soybeans", "commodity", "GLOBAL"),
    ("ZW=F", "Wheat", "commodity", "GLOBAL"),
    ("KC=F", "Coffee", "commodity", "GLOBAL"),
    ("SB=F", "Sugar", "commodity", "GLOBAL"),
    ("CT=F", "Cotton", "commodity", "GLOBAL"),
    ("CC=F", "Cocoa", "commodity", "GLOBAL"),
    ("LE=F", "Live Cattle", "commodity", "GLOBAL"),
    ("HE=F", "Lean Hogs", "commodity", "GLOBAL"),
    ("LBS=F", "Lumber", "commodity", "GLOBAL"),
    ("RB=F", "RBOB Gasoline", "commodity", "GLOBAL"),
    ("HO=F", "Heating Oil", "commodity", "GLOBAL"),
]

# ══════════════════════════════════════════════════════════
#  FOREX
# ══════════════════════════════════════════════════════════
FOREX = [
    ("USDBRL=X", "USD/BRL", "fx", "BR"),
    ("EURBRL=X", "EUR/BRL", "fx", "BR"),
    ("GBPBRL=X", "GBP/BRL", "fx", "BR"),
    ("EURUSD=X", "EUR/USD", "fx", "GLOBAL"),
    ("GBPUSD=X", "GBP/USD", "fx", "GLOBAL"),
    ("USDJPY=X", "USD/JPY", "fx", "GLOBAL"),
    ("USDCHF=X", "USD/CHF", "fx", "GLOBAL"),
    ("AUDUSD=X", "AUD/USD", "fx", "GLOBAL"),
    ("NZDUSD=X", "NZD/USD", "fx", "GLOBAL"),
    ("USDCAD=X", "USD/CAD", "fx", "GLOBAL"),
    ("USDCNY=X", "USD/CNY", "fx", "GLOBAL"),
    ("USDMXN=X", "USD/MXN", "fx", "MX"),
    ("USDARS=X", "USD/ARS", "fx", "AR"),
    ("USDCLP=X", "USD/CLP", "fx", "CL"),
    ("USDCOP=X", "USD/COP", "fx", "CO"),
    ("EURGBP=X", "EUR/GBP", "fx", "GLOBAL"),
    ("EURJPY=X", "EUR/JPY", "fx", "GLOBAL"),
    ("GBPJPY=X", "GBP/JPY", "fx", "GLOBAL"),
    ("USDINR=X", "USD/INR", "fx", "IN"),
    ("USDKRW=X", "USD/KRW", "fx", "KR"),
]

# ══════════════════════════════════════════════════════════
#  CRYPTO
# ══════════════════════════════════════════════════════════
CRYPTO = [
    ("BTC-USD", "Bitcoin", "crypto", "GLOBAL"),
    ("ETH-USD", "Ethereum", "crypto", "GLOBAL"),
    ("BNB-USD", "Binance Coin", "crypto", "GLOBAL"),
    ("SOL-USD", "Solana", "crypto", "GLOBAL"),
    ("XRP-USD", "Ripple", "crypto", "GLOBAL"),
    ("ADA-USD", "Cardano", "crypto", "GLOBAL"),
    ("DOGE-USD", "Dogecoin", "crypto", "GLOBAL"),
    ("AVAX-USD", "Avalanche", "crypto", "GLOBAL"),
    ("DOT-USD", "Polkadot", "crypto", "GLOBAL"),
    ("LINK-USD", "Chainlink", "crypto", "GLOBAL"),
    ("MATIC-USD", "Polygon", "crypto", "GLOBAL"),
    ("UNI7083-USD", "Uniswap", "crypto", "GLOBAL"),
    ("ATOM-USD", "Cosmos", "crypto", "GLOBAL"),
    ("LTC-USD", "Litecoin", "crypto", "GLOBAL"),
    ("FIL-USD", "Filecoin", "crypto", "GLOBAL"),
    ("NEAR-USD", "NEAR Protocol", "crypto", "GLOBAL"),
    ("APT21794-USD", "Aptos", "crypto", "GLOBAL"),
    ("OP-USD", "Optimism", "crypto", "GLOBAL"),
    ("ARB11841-USD", "Arbitrum", "crypto", "GLOBAL"),
    ("AAVE-USD", "Aave", "crypto", "GLOBAL"),
]

# ══════════════════════════════════════════════════════════
#  ETFs
# ══════════════════════════════════════════════════════════
ETFS = [
    # Brasil
    ("BOVA11.SA", "iShares Ibovespa", "etf", "BR"),
    ("IVVB11.SA", "iShares S&P 500 BRL", "etf", "BR"),
    ("SMAL11.SA", "iShares Small Cap BR", "etf", "BR"),
    ("HASH11.SA", "Hashdex Crypto Index", "etf", "BR"),
    ("IMAB11.SA", "Itaú IMA-B", "etf", "BR"),
    ("DIVO11.SA", "It Now Dividendos", "etf", "BR"),
    ("XFIX11.SA", "FIIs Index", "etf", "BR"),
    # EUA
    ("SPY", "SPDR S&P 500", "etf", "US"),
    ("QQQ", "Invesco NASDAQ 100", "etf", "US"),
    ("IWM", "iShares Russell 2000", "etf", "US"),
    ("VTI", "Vanguard Total Stock Market", "etf", "US"),
    ("VOO", "Vanguard S&P 500", "etf", "US"),
    ("DIA", "SPDR Dow Jones", "etf", "US"),
    ("EWZ", "iShares MSCI Brazil", "etf", "US"),
    ("EEM", "iShares MSCI Emerging Markets", "etf", "US"),
    ("VWO", "Vanguard FTSE Emerging Markets", "etf", "US"),
    ("GLD", "SPDR Gold Trust", "etf", "US"),
    ("SLV", "iShares Silver Trust", "etf", "US"),
    ("TLT", "iShares 20+ Year Treasury", "etf", "US"),
    ("HYG", "iShares High Yield Corporate", "etf", "US"),
    ("LQD", "iShares Investment Grade Corporate", "etf", "US"),
    ("XLE", "Energy Select SPDR", "etf", "US"),
    ("XLF", "Financial Select SPDR", "etf", "US"),
    ("XLK", "Technology Select SPDR", "etf", "US"),
    ("XLV", "Health Care Select SPDR", "etf", "US"),
    ("XLI", "Industrial Select SPDR", "etf", "US"),
    ("XLP", "Consumer Staples Select SPDR", "etf", "US"),
    ("XLY", "Consumer Discretionary Select SPDR", "etf", "US"),
    ("XLU", "Utilities Select SPDR", "etf", "US"),
    ("XLRE", "Real Estate Select SPDR", "etf", "US"),
    ("XLC", "Communication Services Select SPDR", "etf", "US"),
    ("XLB", "Materials Select SPDR", "etf", "US"),
    ("ARKK", "ARK Innovation", "etf", "US"),
    ("ARKG", "ARK Genomic Revolution", "etf", "US"),
    ("SOXX", "iShares Semiconductor", "etf", "US"),
    ("SMH", "VanEck Semiconductor", "etf", "US"),
    ("KWEB", "KraneShares CSI China Internet", "etf", "US"),
    ("VGK", "Vanguard FTSE Europe", "etf", "US"),
    ("EWJ", "iShares MSCI Japan", "etf", "US"),
    ("FXI", "iShares China Large-Cap", "etf", "US"),
    ("INDA", "iShares MSCI India", "etf", "US"),
]

# ══════════════════════════════════════════════════════════
#  AGREGAÇÃO
# ══════════════════════════════════════════════════════════

ALL_SYMBOLS = (
    STOCKS_BR
    + STOCKS_US
    + STOCKS_EU
    + STOCKS_ASIA
    + STOCKS_LATAM
    + INDICES
    + COMMODITIES
    + FOREX
    + CRYPTO
    + ETFS
)

# Mapas de lookup rápido
SYMBOL_MAP = {s[0]: {"name": s[1], "asset_type": s[2], "country": s[3]} for s in ALL_SYMBOLS}

SYMBOLS_BY_TYPE = {}
for sym, name, atype, country in ALL_SYMBOLS:
    SYMBOLS_BY_TYPE.setdefault(atype, []).append(sym)

SYMBOLS_BY_COUNTRY = {}
for sym, name, atype, country in ALL_SYMBOLS:
    SYMBOLS_BY_COUNTRY.setdefault(country, []).append(sym)


def get_symbols(
    asset_type: str | None = None,
    country: str | None = None,
) -> list[tuple[str, str, str, str]]:
    """Filtra símbolos por tipo e/ou país."""
    result = ALL_SYMBOLS
    if asset_type:
        result = [s for s in result if s[2] == asset_type.lower()]
    if country:
        result = [s for s in result if s[3].upper() == country.upper()]
    return result


# Contagem rápida
TOTAL_SYMBOLS = len(ALL_SYMBOLS)
