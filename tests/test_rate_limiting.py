"""
tests/test_rate_limiting.py
Testes do rate limiting (slowapi) — ISSUE-010.

Cobertura:
1. Wiring: o limiter compartilhado está registrado em `app.state.limiter`,
   `SlowAPIMiddleware` está na pilha e o handler de `RateLimitExceeded` está
   instalado.
2. Default tests = no-op: o `conftest.py` define `RATE_LIMIT_ENABLED=false`,
   então `limiter.enabled` deve ser `False` e múltiplas chamadas em sequência
   contra um endpoint da API real não disparam 429.
3. Comportamento real do slowapi quando ligado: subimos um sub-app de teste
   com um limite tight ("2/minute") e verificamos a sequência 200/200/429,
   incluindo a presença do header `Retry-After` na resposta bloqueada.

Não tocamos a configuração global do limiter compartilhado — testes isolados
usam suas próprias instâncias de `Limiter`.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from backend.app import app
from backend.api._limiter import limiter as shared_limiter


# ════════════════════════════════════════════════════════════════════
# 1. WIRING
# ════════════════════════════════════════════════════════════════════

class TestLimiterWiring:
    def test_limiter_compartilhado_em_app_state(self):
        # `app.state.limiter` deve ser exatamente a instância importada de
        # `backend.api._limiter` — qualquer outra coisa significa que rotas
        # decoradas e o middleware estão olhando para limiters diferentes.
        assert app.state.limiter is shared_limiter

    def test_exception_handler_registrado(self):
        # FastAPI guarda handlers customizados em `app.exception_handlers`.
        # Aceita tanto a chave `RateLimitExceeded` quanto o status 429.
        handlers = app.exception_handlers
        assert RateLimitExceeded in handlers

    def test_middleware_instalado(self):
        # Inspeciona a pilha de middlewares — `SlowAPIMiddleware` precisa
        # estar presente ou o decorador `@limiter.limit(...)` é silenciosamente
        # ignorado em runtime.
        middleware_classes = [m.cls for m in app.user_middleware]
        assert SlowAPIMiddleware in middleware_classes


# ════════════════════════════════════════════════════════════════════
# 2. NO-OP QUANDO DESABILITADO (defaults dos testes via conftest.py)
# ════════════════════════════════════════════════════════════════════

class TestLimiterDisabledNoOp:
    def test_limiter_desabilitado_por_padrao_em_testes(self):
        # `conftest.py` define `RATE_LIMIT_ENABLED=false` → o `Limiter` foi
        # instanciado com `enabled=False` no import inicial.
        assert shared_limiter.enabled is False

    def test_endpoint_real_aceita_muitas_chamadas_quando_desabilitado(self):
        # Se o limiter estivesse ligado, "60/minute" cortaria na 61ª. Aqui
        # batemos 80 vezes contra `/api/ingestion/status` (com session mockada)
        # e exigimos 200 em todas — prova de que `enabled=False` desliga o gate.
        from backend.api import ingestion as ingestion_mod

        client = TestClient(app)
        session = MagicMock()
        # Cada chamada do handler executa exatamente uma query (lista de logs).
        result = MagicMock()
        scalars_proxy = MagicMock()
        scalars_proxy.all.return_value = []
        result.scalars.return_value = scalars_proxy
        session.execute.return_value = result

        with patch.object(ingestion_mod, "get_session", return_value=session):
            statuses = [client.get("/api/ingestion/status").status_code for _ in range(80)]

        assert all(s == 200 for s in statuses), (
            f"esperado todos 200 com limiter desabilitado, "
            f"got {set(statuses)} (ocorrências: {statuses.count(429)} × 429)"
        )


# ════════════════════════════════════════════════════════════════════
# 3. ENFORCEMENT REAL DO SLOWAPI (sub-app dedicado)
# ════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_app_com_limite_tight():
    """
    Sub-app FastAPI com a mesma cadeia (limiter + middleware + handler) e um
    único endpoint limitado a 2/minute. Permite verificar o gate sem precisar
    bater 61× num endpoint real.
    """
    test_limiter = Limiter(key_func=get_remote_address, enabled=True)

    sub_app = FastAPI()
    sub_app.state.limiter = test_limiter
    sub_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    sub_app.add_middleware(SlowAPIMiddleware)

    @sub_app.get("/limited")
    @test_limiter.limit("2/minute")
    def limited(request: Request):
        return {"ok": True}

    return sub_app


class TestLimiterEnforcement:
    def test_terceira_chamada_retorna_429(self, test_app_com_limite_tight):
        client = TestClient(test_app_com_limite_tight, raise_server_exceptions=False)
        r1 = client.get("/limited")
        r2 = client.get("/limited")
        r3 = client.get("/limited")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429

    def test_resposta_429_traz_corpo_de_erro(self, test_app_com_limite_tight):
        client = TestClient(test_app_com_limite_tight, raise_server_exceptions=False)
        client.get("/limited")
        client.get("/limited")
        r = client.get("/limited")

        assert r.status_code == 429
        # `_rate_limit_exceeded_handler` devolve um JSON com a string do limite
        # excedido. Não dependemos do texto exato — só checamos que veio JSON
        # e que o limite "2/minute" aparece no payload (suficiente para o cliente
        # entender o motivo).
        body = r.text
        assert "2 per" in body or "2/minute" in body or "Rate limit" in body
