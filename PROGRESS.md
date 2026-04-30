# Progress — Market Data Platform

Atualizado pela Routine `MDP Sprint Worker` ao fim de cada run.
Ordem = prioridade de execução. Marcações:
- `[ ]` aberta
- `[x]` resolvida (PR #N, data)
- `[blocked: motivo]`
- `[humano-only]` — Routine não pega

## Sprint 0 — Estabilização

- [humano-only] ISSUE-001 — Decidir destino do nested `Global_Mkt_2.0/`
- [x] ISSUE-002 — Fix `GET /api/prices` (DISTINCT ON + paginação) — PR #1, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/1)
- [x] ISSUE-003 — Fix exception handler em `app.py` — PR #1, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/1)
- [x] ISSUE-004 — Remover senha hardcoded em `connection.py:16` e `settings.py:13` — PR #2, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/2)
- [humano-only] ISSUE-005 — Auditar git history por senha (filter-repo é destrutivo)
- [x] ISSUE-006 — Smoke tests da API (cobertura completa, 1 teste por endpoint) — PR #3, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/3)
- [x] ISSUE-007 — Servir frontend via FastAPI StaticFiles — PR #4, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/4)
- [humano-only] ISSUE-008 — Arquivar `market_platform/` e `emergent/`

## Sprint 1 — Escala

- [x] ISSUE-009 — Alembic + migrações iniciais — PR #5, 2026-04-29 (https://github.com/mullerdoskov/Global_Mkt/pull/5)
- [x] ISSUE-010 — Rate limiting com slowapi — PR #6, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/6)
- [x] ISSUE-011 — Cache Redis com fastapi-cache2 — PR #7, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/7)
- [x] ISSUE-012 — Validação robusta de `period` — PR #8, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/8)
- [x] ISSUE-013 — Implementar `net_debt_ebitda` real — PR #9, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/9)
- [x] ISSUE-014 — Remover side effects de import — PR aberto, 2026-04-30

## Sprint 2 — Continuidade do briefing

- [ ] ISSUE-015 — Agendamento incremental
- [ ] ISSUE-016 — Adicionar ativos asiáticos (JP/AU/HK)
- [ ] ISSUE-017 — Endpoint `/api/export/{symbol}.csv`
- [ ] ISSUE-018 — Watchlist persistente (DB)

## Sprint 3 — Opcional, sem prioridade

- [ ] ISSUE-019 — Migrar `index.html` para Vite + React + TS
- [ ] ISSUE-020 — WebSocket de preços real-time

## Histórico

- 2026-04-30 — Run #10: ISSUE-014 resolvida.
  Três módulos deixam de fazer trabalho em escopo de import:
  (a) `backend/db/connection.py` — `load_dotenv`, `_resolve_database_url`
  e `create_engine` saem do top-level. Novos `get_engine()` e
  `get_sessionmaker()` cacheados via `lru_cache(maxsize=1)`, `is_sqlite()`
  como helper runtime. Compat com `from connection import engine,
  IS_SQLITE, SessionLocal, DATABASE_URL` mantida via PEP 562
  (`__getattr__`) — atributos resolvem on demand sem rodar nada no
  import. (b) `backend/config/logging_config.py` — removida a linha
  `logger = setup_logging()`; `os.makedirs(LOG_DIR)` só roda quando
  alguém chama `setup_logging()`/`get_logger(name)`. Adicionado
  `get_logger` como ponto de entrada recomendado. (c) `backend/api/_cache.py`
  — removida a chamada `init_cache_sync()` no module-level. Em produção,
  o lifespan já cobre via `init_cache_async`; em testes, adicionada
  fixture autouse session-scoped no `conftest.py` raiz que faz a init
  antes de qualquer teste rodar.
  Tests: `tests/test_no_import_side_effects.py` (10 testes novos) prova
  que os 3 módulos podem ser carregados em isolamento sem disparar
  `load_dotenv`, `create_engine`, `os.makedirs(LOG_DIR)`, `addHandler`
  ou `FastAPICache.init`. Cobre também `get_engine()` cacheado, lazy
  attrs do PEP 562, `setup_logging` idempotente, e `get_logger` retornando
  loggers root/child. Total: 147/147 passando + 1 skip
  (3 alembic + 23 smoke + 9 cache + 5 db_url + 19 net_debt_ebitda +
  10 import_side_effects + 65+1s periods + 6 prices + 7 rate_limit).
  PR aberto sobre branch da PR #9 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #9: ISSUE-013 resolvida.
  `net_debt_ebitda` deixa de ser placeholder. Duas funções públicas novas em
  `backend/ingestion/fundamentals_loader.py`: `compute_net_debt_ebitda(nd, eb)`
  (puro, devolve `nd/eb` quando ambos são finitos e `eb != 0`; senão None) e
  `latest_net_debt_ebitda(session, company_id)` (busca `FinancialStatement`
  mais recente por `period_end DESC` e aplica a fórmula). O snapshot de
  `valuation_multiples` agora carrega o campo via
  `latest_net_debt_ebitda(session, company.id)` — chamado depois do `commit`
  do bloco de demonstrações, então a métrica considera o Q recém-ingerido.
  Comportamento explícito: `ebitda=0` no Q mais recente → None (não faz
  fallback para o Q anterior). Justificativa em DECISIONS.md.
  Funciona também quando yfinance retorna só `info` (sem novos statements):
  o lookup busca o que já estava persistido, então o snapshot continua
  carregando a métrica em vez de virar NULL na 2ª ingestão do dia.
  Tests: `tests/test_net_debt_ebitda.py` adiciona 19 testes — 11 sobre a
  função pura (5 cálculos parametrizados, 3 caminhos None, ebitda=0,
  NaN/inf, tipo não numérico), 5 sobre o lookup (sem demonstração, 1
  demonstração, ordenação cronológica fora de ordem, ebitda=0 sem fallback,
  isolamento por company), e 3 de wiring no `ingest_financials_for_symbol`
  (snapshot consome balance corrente; snapshot consome dados persistidos
  quando yfinance não traz statements; snapshot fica None quando não há
  demonstração). Total: 137/137 passando + 1 skip
  (19 net_debt_ebitda + 65 periods + 9 cache + 7 rate_limit + 3 alembic +
  23 smoke + 6 prices + 5 db_url).
  Sem dependência de internet ou pandas: `_get_field` e `get_financials`
  são mockados; banco é SQLite em memória criado via `Base.metadata.create_all`.
  PR aberto sobre branch da PR #8 (stack) — auto-retarget para `main` quando
  PRs anteriores mergearem.

- 2026-04-30 — Run #8: ISSUE-012 resolvida.
  Validação estrita de `period` centralizada em `backend/api/_periods.py`.
  `parse_period(period: str) -> ParsedPeriod` aceita exatamente
  `<inteiro positivo><unidade>` com unidade em {d, w, m, y}, range
  `1d..10y` (inclusive). `ParsedPeriod` é frozen dataclass com `raw`
  (string original, ecoada na resposta) e `delta` (timedelta para
  cálculos). `period_dep` envolve a validação como `Depends`,
  declarando `period` como `Query("90d", ...)` para preservar o
  contrato de OpenAPI/Swagger.
  Comportamento antigo: `prices._parse_period` e o parsing inline em
  `market.py` caíam silenciosamente em 90d para qualquer formato
  desconhecido (typos viravam "default"). Novo: 422 explícito com
  mensagem útil. `prices._parse_period` removido (era o único usuário).
  Wiring: 3 endpoints atualizados — `/api/prices/{symbol}/history`,
  `/api/prices/{symbol}/returns`, `/api/market/sectors`. Resposta JSON
  ecoa `period` original (ex: cliente pede `4w`, resposta tem
  `period: "4w"`, não `"28d"`).
  Cache (ISSUE-011) revalidado: query string permanece como base do
  `default_key_builder` da fastapi-cache2, então `period=90d` e
  `period=180d` continuam gerando entradas distintas; `period=90d`
  duas vezes seguidas continua servindo do cache. `ParsedPeriod` é
  frozen para que `repr` seja estável caso o key builder mude para
  considerar args.
  Tests: `tests/test_periods.py` adiciona 65 testes — 12 casos válidos
  parametrizados (incluindo boundaries 1d e 10y), 23 casos inválidos
  (vazio, formato livre, decimal, negativo, unidade não suportada,
  acima do MAX_DAYS), 3 testes de `period_dep`, 18 testes de integração
  (3 endpoints × 6 períodos inválidos via parametrize), e 4 caminhos
  felizes (5y, default omitido, 4w, 1y) confirmando wiring correto.
  Total: 118/118 testes passando + 1 skip intencional
  (9 cache + 7 rate_limit + 3 alembic + 23 smoke + 6 prices + 5 db_url +
  65 periods).
  PR aberto sobre branch da PR #7 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #7: ISSUE-011 resolvida.
  Cache HTTP via `fastapi-cache2` aplicado em `/api/market/summary` e
  `/api/market/sectors` com TTL de 15min (`CACHE_TTL_MARKET = 900`).
  Backend de cache escolhido em runtime: `RedisBackend` se `REDIS_URL` setada
  e ping ok; senão `InMemoryBackend` (process-local). Falha no Redis cai
  em InMemory com WARNING — Redis é nice-to-have, não bloqueia o start.
  `CACHE_ENABLED=false` (default em testes via conftest.py) faz `@cache(...)`
  virar no-op silencioso.
  `backend/api/_cache.py` faz `init_cache_sync()` em escopo de import (para
  garantir backend válido em testes que pulam lifespan), e `init_cache_async()`
  no lifespan tenta upgrade para Redis. Bug encontrado e contornado:
  `FastAPICache.init` da fastapi-cache2 retorna cedo se já inicializado
  (`if cls._init: return`), então `reset()` é chamado antes de cada `init`.
  `docker-compose.dev.yml` criado com Redis 7-alpine (e Postgres 17 opcional)
  para subir as deps de dev local.
  Tests: `tests/test_cache.py` adiciona 9 testes — wiring (4: backend,
  prefix, enable, decorador aplicado), no-op quando desabilitado (1, com
  6 execuções de `session.execute` em 2 requests), cache hit real com
  InMemoryBackend (2: 2ª chamada não executa handler; query params
  diferentes geram entradas distintas), e fallback do `init_cache_async`
  (2: sem REDIS_URL e com Redis indisponível). Total: 53/53 passando
  (9 cache + 7 rate_limit + 3 alembic + 23 smoke + 6 prices + 5 db_url
  validation).
  `requirements.txt`: +fastapi-cache2>=0.2.1, +redis>=5.0.0.
  PR aberto sobre branch da PR #6 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #6: ISSUE-010 resolvida.
  Rate limiting com slowapi habilitado em todos os endpoints sob `/api` (13
  rotas: 3 em assets, 4 em prices, 3 em market, 2 em fundamentals, 1 em
  ingestion). Limite default: 60 req/min por IP via `get_remote_address`.
  Limiter compartilhado em `backend/api/_limiter.py`; `app.py` registra
  `app.state.limiter`, exception handler para `RateLimitExceeded` e
  `SlowAPIMiddleware`. Cada handler ganhou `request: Request` como primeiro
  parâmetro nomeado (exigido pelo decorador). `/health`, `/api/info` e o
  StaticFiles continuam fora do gate. Configuração em `settings.py`:
  `rate_limit_default` (string limits) e `rate_limit_enabled` (bool, default
  True). `conftest.py` define `RATE_LIMIT_ENABLED=false` para que os smoke
  tests (várias chamadas em sequência) não tropecem no limite.
  Tests: `tests/test_rate_limiting.py` adiciona 7 testes — wiring (3),
  no-op quando desabilitado (2, incluindo 80 chamadas reais ao endpoint),
  e enforcement real do slowapi (2, via sub-app dedicado com limite
  "2/minute"). Total: 44/44 testes passando (7 rate_limit + 3 alembic +
  23 smoke + 6 prices + 5 db_url validation).
  PR aberto sobre branch da PR #5 (stack) — auto-retarget para `main` quando
  PRs anteriores mergearem.

- 2026-04-29 — Run #5: ISSUE-009 resolvida.
  Alembic configurado em `market_platform_unified/`. `alembic.ini` na raiz,
  `alembic/env.py` lê `MARKET_DB_URL` do ambiente (sem `sqlalchemy.url` no ini —
  evita versionar credencial), `target_metadata = backend.db.schema.Base.metadata`,
  `render_as_batch=True` quando dialeto é SQLite. `alembic/versions/1a4f86d9547c_initial_schema.py`
  cobre as 9 tabelas + índices + UNIQUE constraints (gerado via autogenerate
  contra SQLite vazio, depois ajustado para dropar os 3 ENUMs do Postgres
  no downgrade — autogenerate deixa esses tipos órfãos por padrão).
  `create_all_tables()` mantido no startup como rede de segurança em dev
  (idempotente); o canônico em prod passa a ser `alembic upgrade head` antes
  de subir a API. Documentado em `BACKEND_README.md` seção "Migrações de schema"
  e em `README.md`. Tests: `tests/test_alembic_migration.py` adiciona 3 testes
  (upgrade head, round-trip up→down→up, e drift entre `Base.metadata` e a head
  via `compare_metadata`). Total: 37/37 testes passando (3 alembic + 23 smoke
  + 6 prices + 5 db_url validation).
  PR aberto sobre branch da PR #4 (stack) — auto-retarget para `main` quando
  PRs anteriores mergearem.

- 2026-04-29 — Run #4: ISSUE-007 resolvida.
  `frontend/index.html` agora é servido pelo próprio FastAPI via
  `StaticFiles(directory=frontend, html=True)` montado em `/` após todos os
  routers. Endpoint antigo `GET /` (JSON com info da API) movido para
  `GET /api/info` para preservar o contrato. `"null"` removido do `CORS_ORIGINS`
  (origin de `file://` deixa de ser suportada — frontend roda mesmo origin que
  a API). README atualizado para apontar `http://localhost:8000/`.
  Tests: `test_root_retorna_200` reescrito como `test_root_serve_index_html`;
  adicionados `test_static_file_acessivel` e `test_api_info_retorna_json`.
  Total: 34/34 testes passando (23 smoke + 6 prices + 5 db_url validation).
  PR aberto sobre branch da PR #3 (stack) — auto-retarget para `main` quando
  PRs anteriores mergearem.

- 2026-04-29 — Run #1 (bootstrap): inicialização do PROGRESS.md, DECISIONS.md, .gitignore.
  Issues ISSUE-002 e ISSUE-003 resolvidas em conjunto (acopladas: query + exception handler).
  Infraestrutura de testes criada (pytest + conftest + test_prices_endpoint.py — 6/6 testes passando).
  Nota: git inicializado em `market_platform_unified/` neste run (pré-requisito não estava concluído).
  ISSUE-001 (humano-only) ainda pendente — bloqueia decisão sobre `Global_Mkt_2.0/`.

- 2026-04-29 — Run #3: ISSUE-006 resolvida.
  Adicionado `tests/test_api_smoke.py` com 21 testes cobrindo todos os 13 endpoints
  da `api_router` + `/health` + `/`. Estratégia: patch de `get_session` por módulo,
  com `MagicMock` cuja `.execute()` retorna resultados em sequência. Endpoints com
  parâmetro `{symbol}` ganharam também o caminho 404. Total: 32/32 testes passando
  (21 smoke + 6 prices + 5 db_url validation).
  Bônus de escopo: `IndexSnapshot.date` renomeado para `index_date` (mesma classe
  de bug Pydantic-v2 já documentada para `LatestPrice.price_date` em DECISIONS.md).
  Sem o rename, o smoke test do `/api/market/summary` falhava com `none_required`
  ao serializar qualquer índice com data real — bug latente em produção.
  Frontend não consome o campo, então a renomeação é segura.
  PR aberto sobre branch da PR #2 (stack) — auto-retarget para `main` quando #1 e #2 mergearem.

- 2026-04-29 — Run #2: ISSUE-004 resolvida.
  Removida credencial hardcoded `141592` do código (`connection.py`, `settings.py`)
  e dos docs versionados (`BACKEND_README.md`, `RELATORIO_CONTEXTO.md`).
  Comportamento novo: ausência de `MARKET_DB_URL` aborta com `RuntimeError` claro
  (sem fallback inseguro). 4 testes novos cobrem a validação + sentry contra
  regressão da senha vazada. Total: 11/11 testes passando (escopo árvore oficial,
  nested `Global_Mkt_2.0/` excluído conforme regra de ISSUE-001).
  PR aberto sobre branch da PR #1 (stack) — auto-retarget para `main` quando PR #1 mergear.
  `.env` real NÃO foi tocado (PSCW: pré-requisito 4 / ISSUE-005, humano-only).
