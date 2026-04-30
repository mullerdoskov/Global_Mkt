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

- [ ] ISSUE-009 — Alembic + migrações iniciais
- [ ] ISSUE-010 — Rate limiting com slowapi
- [ ] ISSUE-011 — Cache Redis com fastapi-cache2
- [ ] ISSUE-012 — Validação robusta de `period`
- [ ] ISSUE-013 — Implementar `net_debt_ebitda` real
- [ ] ISSUE-014 — Remover side effects de import

## Sprint 2 — Continuidade do briefing

- [ ] ISSUE-015 — Agendamento incremental
- [ ] ISSUE-016 — Adicionar ativos asiáticos (JP/AU/HK)
- [ ] ISSUE-017 — Endpoint `/api/export/{symbol}.csv`
- [ ] ISSUE-018 — Watchlist persistente (DB)

## Sprint 3 — Opcional, sem prioridade

- [ ] ISSUE-019 — Migrar `index.html` para Vite + React + TS
- [ ] ISSUE-020 — WebSocket de preços real-time

## Histórico

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
