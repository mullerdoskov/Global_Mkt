"""
api/_limiter.py
Limiter compartilhado por toda a API (ISSUE-010).

A instância única de `Limiter` vive aqui para que `app.py` possa registrá-la
em `app.state.limiter`/middleware e cada router em `backend/api/*.py` possa
aplicar `@limiter.limit(...)` referenciando o mesmo objeto. Slowapi exige que
o handler decorado receba `request: Request` como parâmetro nomeado — todos os
endpoints que usam o decorador foram ajustados para isso.

Configuração lida de `settings`:
- `rate_limit_default`: string no vocabulário do `limits` (ex.: "60/minute").
- `rate_limit_enabled`: quando `False`, o limiter vira no-op (não conta, não
  bloqueia). Útil para os testes (ver `conftest.py`) e para dev local.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config.settings import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    enabled=settings.rate_limit_enabled,
)
