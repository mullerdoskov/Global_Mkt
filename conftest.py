import os

# Define antes de qualquer import do backend para que load_dotenv() e pydantic-settings
# não sobrescrevam com as credenciais reais do .env
os.environ.setdefault("MARKET_DB_URL", "sqlite:///./test_market.db")

# Rate limiting (ISSUE-010): em testes o limiter é instanciado como no-op para
# não interferir nos smoke tests, que disparam várias chamadas em sequência da
# mesma origem (TestClient). Os testes específicos de rate limiting alternam
# `limiter.enabled=True` localmente via fixture (ver test_rate_limiting.py).
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
