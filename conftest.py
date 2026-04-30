import os

# Define antes de qualquer import do backend para que load_dotenv() e pydantic-settings
# não sobrescrevam com as credenciais reais do .env
os.environ.setdefault("MARKET_DB_URL", "sqlite:///./test_market.db")
