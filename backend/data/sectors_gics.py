"""
data/sectors_gics.py
34 setores GICS com nome em PT-BR, 12 países, mapeamento de tickers para setores.
"""

# ══════════════════════════════════════════════
# SETORES GICS (Global Industry Classification Standard)
# ══════════════════════════════════════════════
SECTORS_GICS = [
    # Energy
    {"sector": "Energy", "sector_pt": "Energia", "industry_group": "Energy",
     "industry": "Oil, Gas & Consumable Fuels", "sub_industry": "Integrated Oil & Gas", "gics_code": "10101010"},
    {"sector": "Energy", "sector_pt": "Energia", "industry_group": "Energy",
     "industry": "Oil, Gas & Consumable Fuels", "sub_industry": "Exploration & Production", "gics_code": "10101020"},
    {"sector": "Energy", "sector_pt": "Energia", "industry_group": "Energy",
     "industry": "Energy Equipment & Services", "sub_industry": "Oil & Gas Equipment & Services", "gics_code": "10102010"},
    # Materials
    {"sector": "Materials", "sector_pt": "Materiais", "industry_group": "Materials",
     "industry": "Metals & Mining", "sub_industry": "Diversified Metals & Mining", "gics_code": "15104020"},
    {"sector": "Materials", "sector_pt": "Materiais", "industry_group": "Materials",
     "industry": "Metals & Mining", "sub_industry": "Steel", "gics_code": "15104050"},
    {"sector": "Materials", "sector_pt": "Materiais", "industry_group": "Materials",
     "industry": "Chemicals", "sub_industry": "Diversified Chemicals", "gics_code": "15101010"},
    # Industrials
    {"sector": "Industrials", "sector_pt": "Industriais", "industry_group": "Capital Goods",
     "industry": "Machinery", "sub_industry": "Industrial Machinery", "gics_code": "20106010"},
    {"sector": "Industrials", "sector_pt": "Industriais", "industry_group": "Capital Goods",
     "industry": "Aerospace & Defense", "sub_industry": "Aerospace & Defense", "gics_code": "20101010"},
    {"sector": "Industrials", "sector_pt": "Industriais", "industry_group": "Transportation",
     "industry": "Road & Rail", "sub_industry": "Railroads", "gics_code": "20304010"},
    # Consumer Discretionary
    {"sector": "Consumer Discretionary", "sector_pt": "Consumo Discricionário", "industry_group": "Retailing",
     "industry": "Specialty Retail", "sub_industry": "Apparel Retail", "gics_code": "25504020"},
    {"sector": "Consumer Discretionary", "sector_pt": "Consumo Discricionário", "industry_group": "Automobiles & Components",
     "industry": "Automobiles", "sub_industry": "Automobile Manufacturers", "gics_code": "25102010"},
    # Consumer Staples
    {"sector": "Consumer Staples", "sector_pt": "Consumo Básico", "industry_group": "Food, Beverage & Tobacco",
     "industry": "Beverages", "sub_industry": "Soft Drinks", "gics_code": "30201020"},
    {"sector": "Consumer Staples", "sector_pt": "Consumo Básico", "industry_group": "Food & Staples Retailing",
     "industry": "Food & Staples Retailing", "sub_industry": "Food Distributors", "gics_code": "30101020"},
    {"sector": "Consumer Staples", "sector_pt": "Consumo Básico", "industry_group": "Food, Beverage & Tobacco",
     "industry": "Food Products", "sub_industry": "Packaged Foods & Meats", "gics_code": "30202030"},
    # Health Care
    {"sector": "Health Care", "sector_pt": "Saúde", "industry_group": "Pharmaceuticals, Biotechnology & Life Sciences",
     "industry": "Pharmaceuticals", "sub_industry": "Pharmaceuticals", "gics_code": "35202010"},
    {"sector": "Health Care", "sector_pt": "Saúde", "industry_group": "Health Care Equipment & Services",
     "industry": "Health Care Providers & Services", "sub_industry": "Managed Health Care", "gics_code": "35102030"},
    {"sector": "Health Care", "sector_pt": "Saúde", "industry_group": "Pharmaceuticals, Biotechnology & Life Sciences",
     "industry": "Biotechnology", "sub_industry": "Biotechnology", "gics_code": "35201010"},
    # Financials
    {"sector": "Financials", "sector_pt": "Financeiro", "industry_group": "Banks",
     "industry": "Banks", "sub_industry": "Diversified Banks", "gics_code": "40101010"},
    {"sector": "Financials", "sector_pt": "Financeiro", "industry_group": "Diversified Financials",
     "industry": "Capital Markets", "sub_industry": "Asset Management & Custody Banks", "gics_code": "40203010"},
    {"sector": "Financials", "sector_pt": "Financeiro", "industry_group": "Insurance",
     "industry": "Insurance", "sub_industry": "Multi-line Insurance", "gics_code": "40301020"},
    # Information Technology
    {"sector": "Information Technology", "sector_pt": "Tecnologia da Informação", "industry_group": "Software & Services",
     "industry": "Software", "sub_industry": "Systems Software", "gics_code": "45103010"},
    {"sector": "Information Technology", "sector_pt": "Tecnologia da Informação", "industry_group": "Semiconductors & Semiconductor Equipment",
     "industry": "Semiconductors & Semiconductor Equipment", "sub_industry": "Semiconductors", "gics_code": "45301020"},
    {"sector": "Information Technology", "sector_pt": "Tecnologia da Informação", "industry_group": "Technology Hardware & Equipment",
     "industry": "Technology Hardware, Storage & Peripherals", "sub_industry": "Technology Hardware", "gics_code": "45201020"},
    # Communication Services
    {"sector": "Communication Services", "sector_pt": "Serviços de Comunicação", "industry_group": "Media & Entertainment",
     "industry": "Interactive Media & Services", "sub_industry": "Interactive Media & Services", "gics_code": "50203010"},
    {"sector": "Communication Services", "sector_pt": "Serviços de Comunicação", "industry_group": "Telecommunication Services",
     "industry": "Diversified Telecommunication Services", "sub_industry": "Integrated Telecommunication Services", "gics_code": "50101020"},
    # Utilities
    {"sector": "Utilities", "sector_pt": "Utilidades Públicas", "industry_group": "Utilities",
     "industry": "Electric Utilities", "sub_industry": "Electric Utilities", "gics_code": "55101010"},
    {"sector": "Utilities", "sector_pt": "Utilidades Públicas", "industry_group": "Utilities",
     "industry": "Multi-Utilities", "sub_industry": "Multi-Utilities", "gics_code": "55105010"},
    {"sector": "Utilities", "sector_pt": "Utilidades Públicas", "industry_group": "Utilities",
     "industry": "Water Utilities", "sub_industry": "Water Utilities", "gics_code": "55104010"},
    # Real Estate
    {"sector": "Real Estate", "sector_pt": "Imobiliário", "industry_group": "Equity Real Estate Investment Trusts (REITs)",
     "industry": "Equity Real Estate Investment Trusts (REITs)", "sub_industry": "Industrial REITs", "gics_code": "60101010"},
    {"sector": "Real Estate", "sector_pt": "Imobiliário", "industry_group": "Real Estate Management & Development",
     "industry": "Real Estate Management & Development", "sub_industry": "Real Estate Operating Companies", "gics_code": "60201010"},
    # Adicionais para cobertura BR
    {"sector": "Industrials", "sector_pt": "Industriais", "industry_group": "Transportation",
     "industry": "Transportation Infrastructure", "sub_industry": "Highways & Railtracks", "gics_code": "20305020"},
    {"sector": "Consumer Discretionary", "sector_pt": "Consumo Discricionário", "industry_group": "Consumer Services",
     "industry": "Hotels, Restaurants & Leisure", "sub_industry": "Restaurants", "gics_code": "25301040"},
    {"sector": "Financials", "sector_pt": "Financeiro", "industry_group": "Diversified Financials",
     "industry": "Financial Services", "sub_industry": "Financial Exchanges & Data", "gics_code": "40204010"},
    {"sector": "Consumer Staples", "sector_pt": "Consumo Básico", "industry_group": "Household & Personal Products",
     "industry": "Personal Products", "sub_industry": "Personal Products", "gics_code": "30302010"},
]

# ══════════════════════════════════════════════
# PAÍSES (12)
# ══════════════════════════════════════════════
COUNTRIES = [
    {"iso2": "BR", "iso3": "BRA", "name": "Brazil", "name_pt": "Brasil",
     "region": "Americas", "currency_code": "BRL", "main_exchange": "B3", "yf_suffix": ".SA"},
    {"iso2": "US", "iso3": "USA", "name": "United States", "name_pt": "Estados Unidos",
     "region": "Americas", "currency_code": "USD", "main_exchange": "NYSE/NASDAQ", "yf_suffix": ""},
    {"iso2": "GB", "iso3": "GBR", "name": "United Kingdom", "name_pt": "Reino Unido",
     "region": "Europe", "currency_code": "GBP", "main_exchange": "LSE", "yf_suffix": ".L"},
    {"iso2": "DE", "iso3": "DEU", "name": "Germany", "name_pt": "Alemanha",
     "region": "Europe", "currency_code": "EUR", "main_exchange": "Xetra", "yf_suffix": ".DE"},
    {"iso2": "FR", "iso3": "FRA", "name": "France", "name_pt": "França",
     "region": "Europe", "currency_code": "EUR", "main_exchange": "Euronext Paris", "yf_suffix": ".PA"},
    {"iso2": "NL", "iso3": "NLD", "name": "Netherlands", "name_pt": "Holanda",
     "region": "Europe", "currency_code": "EUR", "main_exchange": "Euronext Amsterdam", "yf_suffix": ".AS"},
    {"iso2": "CH", "iso3": "CHE", "name": "Switzerland", "name_pt": "Suíça",
     "region": "Europe", "currency_code": "CHF", "main_exchange": "SIX", "yf_suffix": ".SW"},
    {"iso2": "JP", "iso3": "JPN", "name": "Japan", "name_pt": "Japão",
     "region": "Asia", "currency_code": "JPY", "main_exchange": "TSE", "yf_suffix": ".T"},
    {"iso2": "CN", "iso3": "CHN", "name": "China", "name_pt": "China",
     "region": "Asia", "currency_code": "CNY", "main_exchange": "SSE/SZSE", "yf_suffix": ".SS"},
    {"iso2": "AU", "iso3": "AUS", "name": "Australia", "name_pt": "Austrália",
     "region": "Oceania", "currency_code": "AUD", "main_exchange": "ASX", "yf_suffix": ".AX"},
    {"iso2": "CA", "iso3": "CAN", "name": "Canada", "name_pt": "Canadá",
     "region": "Americas", "currency_code": "CAD", "main_exchange": "TSX", "yf_suffix": ".TO"},
    {"iso2": "XX", "iso3": "XXX", "name": "Global", "name_pt": "Global",
     "region": "Global", "currency_code": "USD", "main_exchange": "N/A", "yf_suffix": ""},
]

# ══════════════════════════════════════════════
# MAPEAMENTO TICKER → SETOR GICS (simplificado)
# ══════════════════════════════════════════════
TICKER_SECTOR_MAP = {
    # BR — Energia (O&G)
    "PETR3.SA": "10101010", "PETR4.SA": "10101010", "PRIO3.SA": "10101020",
    "RECV3.SA": "10101020", "RRRP3.SA": "10101020", "CSAN3.SA": "10101010",
    "UGPA3.SA": "10101010", "VBBR3.SA": "10101010",
    # BR — Materiais
    "VALE3.SA": "15104020", "CSNA3.SA": "15104050", "GGBR4.SA": "15104050",
    "GOAU4.SA": "15104050", "USIM5.SA": "15104050", "SUZB3.SA": "15101010",
    "KLBN11.SA": "15101010",
    # BR — Financeiro
    "ITUB4.SA": "40101010", "BBDC4.SA": "40101010", "BBAS3.SA": "40101010",
    "SANB11.SA": "40101010", "BPAC11.SA": "40101010", "ITSA4.SA": "40203010",
    "B3SA3.SA": "40204010", "BBSE3.SA": "40301020", "CIEL3.SA": "40204010",
    # BR — Utilities (Energia Elétrica)
    "ELET3.SA": "55101010", "ELET6.SA": "55101010", "CMIG4.SA": "55101010",
    "CPFE3.SA": "55101010", "ENGI11.SA": "55101010", "EQTL3.SA": "55101010",
    "TAEE11.SA": "55101010", "CPLE6.SA": "55101010", "AURE3.SA": "55101010",
    "NEOE3.SA": "55101010", "AESB3.SA": "55101010",
    # BR — Consumo
    "ABEV3.SA": "30201020", "JBSS3.SA": "30202030", "BRFS3.SA": "30202030",
    "WEGE3.SA": "20106010", "EMBR3.SA": "20101010",
    # US — Tech
    "AAPL": "45201020", "MSFT": "45103010", "GOOGL": "50203010",
    "AMZN": "25504020", "NVDA": "45301020", "META": "50203010",
    "TSLA": "25102010",
    # US — Financeiro
    "JPM": "40101010", "BAC": "40101010", "GS": "40203010", "MS": "40203010",
    # US — Energia
    "XOM": "10101010", "CVX": "10101010",
    # US — Saúde
    "UNH": "35102030", "JNJ": "35202010", "LLY": "35202010",
    # US — Utilities
    "NEE": "55101010", "DUK": "55101010", "SO": "55101010",
}
