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
- [x] ISSUE-004 — Remover senha hardcoded em `connection.py:16` e `settings.py:13` — PR #2, 2026-04-29
- [humano-only] ISSUE-005 — Auditar git history por senha (filter-repo é destrutivo)
- [ ] ISSUE-006 — Smoke tests da API (cobertura completa, 1 teste por endpoint)
- [ ] ISSUE-007 — Servir frontend via FastAPI StaticFiles
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

- 2026-04-29 — Run #1 (bootstrap): inicialização do PROGRESS.md, DECISIONS.md, .gitignore.
  Issues ISSUE-002 e ISSUE-003 resolvidas em conjunto (acopladas: query + exception handler).
  Infraestrutura de testes criada (pytest + conftest + test_prices_endpoint.py — 6/6 testes passando).
  Nota: git inicializado em `market_platform_unified/` neste run (pré-requisito não estava concluído).
  ISSUE-001 (humano-only) ainda pendente — bloqueia decisão sobre `Global_Mkt_2.0/`.

- 2026-04-29 — Run #2: ISSUE-004 resolvida.
  Removida credencial hardcoded `141592` do código (`connection.py`, `settings.py`)
  e dos docs versionados (`BACKEND_README.md`, `RELATORIO_CONTEXTO.md`).
  Comportamento novo: ausência de `MARKET_DB_URL` aborta com `RuntimeError` claro
  (sem fallback inseguro). 4 testes novos cobrem a validação + sentry contra
  regressão da senha vazada. Total: 11/11 testes passando (escopo árvore oficial,
  nested `Global_Mkt_2.0/` excluído conforme regra de ISSUE-001).
  PR aberto sobre branch da PR #1 (stack) — auto-retarget para `main` quando PR #1 mergear.
  `.env` real NÃO foi tocado (PSCW: pré-requisito 4 / ISSUE-005, humano-only).
