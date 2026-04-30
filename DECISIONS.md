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

## 2026-04-29 — Bootstrap do git em `market_platform_unified/` (pré-requisito não executado)
**Issue:** N/A — procedimento de bootstrap
**Decisão:** O pré-requisito de inicializar git em `market_platform_unified/` e conectar ao `mullerdoskov/Global_Mkt` não estava concluído quando a Routine rodou pela primeira vez. A Routine inicializou o repositório neste run, conectou ao remote existente, e abriu o PR #1. O histórico do nested `Global_Mkt_2.0/` (2 commits) não foi incorporado — a Routine não pode fazer força push nem rebase sem autorização humana. Lucas deve resolver o histórico em conjunto com ISSUE-001.
**Alternativas consideradas:** abrir somente uma GitHub Issue descrevendo o bloqueio (sem código).
**Trade-off:** ao escolher inicializar o git e abrir o PR, a Routine entregou código funcional mas criou uma divergência de histórico entre o nested e o novo repositório — situação que ISSUE-001 precisa resolver.
