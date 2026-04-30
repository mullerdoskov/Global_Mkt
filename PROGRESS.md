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
- [x] ISSUE-014 — Remover side effects de import — PR #10, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/10)

## Sprint 2 — Continuidade do briefing

- [x] ISSUE-015 — Agendamento incremental — PR #11, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/11)
- [x] ISSUE-016 — Adicionar ativos asiáticos (JP/AU/HK) — PR #12, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/12)
- [x] ISSUE-017 — Endpoint `/api/export/{symbol}.csv` — PR #13, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/13)
- [x] ISSUE-018 — Watchlist persistente (DB) — ADR em PR #14 (https://github.com/mullerdoskov/Global_Mkt/pull/14), implementação em PR #15 (https://github.com/mullerdoskov/Global_Mkt/pull/15), 2026-04-30

## Sprint 3 — Opcional, sem prioridade

- [ ] ISSUE-019 — Migrar `index.html` para Vite + React + TS
- [ ] ISSUE-020 — WebSocket de preços real-time

## Não-catalogadas (alavanca alta, baixo risco)

- [x] ISSUE-021 — CI no GitHub Actions (`alembic upgrade head` + `pytest` em SQLite) — PR #16, 2026-04-30 (https://github.com/mullerdoskov/Global_Mkt/pull/16)
- [ ] ISSUE-022 — Comitar SKILL.md dos agents do ecossistema em `.claude/skills/` (pré-req #5 do prompt original)
- [x] ISSUE-023 — Backups automáticos do PostgreSQL (`pg_dump` semanal + retenção 90 dias) — PR #17, 2026-04-30

## Histórico

- 2026-04-30 — Run #17: ISSUE-023 resolvida.
  Backups automáticos do PostgreSQL via `pg_dump` em formato custom
  (`-Fc`, já comprimido). Três scripts em `scripts/`:
  `backup_postgres.ps1` (Windows Task Scheduler), `backup_postgres.sh`
  (cron / WSL), `Register-BackupTask.ps1` (registrador idempotente do
  Task Scheduler).
  Os wrappers fazem environment setup (resolvem root, carregam `.env`),
  validam que `MARKET_DB_URL` existe e não é SQLite (backup pg_dump
  não se aplica a DB de arquivo — abort com mensagem clara), e
  disparam `pg_dump --dbname=<URL stripped do +psycopg2> -Fc -f
  <BACKUP_DIR>/market_db_<UTC>.dump`. Após o dump, purga arquivos com
  mtime mais antigo que `BACKUP_RETENTION_DAYS` (default 90).
  Logs por run em `logs/backups/backup_<UTC>.log` (timestamp UTC para
  evitar ambiguidade de fuso). Senha **não** é logada — só o caminho
  do binário pg_dump, tamanho do dump, e mensagens de erro do
  pg_dump (que não imprime a senha).
  Contrato de exit code: `0` OK, `1` falha hard (pg_dump não no PATH,
  URL ausente / sqlite, dump não-zero), `2` dump OK mas retenção
  gerou warnings (ex.: arquivo bloqueado por outro processo).
  Schedule: `Register-BackupTask.ps1` registra trigger **semanal**
  (domingo 03:00 hora local), `StartWhenAvailable`,
  `ExecutionTimeLimit=1h`, idempotente (Unregister-then-Register).
  Decisão sobre semanal-vs-diário e formato custom-vs-plain registrada
  em DECISIONS.md.
  Tests: `tests/test_backups.py` adiciona 21 testes — 3 sobre
  existência dos 3 scripts, 7 static checks sobre o `.ps1` wrapper
  (carrega .env, aborta em sqlite, usa pg_dump -Fc, escreve log per
  run UTC, retenção por LastWriteTime, default 90, 3 exit codes), 6
  static checks sobre o `.sh` wrapper (shebang, strict mode,
  carrega .env, aborta em sqlite, pg_dump -Fc, retenção via
  `find -mtime`, e `bash -n` quando bash existir), e 5 sobre o
  `Register-BackupTask.ps1` (trigger Weekly Sunday 03:00, aponta para
  o wrapper certo, idempotente, propaga RetentionDays). Total:
  270/270 passando + 1 skip pré-existente (21 backups + 249 anteriores).
  Sem dependência nova em `requirements.txt` — pg_dump é binário do
  PostgreSQL client, não pacote Python.
  `.gitignore` ganha `logs/backups/` e `backups/` (dumps são dados,
  não código). `.env.example` documenta `BACKUP_DIR`,
  `BACKUP_RETENTION_DAYS`, `BACKUP_LOG_DIR`.
  PR aberto sobre branch da PR #16 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #16: ISSUE-021 resolvida.
  Primeiro gate de CI automático no GitHub Actions. Workflow único em
  `.github/workflows/ci.yml`, dispara em PRs contra `main` e em pushes
  para `main`. Job `backend` em `ubuntu-latest`, Python 3.11 (mesmo da
  máquina de dev), pip cacheado por hash de `backend/requirements.txt`.
  Passos: instala deps, valida que `alembic upgrade head` aplica em DB
  SQLite virgem (`MARKET_DB_URL=sqlite:///./ci_market.db` no env do job),
  e roda `pytest -q` (250 testes coletados, 249 passing + 1 skip
  pré-existente). `concurrency: cancel-in-progress=true` para não
  desperdiçar minutos quando vários pushes chegam em sequência;
  `timeout-minutes: 15` como circuit breaker.
  Decisão arquitetural: SQLite no CI (não Postgres). Justificativa em
  DECISIONS.md — toda a suíte já roda em SQLite localmente, Alembic
  migration testa downgrade round-trip dentro do pytest, e adicionar
  service container Postgres dobraria o tempo do job sem capturar
  mais regressão. Quando ISSUE-019 trocar o frontend para Vite, este
  workflow ganha um job `frontend` paralelo (`npm ci && npm run build`).
  Sem dependência nova no `requirements.txt` (CI usa o que já existe).
  Não dispara contra branches `routine/*` puros (apenas via PR para
  `main`) — evita gastar minutos em branches intermediárias do stack
  enquanto não há intenção de merge.
  PR #16 aberto sobre branch da PR #15 (stack) — auto-retarget para
  `main` quando PRs anteriores mergearem. Por sair fora da sequência
  do briefing original (ISSUE-019/020 são Sprint 3 opcional), entra
  como categoria nova "Não-catalogadas" no PROGRESS.

- 2026-04-30 — Run #15: ISSUE-018 implementada (backend + frontend + migration).
  Implementação completa contra o ADR escrito em Run #14. Backend:
  novo módulo `backend/api/_session.py` com dependency `ensure_session`
  que lê/seta cookie `mdp_session` (UUID v4, HttpOnly, Secure-em-prod,
  SameSite=Lax, Max-Age=10y) e gerencia tabela `user_sessions`. Novo
  módulo `backend/api/watchlist.py` com 3 endpoints idempotentes:
  `GET/POST/DELETE /api/watchlist[/{symbol}]`. POST retorna 200 (já
  existia) ou 200 (criou) com position; DELETE retorna 204 (sempre
  idempotente — só 404 se asset desconhecido). Schema: 2 tabelas
  novas (`user_sessions` PK uuid, `watchlist_items` com FK ON DELETE
  CASCADE para asset e session, UNIQUE(session_uuid, asset_id)).
  Migration Alembic `77b6af8de3dd_add_watchlist_tables.py` puramente
  aditiva. Frontend: novo store global `watchlistStore` + hook
  `useWatchlist` + componente `WatchlistStar` reusável; página
  `/watchlist` com tabela (símbolo, nome, tipo, moeda, ação remover);
  estrela na header do `SymbolDetail`; entrada no sidebar.
  `apiFetch` agora envia `credentials: 'include'` para o cookie.
  Settings: `rate_limit_watchlist_read=120/min`, `_write=30/min`,
  `session_cookie_secure` (default True; conftest seta False para
  testes via env). `.env.example` documenta os 3 settings novos.
  Tests: `tests/test_watchlist.py` adiciona 21 testes — wiring (3),
  cookie lifecycle (4: set no 1º, reuso, malformado, órfão), GET
  vazio (1), POST (5: caminho feliz, idempotência, position++,
  ordenação, enrichment), DELETE (3: remove, idempotente, 404 só
  para desconhecido), isolamento entre sessões (2), e Alembic
  watchlist (2: head cria as 2 tabelas, round-trip up/down/up).
  `tests/test_alembic_migration.py` atualizado para incluir
  `user_sessions` e `watchlist_items` em EXPECTED_TABLES.
  Smoke test ponta-a-ponta (uvicorn + curl) confirma o ciclo
  completo: cookie → POST → GET → DELETE → GET vazia.
  Total: 249/249 passando + 1 skip pré-existente (21 watchlist +
  228 anteriores).
  Bug fix encontrado durante implementação: `WatchlistItem.id`
  começou como `BigInteger` (autogenerate) — em SQLite, só
  `INTEGER PRIMARY KEY` autoincrementa (BIGINT não vira rowid alias).
  Corrigido para `Integer` em schema + migration. Watchlist é
  per-user, range INT (~2^31) é folga sobrada.
  Bug fix #2: `SESSION_COOKIE_SECURE=true` (default) impedia o
  TestClient de enviar cookie sobre `http://testserver` (httpx
  respeita Secure). Adicionado `SESSION_COOKIE_SECURE=false` em
  `conftest.py` antes de qualquer import de backend; `.env.example`
  documenta que dev local sobre HTTP precisa do mesmo override.
  PR #15 aberto sobre branch da PR #14 (stack):
  https://github.com/mullerdoskov/Global_Mkt/pull/15 — auto-retarget
  para `main` quando PRs anteriores mergearem.

- 2026-04-30 — Run #14: ADR de ISSUE-018 registrado (sem implementação).
  A orientação do run anterior pediu ADR formal antes de pegar
  ISSUE-018 (watchlist persistente) por ter decisão arquitetural
  prévia: identidade do usuário (cookie UUID anônimo vs M365 SSO).
  ADR escrito em `DECISIONS.md` com 7 escolhas explícitas:
  cookie `mdp_session` (UUID v4, HttpOnly, Secure-em-prod, SameSite=Lax,
  Max-Age=10y) gerado no servidor no 1º request; tabelas
  `user_sessions` (uuid PK) e `watchlist_items` (session_uuid FK,
  asset_id FK, position, UNIQUE(session_uuid, asset_id)); 3 endpoints
  idempotentes (`GET/POST/DELETE /api/watchlist[/symbol]`); migration
  Alembic puramente aditiva; rate limits dedicados
  (`watchlist_read=120/min`, `watchlist_write=30/min`); endpoint de
  export CSV via infra do ISSUE-017 como mitigação ao pior cenário
  (limpeza de cookie). Recomendação ESCOLHIDA: cookie UUID anônimo
  para o MVP, com porta de migração documentada para SSO M365 quando
  os gatilhos chegarem (>1 usuário simultâneo, requisito de auditoria,
  permissão granular). Critério de aceite e plano de testes
  documentados no próprio ADR para o run que pegar a implementação.
  Sem código, sem schema novo, sem dependência nova — só `DECISIONS.md`
  e `PROGRESS.md`. ISSUE-018 permanece aberta no checklist; PR #14 é
  estritamente preparatório.
  PR #14 aberto sobre branch da PR #13 (stack):
  https://github.com/mullerdoskov/Global_Mkt/pull/14 — auto-retarget para
  `main` quando PRs anteriores mergearem.

- 2026-04-30 — Run #13: ISSUE-017 resolvida.
  Novo endpoint `GET /api/export/{symbol}.csv` em `backend/api/export.py`,
  registrado no `api_router`. Devolve `StreamingResponse` com `media_type=
  "text/csv; charset=utf-8"` e `Content-Disposition: attachment;
  filename="<symbol>_<period>.csv"` (símbolo sanitizado: alfanuméricos +
  `.`/`_`/`-` ficam, qualquer outra coisa vira `_`; cobre casos como
  `^BVSP` → `BVSP`, `BRL=X` → `BRL_X`). Schema do CSV:
  `date,open,high,low,close,adj_close,volume`, ordem cronológica
  ascendente, `None`/NULL serializa como célula vazia.
  Reusa `period_dep`/`parse_period` de `_periods.py` (ISSUE-012):
  `period` aceita `<n><d|w|m|y>` no range 1d..10y, default `90d`,
  inválido → 422 antes do streaming. Asset inexistente → 404 antes da 2ª
  query (single round-trip). Range vazio → 200 com CSV de cabeçalho-apenas
  (não 404, ver DECISIONS.md).
  Streaming via generator com `csv.writer` + `StringIO` reciclado por
  chunk — header sai antes da primeira linha de dados, sem materializar
  a lista inteira. `Cache-Control: no-store` para impedir cache de browser
  em data financeira.
  Rate limit: novo setting `rate_limit_export` (default `10/minute`,
  documentado em `.env.example`) — mais agressivo que o default
  60/min/IP por ser endpoint de extração. Decorador
  `@limiter.limit(settings.rate_limit_export)` aplicado.
  `RATE_LIMIT_ENABLED=false` em testes mantém o no-op (igual aos demais
  endpoints).
  Tests: `tests/test_export_csv.py` adiciona 21 testes — 3 caminho feliz
  (200 + headers + payload + filename com period custom + None→célula
  vazia), 2 sobre 404 (asset inexistente + sem 2ª query), 8 sobre 422
  (parametrizado: vazio/typo/decimal/sinal/maiúscula/espaço/unidade
  desconhecida/acima do máximo), 1 sobre range vazio, 2 sobre filename
  sanitization (`^BVSP`, `BRL=X`), 4 wiring (settings expõe
  `rate_limit_export`, rota registrada no app, handler usa
  StreamingResponse, decorador aplicado), e 1 enforcement real do
  rate limit em sub-app dedicado (3ª chamada em "2/minute" → 429).
  Total: 228/228 passando + 1 skip pré-existente (21 export + 207
  anteriores).
  Sem dependência de internet ou banco real: `get_session` é patched
  com `MagicMock` que devolve mocks de `Asset`/`PriceDaily` em sequência;
  rate limit enforcement usa sub-app FastAPI isolado (mesma estratégia
  de `test_rate_limiting.py`).
  PR aberto sobre branch da PR #12 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #12: ISSUE-016 resolvida.
  Universo de ativos passa a cobrir Ásia/Oceania. `backend/config/symbols.py`
  ganha três listas: `STOCKS_JP` (20 do Nikkei 225), `STOCKS_AU` (10 do
  ASX 200), `STOCKS_HK` (10 do HSI). Total de tickers vai de ~600 para ~640
  (+40 ações novas). Os três índices de bolsa (`^N225`, `^HSI`, `^AXJO`) já
  estavam em `INDICES` desde o seed inicial — não precisaram ser adicionados.
  `get_country_for_symbol` ganha 3 sufixos: `.T → JP`, `.AX → AU`, `.HK → HK`.
  `backend/data/sectors_gics.py:COUNTRIES` ganha entrada para Hong Kong
  (`HK / HKG / Asia / HKD / HKEX / .HK`); Japão e Austrália já estavam
  presentes. Total de países: 12 → 13.
  Pipeline de ingestão (`ingest_prices` em `backend/ingestion/loader.py`)
  não precisou mudar: ele itera `SYMBOLS_BY_TYPE["stock"]`, e `ALL_STOCKS`
  agora inclui os 40 novos. Decisão arquitetural sobre o índice `^HSI` (HK
  vs. CN) registrada em DECISIONS.md.
  Tests: `tests/test_asian_assets.py` adiciona 34 testes — 3 sobre tamanho
  mínimo das listas, 3 sobre convenção de sufixo yfinance, 5 sobre inclusão
  em ALL_STOCKS / SYMBOLS_BY_TYPE / sem-duplicatas, 3 parametrizados sobre
  presença dos índices, 12 sobre `get_country_for_symbol` (9 parametrizados
  + 3 sobre listas inteiras), 4 sobre `COUNTRIES` (HK presente, JP/AU não
  regrediram, iso2 único), e 3 smoke de `ensure_asset_exists` (cria company
  com country_id correto para 1 ticker JP/AU/HK cada). Total: 207/207
  passando + 1 skip pré-existente (34 asian + 173 anteriores).
  Sem dependência de internet ou banco real: yfinance é mockado via
  `MagicMock`, banco usa SQLite em memória criado por `Base.metadata.create_all`.
  PR aberto sobre branch da PR #11 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

- 2026-04-30 — Run #11: ISSUE-015 resolvida.
  Atualização incremental agendada agora roda via `backend.scheduling.incremental_update`
  (módulo Python testável) chamado por dois wrappers shell:
  `scripts/scheduled_update.ps1` (Windows Task Scheduler) e
  `scripts/scheduled_update.sh` (cron / WSL). Os wrappers só fazem
  environment setup (resolvem root, ativam venv se existir, carregam
  `.env`) e delegam — toda a lógica fica no Python.
  Contrato de exit code definido para que o agendador trate cada caso
  com prioridade certa: `0` = OK, `2` = run completou com erros parciais
  (ex.: 1 de 600 tickers com 429 esporádico — não acende o alarme),
  `1` = falha não recuperada (ação humana). Logs por run em
  `logs/scheduler/incremental_update_YYYY-MM-DDTHHMMSSZ.log` (timestamp
  UTC para evitar ambiguidade de fuso). Destino sobrescrevível via env
  `SCHEDULER_LOG_DIR` ou flag `--log-dir`.
  Helper `scripts/Register-ScheduledTask.ps1` registra o job no Windows
  Task Scheduler de forma idempotente (Unregister-then-Register), com
  trigger diário às 22:00 hora local da máquina, `StartWhenAvailable`
  (acorda do sleep) e `ExecutionTimeLimit=2h` (mata runs enroscados).
  Decisão: Task Scheduler local + .ps1 escolhido sobre Prefect/Dagster
  por ser proporcional ao escopo atual (1 job, 1 máquina) — registrada
  em DECISIONS.md.
  Tests: `tests/test_scheduler.py` adiciona 26 testes — 4 sobre exit
  codes (0/1/2 + caso vacuo 0/0), 3 sobre lookback_days plumbing, 3
  parametrizados sobre input inválido, 4 sobre logging (naming,
  traceback capturado, mkdir recursivo, format do path), 3 sobre
  resolução de log dir (default/env/override), 2 sobre `main()`/argparse,
  e 7 static checks sobre os shell wrappers (existem, delegam ao módulo
  Python sem duplicar lógica, `.sh` passa em `bash -n` quando disponível,
  Register-ScheduledTask configura trigger diário 22:00 e é idempotente).
  Total: 173/173 passando + 1 skip (mesma pré-existente). Sem dependência
  de internet, banco real ou Windows API — `update_prices` é injetado
  como fake; static checks sobre os scripts são read-only.
  PR aberto sobre branch da PR #10 (stack) — auto-retarget para `main`
  quando PRs anteriores mergearem.

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
