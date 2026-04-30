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

## 2026-04-29 — Frontend servido pelo backend via `StaticFiles`; antigo `GET /` movido para `GET /api/info`
**Issue:** ISSUE-007
**Decisão:** Três mudanças acopladas:
1. `app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True))` registrado
   ao final de `app.py`, depois de todos os routers e rotas explícitas. Com
   `html=True`, `GET /` devolve `frontend/index.html`. Outros caminhos não
   capturados por rotas explícitas são servidos a partir de `frontend/`.
   `FRONTEND_DIR` é resolvido em tempo de import via
   `Path(__file__).resolve().parent.parent / "frontend"` para não depender do
   CWD em que o `uvicorn` for invocado.
2. Endpoint antigo `@app.get("/")` (JSON com `name/version/description/docs/api_prefix`)
   movido para `@app.get("/api/info")`. Preserva o contrato para qualquer
   consumidor externo e libera `/` para o SPA.
3. `cors_origins.append("null")` removido — a origem `"null"` que o navegador
   envia ao abrir um arquivo via `file://` não é mais necessária, já que o
   frontend é servido pelo mesmo origin que a API.
**Alternativas consideradas:** (a) manter `@app.get("/")` retornando JSON e
servir o SPA em `/app` ou `/ui` — rejeitada por contrariar o briefing
("frontend acessível em `localhost:8000/`"); (b) servir via Nginx/CDN
separado — overkill para desenvolvimento e PoC interno.
**Trade-off:** acesso via `file://` deixa de funcionar (CORS bloqueia o
`fetch` para `localhost:8000/api`). Documentado no `README.md` seção 5. Para
desenvolvimento local, basta abrir `http://localhost:8000/`.

---

## 2026-04-29 — Alembic adotado; `MARKET_DB_URL` é fonte única de configuração de banco
**Issue:** ISSUE-009
**Decisão:** Alembic instalado em `market_platform_unified/alembic/` com
`alembic.ini` na raiz. `sqlalchemy.url` **NÃO** é declarada no ini — `env.py`
lê `MARKET_DB_URL` do ambiente, mesmo contrato exigido pelo backend desde
ISSUE-004. Schema canônico passa a ser o da migração head; `Base.metadata`
em `backend/db/schema.py` permanece como fonte da verdade para o autogenerate.
`render_as_batch=True` quando o dialeto é SQLite (necessário para `ALTER`
em SQLite que não suporta operações in-place). `create_all_tables()` mantido
no lifespan do FastAPI como rede de segurança em dev (é idempotente); em prod
o procedimento canônico é `alembic upgrade head` antes de iniciar a API.
**Alternativas consideradas:** (a) Declarar `sqlalchemy.url` em `alembic.ini`
com placeholder e substituir via `%(MARKET_DB_URL)s` — rejeitada por dar a
falsa impressão de que a URL pertence ao ini; (b) Importar `engine` direto de
`backend.db.connection` em `env.py` — rejeitada porque esse módulo cria pool
e instancia engine global no top-level, side effects que não pertencem ao
processo do alembic; (c) Remover `create_all_tables()` agora — adiada para
ISSUE-014 (remover side effects de import) para manter o diff focado.
**Trade-off:** mais um pré-requisito documentado para subir a API em prod
("rode `alembic upgrade head` antes do `uvicorn`"). Em troca, evolução de
schema vira PR rastreável e reversível em vez de mutação implícita via
`Base.metadata.create_all`.

---

## 2026-04-29 — Migração inicial: cleanup explícito de ENUMs Postgres no downgrade
**Issue:** ISSUE-009
**Decisão:** Adicionado ao `downgrade()` da migração `1a4f86d9547c_initial_schema.py`
um bloco que dropa explicitamente os três tipos ENUM (`assettype`, `periodtype`,
`ingestionstatus`) com `checkfirst=True` após `drop_table`. O autogenerate do
alembic tem um buraco conhecido: para `sa.Enum(..., name=...)`, ele cria o tipo
implicitamente em `op.create_table()` mas não dropa em `op.drop_table()`. Em
SQLite isso é no-op (ENUM vira CHECK constraint embutido na tabela), mas em
Postgres o tipo fica órfão e o próximo upgrade falha com "type already exists".
**Alternativas consideradas:** (a) Usar `sa.Enum(..., create_type=False)` e
emitir `op.execute("CREATE TYPE ...")` manual — mais verboso, mais código que
o autogenerate não regera; (b) Aceitar o bug e documentar que downgrade não
funciona em Postgres — rejeitada porque o teste de round-trip
`test_round_trip_upgrade_downgrade_upgrade` é a única forma confiável de
detectar drift de migração no CI.
**Trade-off:** divergência menor entre o que `alembic revision --autogenerate`
emitiria por padrão e o que está commitado. Documentado no docstring do
arquivo de migração para o próximo agent saber que essa edição é intencional.

---

## 2026-04-30 — Rate limiting via slowapi: 60/min por IP, default-on, off em testes
**Issue:** ISSUE-010
**Decisão:** Adotado `slowapi` como gate de rate limiting da API. Quatro
componentes:
1. Instância única de `Limiter` em `backend/api/_limiter.py`, com
   `key_func=get_remote_address` e configuração lida de `settings`
   (`rate_limit_default="60/minute"`, `rate_limit_enabled=True`).
2. `app.py` registra `app.state.limiter`, exception handler para
   `RateLimitExceeded` (`_rate_limit_exceeded_handler` do próprio slowapi)
   e `SlowAPIMiddleware` na pilha.
3. Cada um dos 13 endpoints sob `/api` ganhou
   `@limiter.limit(settings.rate_limit_default)` e `request: Request` como
   primeiro parâmetro nomeado (slowapi exige `request` no handler para
   resolver a chave do limite).
4. `conftest.py` define `RATE_LIMIT_ENABLED=false` para o ambiente de
   testes — o `Limiter` é instanciado com `enabled=False` e vira no-op,
   deixando middleware e decoradores no lugar mas sem bloquear. Testes
   específicos de rate limiting (`tests/test_rate_limiting.py`) usam
   sub-apps dedicados com Limiters próprios em `enabled=True`.
**Alternativas consideradas:**
- (a) Confiar só em `default_limits=[...]` + `SlowAPIMiddleware` global,
  sem decorar cada endpoint. Menos código, mas o middleware aplica o
  limite **a toda rota**, inclusive `/health`, `/api/info`, `/docs`,
  `/openapi.json` e arquivos estáticos do StaticFiles em `/`. Para um SPA
  que carrega múltiplos assets por pageload, 60/min trip rapidamente —
  rejeitada.
- (b) `fastapi-limiter` (alternativa baseada em Redis). Mais robusto em
  setup multi-worker, mas exige Redis funcionando, o que não é pré-
  requisito atual (Redis entra na ISSUE-011). Pode ser revisitado depois.
- (c) Decorar via `Depends(...)` no `include_router` para herdar limite
  por router. Slowapi não suporta esse padrão direto — só `fastapi-
  limiter` tem essa ergonomia. Rejeitada.
**Trade-off:**
- Slowapi por padrão usa storage em memória (`MemoryStorage`). Isso
  significa que cada worker do uvicorn tem sua própria contagem — se
  rodar com `--workers 4`, o limite efetivo é 240/min total (4 × 60) por
  IP, não 60. Documentado para revisitar quando entrar Redis (ISSUE-011);
  basta passar `storage_uri="redis://..."` para o Limiter.
- 13 handlers ganharam `request: Request` como primeiro parâmetro
  nomeado. Diff mecânico mas largo. O alternativo (sem decorador, só
  middleware global) reabriria o problema do StaticFiles citado em (a).
**Como apply / quando revisitar:**
- A 60/min é conservador para uso interno de comercializadora; se o
  frontend vier a fazer polling agressivo (ex.: `/api/market/summary` a
  cada 5s = 12/min), basta ajustar `RATE_LIMIT_DEFAULT` no `.env`.
- Quando ISSUE-011 (Redis + cache) for implementada, mover storage do
  Limiter para Redis pelo mesmo URI do cache resolve o issue de multi-
  worker e dá rate limit distribuído.

---

## 2026-04-29 — Bootstrap do git em `market_platform_unified/` (pré-requisito não executado)
**Issue:** N/A — procedimento de bootstrap
**Decisão:** O pré-requisito de inicializar git em `market_platform_unified/` e conectar ao `mullerdoskov/Global_Mkt` não estava concluído quando a Routine rodou pela primeira vez. A Routine inicializou o repositório neste run, conectou ao remote existente, e abriu o PR #1. O histórico do nested `Global_Mkt_2.0/` (2 commits) não foi incorporado — a Routine não pode fazer força push nem rebase sem autorização humana. Lucas deve resolver o histórico em conjunto com ISSUE-001.
**Alternativas consideradas:** abrir somente uma GitHub Issue descrevendo o bloqueio (sem código).
**Trade-off:** ao escolher inicializar o git e abrir o PR, a Routine entregou código funcional mas criou uma divergência de histórico entre o nested e o novo repositório — situação que ISSUE-001 precisa resolver.
