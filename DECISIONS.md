# Decisions — Market Data Platform

Decisões arquiteturais registradas pela Routine `MDP Sprint Worker`.
Formato: data — título, issue de referência, decisão, alternativas, trade-off.

---

## 2026-04-29 — Paginação de `GET /api/prices` via `total` + `page` + `page_size`
**Issue:** ISSUE-002
**Decisão:** `LatestPricesResponse` passa a expor `total` (contagem total de ativos com preço), `page` e `page_size` em vez de somente `count` (contagem dos itens retornados). Default: `page_size=50`, máx `100`.
**Alternativas consideradas:** manter `count` com semântica de "items returned" sem paginação real.
**Trade-off:** pequena quebra de contrato em relação ao modelo anterior — mas o endpoint estava retornando 500, então na prática não havia contrato estabelecido.

---

## 2026-04-29 — Campo `price_date` em `LatestPrice` (renomeado de `date`)
**Issue:** ISSUE-002
**Decisão:** O campo foi renomeado de `date` para `price_date` em `LatestPrice` para evitar conflito de nome com o built-in `datetime.date` no contexto do Pydantic v2. Em Pydantic v2, um campo chamado `date: Optional[date] = None` com `= None` default causa `ValidationError` do tipo `none_required` porque a atribuição `date = None` no corpo da classe sobrescreve a referência ao tipo importado no namespace da classe.
**Alternativas consideradas:** usar string annotation `"date"`, usar `import datetime as _dt` com `Optional[_dt.date]`.
**Trade-off:** mudança no nome do campo na resposta JSON da API — o frontend usa `...item` spread e não usa `item.date` explicitamente, portanto a renomeação é segura.

---

## 2026-04-29 — `MARKET_DB_URL` passa a ser obrigatória (sem fallback)
**Issue:** ISSUE-004
**Decisão:** A variável de ambiente `MARKET_DB_URL` é agora obrigatória. Se ausente:
- `backend/db/connection.py`: a função `_resolve_database_url()` levanta `RuntimeError`
  com instrução de uso (exemplos para SQLite e PostgreSQL).
- `backend/config/settings.py`: o campo `market_db_url` é declarado sem default;
  pydantic-settings levanta `ValidationError` em `Settings()`.
**Alternativas consideradas:** manter fallback apontando para SQLite local (mais
amigável, mas mascara erro de configuração em prod); usar default vazio com
validador customizado (aumenta superfície sem ganho).
**Trade-off:** quem rodava localmente sem `.env` agora vê erro imediato em vez de
conexão silenciosa contra DB inexistente. É o comportamento desejado: falhas de
configuração devem ser explícitas. A documentação (`BACKEND_README.md`,
`.env.example`) já orienta a copiar `.env.example` para `.env` antes de subir.

---

## 2026-04-29 — Campo `index_date` em `IndexSnapshot` (renomeado de `date`)
**Issue:** ISSUE-006 (correção colateral revelada pelos smoke tests)
**Decisão:** O campo foi renomeado de `date` para `index_date` em `IndexSnapshot`,
seguindo a mesma resolução já aplicada a `LatestPrice.price_date`. Em Pydantic v2,
declarar `date: Optional[date] = None` faz com que `date = None` no corpo da classe
sobrescreva a referência ao tipo importado, e o validador passa a exigir `None`
(`type=none_required`). O endpoint `/api/market/summary` falharia em runtime para
qualquer índice com preço/data real — bug latente que o smoke test (com mock
retornando `price_row.date = date(2026, 4, 25)`) revelou imediatamente.
**Alternativas consideradas:** (1) usar `import datetime as _dt` e `Optional[_dt.date]`;
(2) deixar o bug e fazer o smoke test usar apenas o caminho de "asset não encontrado"
(que emite `IndexSnapshot(... index_date=None)` e passa pela validação); (3) abrir
issue separada sem corrigir agora.
**Trade-off:** quebra de contrato JSON (`indices[].date` → `indices[].index_date`).
Frontend (`frontend/index.html`) não usa o campo — verificado por grep. Se algum
consumidor externo existir, vai precisar atualizar. Optei por consertar agora porque:
(a) é o mesmo bug-class de `LatestPrice` já corrigido com a mesma estratégia;
(b) sem o rename, o smoke test não consegue exercitar o caminho de sucesso do
endpoint (o que é o objetivo da ISSUE-006); (c) deixar metade do codebase com
`Optional[date] = None` quebrado e a outra metade consertada é incoerência pior
que a quebra de contrato.

---

## 2026-04-29 — Bootstrap do git em `market_platform_unified/` (pré-requisito não executado)
**Issue:** N/A — procedimento de bootstrap
**Decisão:** O pré-requisito de inicializar git em `market_platform_unified/` e conectar ao `mullerdoskov/Global_Mkt` não estava concluído quando a Routine rodou pela primeira vez. A Routine inicializou o repositório neste run, conectou ao remote existente, e abriu o PR #1. O histórico do nested `Global_Mkt_2.0/` (2 commits) não foi incorporado — a Routine não pode fazer força push nem rebase sem autorização humana. Lucas deve resolver o histórico em conjunto com ISSUE-001.
**Alternativas consideradas:** abrir somente uma GitHub Issue descrevendo o bloqueio (sem código).
**Trade-off:** ao escolher inicializar o git e abrir o PR, a Routine entregou código funcional mas criou uma divergência de histórico entre o nested e o novo repositório — situação que ISSUE-001 precisa resolver.
