# Decisions — Market Data Platform

Decisões arquiteturais registradas pela Routine `MDP Sprint Worker`.
Formato: data — título, issue de referência, decisão, alternativas, trade-off.

---

## 2026-04-30 — ISSUE-018 implementação: 2 ajustes contra o ADR original
**Issue:** ISSUE-018 (implementação)
**Decisão:** A implementação seguiu o ADR de 2026-04-30 com 2 ajustes
operacionais descobertos durante codificação:

1. **`WatchlistItem.id` é `Integer`, não `BigInteger`.** O autogenerate
   do Alembic propôs `BigInteger` (espelhando a ergonomia de
   `prices_daily.id`). SQLite só auto-incrementa quando o tipo da PK é
   exatamente `INTEGER PRIMARY KEY` (rowid alias) — `BIGINT PRIMARY KEY`
   não tem essa propriedade, então o INSERT falha com
   `NOT NULL constraint failed: watchlist_items.id`. Watchlist é
   per-user, então `Integer` (range ~2.1 bi) é folga sobrada — não
   há cenário em que um usuário acumule 2 bi de items numa só
   watchlist. Corrigido em `schema.py` + migration antes de comitar.

2. **`SESSION_COOKIE_SECURE=false` em testes.** O TestClient do FastAPI
   conversa via `http://testserver`. Cookies com `Secure=True` não
   são enviados de volta por httpx sobre HTTP — comportamento correto
   por especificação, mas quebra o ciclo cookie→request quando o
   default da settings é `True`. Solução: `conftest.py` seta
   `SESSION_COOKIE_SECURE=false` antes de qualquer import de backend,
   pareando com `RATE_LIMIT_ENABLED=false` e `CACHE_ENABLED=false`.
   `.env.example` documenta que dev local sobre `http://localhost:8000`
   precisa do mesmo override (em prod sobre HTTPS, manter `True`).

**Resto da implementação alinha 1:1 com o ADR**: 3 endpoints
idempotentes, `ensure_session` como dependency, store global no
frontend (`watchlistStore` + `useWatchlist` hook), `WatchlistStar`
reusável, página `/watchlist` no sidebar.

**Trade-off:**
- **`Integer` em vez de `BigInteger`**: alinha com SQLite mas diverge
  de `prices_daily.id` (que é `BigInteger` e funciona em Postgres
  porque BIGSERIAL existe nativo). Aceitável — watchlist nunca vai
  ter o volume de prices_daily; a divergência é local à tabela.
- **`SESSION_COOKIE_SECURE=false` em conftest**: vaza para todos os
  testes (não só os de watchlist). Sem impacto operacional — testes
  não exercitam HTTPS, e o cookie só importa para watchlist. O
  contrato em prod (Secure=True) está intacto.

**Como aplicar (verificação rápida em produção):**
- `alembic upgrade head` aplica a migration aditiva sem mexer nas 9
  tabelas existentes.
- `.env` precisa ter `SESSION_COOKIE_SECURE=true` (já é default em
  settings, mas explicitar em `.env` evita surpresas).
- Smoke test manual: `curl -c cookie.txt http://host/api/watchlist`
  → `{"items":[]}`; `curl -b cookie.txt -X POST .../watchlist/AAPL`
  → `{"symbol":"AAPL","in_watchlist":true,"position":0}`; repetir
  GET para confirmar persistência.

---

## 2026-04-30 — Watchlist persistente: identidade via cookie UUID anônimo (MVP), com porta de migração para SSO
**Issue:** ISSUE-018 (ADR pré-implementação — implementação pendente em run futuro)
**Decisão:** A watchlist persistente usa um identificador opaco de sessão
gerado e armazenado em cookie HTTP no primeiro acesso, sem autenticação
de usuário. O servidor trata o cookie como chave de sessão sem PII e o
liga a uma linha de `user_sessions` no banco. As watchlist items
referenciam essa session, não um `user_id`. Sete escolhas explícitas:

1. **Cookie `mdp_session` com UUID v4** (~122 bits de entropia), gerado
   no servidor na primeira request que não tiver o cookie. Atributos:
   `HttpOnly` (impede leitura via JS, mitiga XSS), `Secure` (default
   `True` em prod via setting; relaxável em dev/local com
   `SESSION_COOKIE_SECURE=false` no `.env`), `SameSite=Lax` (envia em
   navegação top-level mas bloqueia POST cross-site — cobre 99% do
   threat model do MVP sem precisar de CSRF token explícito),
   `Max-Age=315360000` (10 anos — efetivamente persistente para o ciclo
   de vida do MVP), `Path=/`. Sem `Domain` (default = origem da request).

2. **Tabela `user_sessions`** (PK `uuid UUID`, `created_at`,
   `last_seen_at`) gerenciada num middleware/dependency
   `ensure_session(request, response)` em `backend/api/_session.py`.
   A dependency: (a) lê o cookie `mdp_session`; (b) se ausente ou
   inválido (UUID malformado, ou UUID que não está na tabela), gera
   novo, insere a linha, e seta o cookie no `response`; (c) se válido,
   atualiza `last_seen_at` (com `func.now()`, sem round-trip extra
   quando combinada à query da watchlist). A dependency é idempotente
   por request — endpoints só `Depends(ensure_session)` quando
   precisam da session_uuid.

3. **Tabela `watchlist_items`** (`id BIGSERIAL PK`, `session_uuid
   UUID NOT NULL REFERENCES user_sessions(uuid) ON DELETE CASCADE`,
   `asset_id BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE`,
   `position INT NOT NULL DEFAULT 0`, `added_at TIMESTAMPTZ DEFAULT
   now()`, `UNIQUE(session_uuid, asset_id)`, `INDEX(session_uuid)`).
   `ON DELETE CASCADE` em ambos os FKs: se o asset for despromovido
   (raríssimo) ou a session for purgada, items somem sem trabalho extra.

4. **Endpoints idempotentes**:
   - `GET /api/watchlist` → 200 + `{ items: [...] }` ordenado por
     `position ASC, added_at ASC`. Lista vazia se ainda não há items
     (não 404 — semântica "asset_id não encontrado" só faz sentido em
     POST/DELETE de símbolo).
   - `POST /api/watchlist/{symbol}` → 201 (criou) ou 200 (já existia,
     idempotente). 404 se `symbol` não está na tabela `assets`. Body
     opcional para `position`; default é "fim da lista" (max+1).
   - `DELETE /api/watchlist/{symbol}` → 204 (removeu) ou 204 mesmo se
     não existia (idempotente; o 404 só dispara se o `symbol` não
     existe em `assets` — diferenciar "não-existe-no-universo" de
     "não-está-na-watchlist"). Decisão: 404 só para asset desconhecido;
     remoção de item ausente é 204.

5. **Migration Alembic puramente aditiva**: nova revisão cria as duas
   tabelas, sem tocar nas 9 existentes. Downgrade dropa as duas. Em
   SQLite (testes), `gen_random_uuid()` não existe — UUID é gerado em
   Python (`uuid.uuid4()`) no insert do middleware, não pelo banco.
   Schema usa `String(36)` em SQLite e `UUID` em Postgres via
   `with_variant`.

6. **Endpoint complementar de portabilidade**:
   `GET /api/watchlist/export.csv` (uma linha por item: `symbol, name,
   position, added_at`) reusa a infra do ISSUE-017 e dá ao usuário
   uma rota de backup manual. Mitiga o pior cenário do cookie-only:
   limpeza acidental de cookies → perda da watchlist.
   `POST /api/watchlist/import` aceita o mesmo CSV e popula a
   watchlist atual (idempotente sobre `UNIQUE(session_uuid, asset_id)`).
   **Adiada para issue ISSUE-018b** — fora do escopo do MVP, mas
   documentada aqui para ancorar a decisão de cookie-only.

7. **Rate limit dedicado**: `rate_limit_watchlist_write` (default
   `30/minute/IP` — endpoint barato mas POST/DELETE em loop é vetor de
   spam de inserções), `rate_limit_watchlist_read` (default `120/minute/IP`,
   acima do default 60 porque dashboard pode poll). Settings novas em
   `backend.config.settings`, documentadas em `.env.example`.

**Alternativas consideradas:**

- **(a) Cookie UUID anônimo (ESCOLHIDO)** — tempo de implementação ~4h
  (alinhado com a estimativa do diagnóstico). Sem dependência de
  serviço externo. Migrável (ver "Como aplicar" abaixo). Custo: cookie
  é ligado ao browser/máquina; troca de device = nova session vazia.

- **(b) M365 SSO via OAuth2/OIDC com biblioteca `msal` ou
  `authlib`** — rejeitado para o MVP. Para fazer direito precisa:
  app registration no Azure AD do tenant da empresa, redirect URI
  configurado, gestão de `client_secret` (mais um item para `.env`),
  endpoint `/auth/login` + `/auth/callback`, sessão server-side
  (cookie de sessão com JWT ou referência), refresh token rotation,
  middleware que injeta `user_id` em handlers protegidos. Dep nova
  (`msal>=1.27` ou `authlib>=1.3`). Tempo realista: 8–16h, +
  configuração no Azure AD (humano-only). **Quando reconsiderar**:
  (i) >1 usuário simultâneo confirmado, (ii) requisito corporativo de
  auditoria de "quem viu o quê", (iii) integração com permissão
  granular (ex.: dashboards privados por papel). Nenhum dos três é
  realidade hoje (Lucas é o usuário primário, sem co-pilots ativos).

- **(c) Auth básico HTTP (`Authorization: Basic ...`)** — rejeitado.
  Usuário/senha em cada request, dificulta integração com SPA, e exige
  gestão de senhas que (depois de ISSUE-005) Lucas já indicou querer
  evitar. Pior que cookie e pior que SSO em todos os eixos.

- **(d) Token estático em header (`X-API-Key`)** — rejeitado para
  watchlist. Faz sentido para integração machine-to-machine (ex.: um
  job de Lucas que popula watchlist via curl), mas para a UI seria
  pior UX que cookie (SPA precisaria gerenciar storage do token).
  Pode coexistir no futuro como camada paralela à de cookie, dedicada
  a uso programático.

- **(e) localStorage no frontend, sem persistência server-side
  (status quo do PoC `emergent/`)** — rejeitado. ISSUE-018 existe
  exatamente para sair desse modelo: localStorage é per-browser, não
  sobrevive a limpeza de cache e não é compartilhável entre devices
  via export. O ADR assume que persistência server-side é o objetivo.

**Trade-off:**

- **Single-user-per-cookie é por design.** Lucas em duas máquinas =
  duas watchlists. Mitigação: endpoint de export/import (item 6, em
  issue separada). Aceitável para MVP; o dia que virar fricção é o
  gatilho para SSO.

- **Sem proteção CSRF dedicada.** `SameSite=Lax` é a única defesa.
  Cobre o cenário de browser moderno (todos os majors aplicam Lax
  default desde 2020). Threat model: como POST/DELETE da watchlist
  só afeta dados próprios do usuário, o pior cenário de CSRF é
  "atacante adiciona/remove tickers da watchlist do Lucas via
  imagem-tag em página maliciosa que ele visite logado". Pequeno,
  reversível, e bloqueado por `SameSite=Lax` na prática. Se um dia
  o threat model mudar (auth real, transações de valor), adicionar
  CSRF token dedicado é um middleware separado — cabe num run.

- **`HttpOnly` + setting opcional `Secure=False` em dev.** Sem isso,
  testes locais sobre `http://localhost:8000` não recebem o cookie em
  navegadores que enforcem Secure. Padrão prod = `Secure=True`;
  documentado em `.env.example` que `SESSION_COOKIE_SECURE=false` é
  só para dev.

- **Cookie de 10 anos parece eterno mas é o ponto.** Cookie de sessão
  curto (24h) força recriação diária e perde watchlist em pausa de
  fim-de-semana. 10 anos é "vida útil esperada do MVP" e
  efetivamente "persistente até limpeza explícita".

- **Caminho de migração para auth real é linear, não revolucionário.**
  Quando SSO chegar: nova tabela `users (id, email, m365_oid,
  linked_session_uuid)`. No primeiro callback OAuth, ler cookie
  `mdp_session`, criar `user` linkando o uuid, e migrar a FK das
  watchlist_items via `ALTER TABLE ... ADD COLUMN user_id` + UPDATE
  por JOIN. O cookie continua existindo (degradação graciosa para
  usuário não-logado), mas ganha `user_id` quando autenticado. Zero
  perda de dados.

- **Não rastreia IP nem user agent.** Decisão de privacidade
  consciente — `user_sessions` carrega só `uuid + created_at +
  last_seen_at`. Se um dia precisar (anti-fraude, debugging),
  adicionar é aditivo. Default = mínimo.

**Como aplicar (próximo run que pegar a issue):**

- Implementar `backend/api/_session.py::ensure_session(request, response)`
  como FastAPI dependency. Helper `get_session_uuid(request) ->
  uuid.UUID | None` para handlers que precisam só ler.
- Adicionar `backend/api/watchlist.py` com os 3 endpoints; registrar
  em `backend/api/router.py`. Decorar com `@limiter.limit(
  settings.rate_limit_watchlist_{read,write})`.
- Schema: estender `backend/db/schema.py` com `UserSession` e
  `WatchlistItem`; gerar revisão Alembic
  (`alembic revision --autogenerate -m "add watchlist tables"`).
  **Atenção:** revisar o autogenerate antes de comitar — verificar
  que UUID é renderizado como `String(36)` em SQLite e `UUID` em
  Postgres (usar `sa.Uuid()` da SQLAlchemy 2.0 que faz isso nativo,
  não tipo Postgres-only).
- Tests:
  - `test_session_cookie.py` — cookie set no 1º request, idempotente
    no 2º, não vazado pra outros endpoints sem `Depends(ensure_session)`,
    `Secure` flag respeita setting.
  - `test_watchlist_api.py` — caminho feliz (POST→GET→DELETE→GET),
    idempotência (POST duplicado = 200, DELETE de inexistente = 204),
    404 só pra asset desconhecido, isolamento entre cookies (criar 2
    sessions, mexer em uma não afeta a outra).
  - `test_watchlist_alembic.py` — upgrade head cria as 2 tabelas,
    downgrade dropa, FK cascade testado em SQLite (cria session →
    cria item → deleta session → item somem).
  - Frontend: a watchlist UI (botão "estrelar" no card de asset)
    fica para ISSUE-018b (continuação na frontend). O ADR cobre só
    a infra de backend.

**Critério de aceite ISSUE-018 (para o próximo run):**
- Migração Alembic up/down sem warning.
- 3 endpoints com testes verdes.
- Cookie set/leitura testado.
- `.env.example` documenta `SESSION_COOKIE_SECURE` e os 2 rate limits.
- DECISIONS.md ganha "Run #N — ISSUE-018 implementada" referenciando
  esta ADR.
- ISSUE-018b (frontend wiring + export/import CSV da watchlist)
  abertas como issues novas, fora do escopo desta entrega.

---

## 2026-04-30 — Endpoint CSV: 4 escolhas de design
**Issue:** ISSUE-017
**Decisão:** Endpoint `GET /api/export/{symbol}.csv` desenhado com 4
escolhas explícitas:

1. **Range vazio devolve 200 + CSV de cabeçalho-apenas, não 404.**
   404 é "asset not found" — semântica. "Asset existe, mas não tem
   preço no período pedido" é resposta válida (típico em ativos novos
   ou períodos curtos sobre fim-de-semana). Cliente que faz parse do CSV
   continua funcionando; tratar lista vazia é menos código que tratar
   404 + 200. O contrato fica: 404 = símbolo não cadastrado.

2. **Streaming via generator com `csv.writer` da stdlib + `StringIO`
   reciclado.** 10y × 252 dias úteis ≈ 2520 linhas — não justifica
   `pandas.to_csv`. O generator emite header antes da 1ª linha de dados,
   evita materializar a lista inteira em memória, e mantém o handler
   sem dependência de pandas (bom para o lifespan do processo: pandas
   é lazy-imported só pelos endpoints que realmente precisam).

3. **Filename sanitizado com regex `[^A-Za-z0-9._-]+ → _`.**
   Símbolos como `^BVSP`, `BRL=X`, `ETH-USD` viram nomes de arquivo
   amigáveis (`BVSP_90d.csv`, `BRL_X_90d.csv`, `ETH-USD_90d.csv`).
   Aspas duplas no `Content-Disposition` permitem espaço/`=`/`^` em
   teoria, mas filesystems Windows têm restrições; mais seguro
   sanitizar.

4. **Rate limit 10/min/IP em vez de 60/min/IP default.** Endpoint de
   extração é mais "barato" para o atacante (resposta grande, custo
   por request alto) e mais "caro" para o servidor (sweep de prices
   table). 10/min ainda permite uso humano normal (clicar download
   uma dúzia de vezes em 60s) mas corta scraping. Configurável em
   `settings.rate_limit_export`; setting separado preserva
   `rate_limit_default` para os outros endpoints.

**Alternativas consideradas:**
- `pandas.to_csv` direto sobre uma lista de dicts — rejeitado: importa
  pandas mesmo quando o handler não está rodando o `/returns` (que é
  o único que precisa de pandas). `csv.writer` resolve com 6 linhas.
- Range vazio devolver 404 — rejeitado, ver item 1 acima.
- Reusar `rate_limit_default` — rejeitado: o threat model do CSV é
  diferente do JSON. Setting dedicado custa 1 linha e dá controle fino.
- Suportar `start_date`/`end_date` além de `period` (como sugerido no
  diagnóstico) — adiado para issue futura. O 95% dos casos é "últimos
  N períodos" via `period`; range explícito vale uma issue separada
  com seus próprios testes (intersecção período↔range, validação de
  datas inválidas, etc.).

**Trade-off:** primeira issue com setting de rate limit não-default;
abre porta para mais "limites por endpoint" (ex.: ingestion endpoints
podem precisar de limit ainda mais apertado). Aceitável — o vocabulário
do `limits` permite migrar para `@limiter.limit("...")` com string
literal a qualquer momento se a configuração virar bagunça.

---

## 2026-04-30 — Universo de ativos asiáticos: 20 JP + 10 AU + 10 HK
**Issue:** ISSUE-016
**Decisão:** Adicionadas três listas em `backend/config/symbols.py`:
- `STOCKS_JP` (20 nomes do Nikkei 225 — Toyota, Sony, SoftBank, Keyence,
  Mitsubishi UFJ, etc., sufixo yfinance `.T` = TSE).
- `STOCKS_AU` (10 nomes do ASX 200 — BHP, CBA, CSL, NAB, WBC, ANZ, MQG, WES,
  WOW, TLS, sufixo `.AX`).
- `STOCKS_HK` (10 nomes do Hang Seng — Tencent, Alibaba, HSBC, AIA, CCB,
  ICBC, Ping An, HKEX, China Mobile, Towngas, sufixo `.HK`).
Todas entram em `ALL_STOCKS` e em `SYMBOLS_BY_TYPE["stock"]` — pipeline de
ingestão (`backend.ingestion.loader.ingest_prices`) passa a buscá-las sem
mudança de código adicional. Sufixos roteados em `get_country_for_symbol`:
`.T → JP`, `.AX → AU`, `.HK → HK`.

**Alternativas consideradas:**
- Listar apenas índices (`^N225`, `^HSI`, `^AXJO`) sem ações individuais —
  rejeitado: o briefing pede cobertura de companhias asiáticas, não só
  benchmarks.
- Cobrir o universo completo (Nikkei 225 inteiro + ASX 200 + HSI completo,
  ~480 tickers) — rejeitado: explosão de chamadas yfinance (limite de
  ~8 req/min) sem ganho marginal de inteligência de mercado para o caso de
  uso atual da Bem Energia. As 40 selecionadas cobrem >70% da capitalização
  de mercado de cada índice.
- Usar `0700.HK` no formato sem zero-pad (`700.HK`) — rejeitado: yfinance
  exige o formato com 4 dígitos zero-padded para ações HK, idem para
  códigos JP de 4 dígitos como `7203.T`.

**Trade-off:** ingestão diária ganha ~40 chamadas yfinance (~5 minutos extra
no batch). Custos negligíveis dentro do limite atual. Tickers HK e JP têm
horários de fechamento diferentes (Tokyo fecha ~15:00 JST, HK fecha
~16:00 HKT, ASX fecha ~16:00 AEDT) — todos antes do trigger de 22:00 BRT do
agendador (ISSUE-015), então não há risco de capturar dia parcial.

---

## 2026-04-30 — Hong Kong adicionado a `COUNTRIES` (13 países no total)
**Issue:** ISSUE-016
**Decisão:** Nova entrada `HK / HKG / Hong Kong / Asia / HKD / HKEX / .HK`
em `backend/data/sectors_gics.py:COUNTRIES`. Japão (JP) e Austrália (AU) já
existiam pré-ISSUE-016 com sufixos corretos.
**Alternativas consideradas:** mapear HK como subdivisão de CN
(`get_country_for_symbol("0700.HK") → "CN"`) para reduzir cardinalidade —
rejeitado: HKD ≠ CNY, HKEX ≠ SSE/SZSE, regulação distinta. Tratar como
jurisdição separada é o padrão de inteligência de mercado.
**Trade-off:** o índice `^HSI` (Hang Seng) foi mantido mapeado para `CN` em
`get_country_for_symbol` — ele *é* listado em HK mas trackeia majoritariamente
H-shares de empresas chinesas continentais. A inconsistência é deliberada
e está coberta por teste explícito (`test_indices_asiaticos_continuam_mapeando_corretamente`)
para que mudanças futuras precisem decidir conscientemente.

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

## 2026-04-30 — Cache via fastapi-cache2: backend opcional, no-op em testes
**Issue:** ISSUE-011
**Decisão:** Adotado `fastapi-cache2` como camada de cache HTTP nos
endpoints pesados de mercado. Quatro componentes:
1. `backend/api/_cache.py` instala `InMemoryBackend` em escopo de import
   via `init_cache_sync()`. Side effect intencional: garante que rotas
   decoradas com `@cache(...)` funcionam mesmo em testes que usam
   `TestClient(app)` sem context-manager (lifespan não roda nesse caso).
2. `backend/app.py` lifespan chama `await init_cache_async()` no startup.
   Se `settings.redis_url` está setada e o ping responde, faz upgrade do
   backend para `RedisBackend`. Falha (URL não setada, módulo redis
   ausente, ou ping falhou) cai silenciosamente em `InMemoryBackend` com
   `WARNING` no log — Redis é opcional, não bloqueia o startup.
3. `/api/market/summary` e `/api/market/sectors` decorados com
   `@cache(expire=CACHE_TTL_MARKET, namespace="market")` (TTL 900s).
   Chave inclui método HTTP, path e query string — `period=90d` e
   `period=180d` são entradas distintas.
4. `conftest.py` define `CACHE_ENABLED=false` para testes; a flag passa
   para `FastAPICache.init(..., enable=...)` e o decorador vira no-op
   silencioso (não lê, não escreve, executa sempre o handler). Smoke
   tests existentes não precisam de mudança. Testes específicos de cache
   (`test_cache.py`) re-inicializam localmente com `enable=True`.

**Alternativas consideradas:**
- (a) **Exigir Redis sempre** (sem InMemoryBackend fallback). Mais simples
  mas inviável: ambiente da Routine roda em cloud sem Redis, e dev local
  nem sempre tem Redis. Quebraria startup. Rejeitada.
- (b) **Cache manual sem lib** (lru_cache wrapper, ou Redis SDK direto).
  Mais código, sem o benefício das injeções automáticas (request,
  response headers, ETag, Cache-Control). O diagnóstico §7.2 explicitamente
  recomenda `fastapi-cache2`. Rejeitada.
- (c) **`aiocache`**. Alternativa válida mas não há bridge oficial para
  FastAPI route-level decoration; o decorador da `fastapi-cache2` já
  resolve injection de Request/Response e geração de chaves estáveis.
  Rejeitada.
- (d) **Aplicar cache também em `/api/prices` e `/api/assets`**. Adiada:
  o diagnóstico recomenda `summary` e `sectors` por serem os mais pesados
  (loop de 16 índices + fan-out por setor). Os outros endpoints já
  retornam rápido em volume típico de uso interno. Pode ser feito em
  PR posterior se medições justificarem.

**Trade-off:**
- `InMemoryBackend` é process-local: em multi-worker (`uvicorn --workers N`),
  cada worker tem cache próprio, ou seja, o "hit rate" efetivo cai por
  fator N (cada worker miss-cache na 1ª request). Para o uso atual (single-
  worker, dev local) é inofensivo. Quando precisar escalar, configura
  `REDIS_URL` e o cache passa a ser distribuído sem mudar uma linha de
  código de aplicação.
- O `slowapi` (ISSUE-010) também usa storage em memória por default. Há
  uma sinergia futura: quando Redis estiver setado, podemos passar o
  mesmo URI ao Limiter (`storage_uri="redis://..."`) e ter rate-limit
  distribuído também. Não feito agora para manter o diff focado.
- Side effect no import de `_cache.py` (chamada a `init_cache_sync()` em
  module-level) contraria parcialmente o espírito de ISSUE-014 (eliminar
  side effects). Justificativa: `TestClient(app)` sem context-manager não
  dispara lifespan, e qualquer rota decorada com `@cache` lança
  `AssertionError: You must call FastAPICache.init` na primeira request.
  Mover o init para um pytest fixture global resolveria sem side effect,
  mas inverteria responsabilidades (test setup virando pré-requisito de
  produção). Documentado como decisão deliberada.

**Como apply / quando revisitar:**
- Para subir Redis em dev local: `docker compose -f docker-compose.dev.yml
  up -d redis` e adicionar `REDIS_URL=redis://localhost:6379/0` ao `.env`.
- Para invalidar manualmente:
  `await FastAPICache.clear(namespace="market")` (apaga só market).
- Para cachear outro endpoint: importar
  `from fastapi_cache.decorator import cache` e adicionar
  `@cache(expire=N, namespace="...")` após o `@limiter.limit(...)`.
- Quando ISSUE-014 (remover side effects de import) for executada, mover
  `init_cache_sync()` no module-level para um fixture autouse no
  `conftest.py` resolve sem perder as garantias.

**Bug encontrado e contornado:**
`FastAPICache.init` (fastapi-cache2 0.2.2) retorna early se já
inicializado: `if cls._init: return`. Sem `reset()` antes, qualquer
re-inicialização (lifespan tentando upgrade para Redis após o
`init_cache_sync()` do import; testes mudando `enable=True/False`)
silenciosamente vira no-op. `init_cache_sync` e `init_cache_async`
chamam `FastAPICache.reset()` antes de `init` — explicitado no docstring.

---

## 2026-04-30 — `net_debt_ebitda`: cálculo trailing do Q mais recente, sem fallback
**Issue:** ISSUE-013
**Decisão:** A métrica `net_debt_ebitda` no snapshot de `valuation_multiples`
passa a ser calculada de fato (deixa de ser placeholder/NULL) por uma de
duas funções novas em `backend/ingestion/fundamentals_loader.py`:
- `compute_net_debt_ebitda(net_debt, ebitda)` — função pura, devolve
  `net_debt / ebitda` quando ambos são finitos e `ebitda != 0`; devolve
  None nos demais casos (None em qualquer operando, ebitda=0, NaN, inf,
  tipo não numérico).
- `latest_net_debt_ebitda(session, company_id)` — busca a `FinancialStatement`
  mais recente por `period_end DESC` (limit 1) e aplica a fórmula.

O loader chama `latest_net_debt_ebitda(session, company.id)` ao montar o
snapshot, **depois** do bloco que faz commit das demonstrações financeiras —
então a métrica reflete o Q recém-ingerido quando yfinance trouxe novos
statements, e cai pro último Q persistido em runs anteriores quando não
trouxe (ex.: rate-limit do yfinance retornou só `info`).
**Alternativas consideradas:**
- (a) Calcular dentro do loop `for col in income.columns:` rastreando o
  `max(period_end)` em variáveis locais e construindo o snapshot a partir
  disso. Funciona quando o batch da chamada atual traz income/balance, mas
  perde a métrica nas chamadas em que yfinance retorna só `info`. O loader
  precisa funcionar em ambos os modos (ingestão completa e refresh de
  multiples), portanto rejeitada.
- (b) Calcular sobre TTM (last 4 quarters somados): `net_debt` mais recente
  + soma de `ebitda` dos últimos 4 Qs. Mais robusto contra sazonalidade,
  mas o briefing original (§7.2 I6) diz `(total_debt - cash) / ebitda`
  sem qualificar TTM, e o yfinance já entrega EBITDA trailing no income
  statement quando disponível. Mantida a fórmula simples; revisitar se
  surgir demanda de TTM explícito.
- (c) Cair pro Q anterior quando `ebitda=0` no Q mais recente. Rejeitada:
  serve um número que parece atual mas é defasado em 3 meses, sem
  sinalização. Usuário interno olhando o dashboard tomaria decisão
  errada. Melhor mostrar None (que o frontend renderiza como "—").
- (d) Aceitar `ebitda<0` como divisor válido (empresa com EBITDA negativo
  produziria `net_debt_ebitda` negativo, métrica matematicamente válida
  mas sem significado financeiro). Mantida — só `ebitda=0` é tratado
  como caso especial. Empresa com prejuízo operacional severo gera
  número negativo que sinaliza "métrica não comparável", consistente
  com convenção de mercado.
- (e) Persistir como Decimal explícito em vez de float. Rejeitada: a
  coluna é `Numeric(12,4)` no schema (precisão suficiente), e o input
  vem do SQLAlchemy como Decimal — a conversão para float dentro de
  `compute_net_debt_ebitda` é interna; o ORM faz o cast de volta para
  Numeric ao persistir.

**Trade-off:**
- A métrica reflete o snapshot trailing do Q mais recente. Empresas
  com forte sazonalidade podem ter números muito diferentes entre Q1
  e Q3. Documentar no frontend é responsabilidade da issue de UX
  (não desta).
- O lookup `SELECT ... ORDER BY period_end DESC LIMIT 1` é executado
  uma vez por símbolo no pipeline de ingestão, em batches de tamanho
  controlado. Custo desprezível mesmo com 600 tickers.
- Fórmula é específica para empresas (não-financeiras). Bancos/seguradoras
  usam outras métricas de alavancagem; para esses, `net_debt_ebitda` é
  numericamente computável mas economicamente sem sentido. O briefing
  trata todas as empresas igualmente — alinhado.

---

## 2026-04-30 — Validação estrita de `period`: rejeita silenciamento por padrão
**Issue:** ISSUE-012
**Decisão:** Toda string `period` aceita pelos endpoints
(`/api/prices/{symbol}/history`, `/api/prices/{symbol}/returns`,
`/api/market/sectors`) passa por `backend/api/_periods.parse_period`
antes de qualquer outra lógica. Aceita exatamente
`<inteiro positivo><unidade>` com unidade em {d, w, m, y}, range
`1d..10y` (inclusive). Qualquer outro formato → `HTTPException(422)`
com mensagem útil. O retorno é um `ParsedPeriod` (frozen dataclass)
com `raw` (string original, para ecoar na resposta) e `delta`
(timedelta, para cálculo de start_date). Wired via
`Depends(period_dep)`.
**Alternativas consideradas:**
- (a) Manter o fallback silencioso para 90d. Rejeitada — mascara typos
  do cliente (ex.: `peridod=180d` virava `90d` sem aviso) e impede
  qualquer monitoramento de "uso indevido da API".
- (b) Validar via Pydantic `constr` ou `Annotated[str, ...]` no Query.
  Possível, mas a mensagem de erro do Pydantic em regex falha é
  genérica (`String should match pattern '...'`). Função dedicada
  permite mensagem de erro contextual ("range permitido", exemplos,
  o que está errado em específico) e centraliza o range check.
- (c) Aceitar formato extenso (`30days`, `1year`). Rejeitada — o
  contrato pré-existente do frontend já usa o formato curto e o
  briefing do projeto referencia `30d, 1y, etc.`. Mais formatos = mais
  superfície de teste sem ganho.
- (d) Aceitar maiúsculas (`30D`). Rejeitada — sem demanda do frontend
  e diverge do contrato do Yahoo Finance (yfinance usa lowercase). Se
  a demanda surgir, basta normalizar com `.lower()` antes do regex.
- (e) Retornar `ParsedPeriod` direto pelos handlers (ecoar `delta`
  como segundos no JSON). Rejeitada — quebra contrato existente
  (`period: str` nos response models) e o cliente espera receber a
  string que mandou.
**Trade-off:**
- Quebra de comportamento: clientes que mandavam strings inválidas e
  recebiam 200 com 90d agora recebem 422. Sem analytics de quem
  mandava o quê em produção, optei pela quebra explícita — é o
  comportamento documentado no diagnóstico §7.2 (I3) e o frontend já
  usa apenas formatos válidos (`30d`, `90d`, `180d`, `1y` — verificado
  por grep em `frontend/index.html`).
- O `default_key_builder` da fastapi-cache2 inclui `repr(kwargs)` na
  chave de cache. `ParsedPeriod` é frozen dataclass, então `repr` é
  estável entre instâncias com mesmo `raw`. Cache continua funcionando
  como antes (`period=90d` e `period=180d` viram entradas distintas;
  duas chamadas com `period=90d` viram a 2ª como hit).
- Função `prices._parse_period` removida (era o único usuário,
  agora substituída pela versão estrita de `_periods`). Mantém o diff
  focado e elimina código morto.

---

## 2026-04-30 — Lazy init dos módulos `connection`, `logging_config`, `_cache`
**Issue:** ISSUE-014
**Decisão:** Três módulos do backend deixam de fazer trabalho em escopo de
import:

1. **`backend/db/connection.py`** — `load_dotenv()`, `_resolve_database_url()`
   e `create_engine()` saem do top-level. Novos pontos de entrada:
   - `get_engine() -> Engine` cacheado via `lru_cache(maxsize=1)`. Primeira
     chamada lê `MARKET_DB_URL`, cria engine e — se SQLite — registra o
     listener de `PRAGMA`; chamadas seguintes devolvem o mesmo objeto.
   - `get_sessionmaker() -> sessionmaker` também cacheado.
   - `is_sqlite() -> bool` runtime helper (substitui o booleano
     module-level `IS_SQLITE`).
   - `_load_dotenv_once()` cacheado: garante que `.env` é lido no máximo
     uma vez por processo.
   - PEP 562 `__getattr__` mantém compat com `from connection import
     engine, IS_SQLITE, SessionLocal, DATABASE_URL` — atributos resolvem
     sob demanda, então o código existente continua funcionando sem
     edição em massa.

2. **`backend/config/logging_config.py`** — removida a linha
   `logger = setup_logging()` no fim do módulo. `os.makedirs(LOG_DIR)`
   é movido para dentro de `setup_logging()`, depois do guard de
   handlers. Adicionado `get_logger(name=None, level=INFO)` como ponto
   de entrada recomendado: chama `setup_logging()` (idempotente) e
   devolve o logger root ou um child (`market_platform.<name>`).

3. **`backend/api/_cache.py`** — removida a chamada `init_cache_sync()`
   em escopo de módulo. Em produção, o lifespan do FastAPI já cobre
   via `init_cache_async()` (que cai em `init_cache_sync` quando
   `REDIS_URL` não está setada). Em testes, adicionada fixture autouse
   session-scoped no `conftest.py` raiz que chama `init_cache_sync()`
   antes de qualquer teste rodar.

**Alternativas consideradas:**
- (a) **Substituir todos os callers de `engine`/`IS_SQLITE` para usar
  `get_engine()`/`is_sqlite()` diretamente.** Mais explícito mas
  refatoração maior (8+ arquivos), e o objetivo da ISSUE-014 é remover
  o side effect, não rebatizar a API. PEP 562 entrega o mesmo benefício
  com diff focado.
- (b) **Manter `logger = setup_logging()` no module-level.** Rejeitada:
  é exatamente o anti-padrão que a ISSUE-014 visa eliminar — importar
  `logging_config` cria diretório `logs/` e abre file handle, mesmo que
  o caller só queira inspecionar a função.
- (c) **Mover `init_cache_sync()` para fixture function-scoped.** Mais
  isolado, mas a fixture precisaria ser explicitamente referenciada em
  cada teste que importa `app`. Session-scoped autouse cobre todo o
  arquivo de testes sem ergonomia adicional.
- (d) **Inicializar o cache em um pytest_configure hook.** Equivalente
  funcionalmente, mas hooks de pytest são menos descobríveis que
  fixtures — o motivo da inicialização fica menos óbvio para quem lê
  o conftest.

**Trade-off:**
- Compat via PEP 562 depende de Python 3.7+. Codebase já requer 3.11
  (pinned em `requirements.txt` + uso de `from __future__ import
  annotations`), então não é restrição nova.
- Atributos lazy resolvem na primeira leitura — se múltiplos testes
  importam `connection.engine` em paralelo, o `lru_cache` de `get_engine`
  garante singleton mas há race window curta na 1ª chamada (irrelevante
  para o uso atual single-threaded em testes e startup de uvicorn).
- A fixture autouse no conftest roda 1x por sessão. Testes que tem
  `reset_cache_state` (function-scoped) continuam funcionando porque
  re-inicializam localmente; o estado deixado pela fixture session-scoped
  é o "default" entre testes, não o "estado durante teste".

**Como aplicar / quando revisitar:**
- Para forçar re-criação do engine (ex.: teste muda `MARKET_DB_URL`):
  `from backend.db.connection import get_engine, get_sessionmaker;
  get_engine.cache_clear(); get_sessionmaker.cache_clear()`.
- Para usar logger em código novo: `from backend.config.logging_config
  import get_logger; logger = get_logger(__name__)` em vez de
  `setup_logging()` — entrega o mesmo logger configurado, com nome
  filho informativo.
- Quando ISSUE-018 (watchlist persistente) ou outra issue precisar de
  acesso direto ao engine, usar `get_engine()` em vez do antigo
  `engine` global (mais explícito sobre lifecycle).

---

## 2026-04-29 — Bootstrap do git em `market_platform_unified/` (pré-requisito não executado)
**Issue:** N/A — procedimento de bootstrap
**Decisão:** O pré-requisito de inicializar git em `market_platform_unified/` e conectar ao `mullerdoskov/Global_Mkt` não estava concluído quando a Routine rodou pela primeira vez. A Routine inicializou o repositório neste run, conectou ao remote existente, e abriu o PR #1. O histórico do nested `Global_Mkt_2.0/` (2 commits) não foi incorporado — a Routine não pode fazer força push nem rebase sem autorização humana. Lucas deve resolver o histórico em conjunto com ISSUE-001.
**Alternativas consideradas:** abrir somente uma GitHub Issue descrevendo o bloqueio (sem código).
**Trade-off:** ao escolher inicializar o git e abrir o PR, a Routine entregou código funcional mas criou uma divergência de histórico entre o nested e o novo repositório — situação que ISSUE-001 precisa resolver.

---

## 2026-04-30 — Agendamento via Task Scheduler local + wrapper .ps1; lógica em módulo Python
**Issue:** ISSUE-015
**Decisão:** Três peças acopladas:
1. **`backend.scheduling.incremental_update`** — módulo Python que envolve
   `update_prices` com logging per-run, exit codes diferenciados
   (`0`/`1`/`2`) e nome de log estável (`incremental_update_<UTC>.log`).
   É o ponto de entrada testável; toda a lógica fica aqui.
2. **`scripts/scheduled_update.{ps1,sh}`** — dois wrappers shell finos.
   Resolvem o root do projeto (a partir do path do próprio script),
   ativam venv se houver, carregam `.env`, e delegam ao módulo Python.
   Sem lógica de negócio — qualquer mudança de comportamento mexe no
   Python, não nos wrappers.
3. **`scripts/Register-ScheduledTask.ps1`** — helper idempotente que
   registra o job no Windows Task Scheduler com trigger diário às 22:00
   hora local da máquina, `StartWhenAvailable=true` (acorda do sleep) e
   `ExecutionTimeLimit=2h`.
**Alternativas consideradas:**
- (B) Cron na máquina Lucas-only: viável em WSL, mas o estado padrão da
  estação é Windows e o cron WSL exige WSL rodando em background. Mais
  setup, mais frágil.
- (C) Prefect / Dagster (orquestrador full): adiciona ~1 servidor a mais
  para operar (Prefect Cloud agente, ou self-hosted server + worker),
  observabilidade e UI vêm de graça mas custam complexidade que ainda
  não compensa para 1 job em 1 máquina. O módulo Python já é
  empacotável como flow/job se um dia migrar — basta envolver
  `run_incremental_update` num `@flow` decorator.
- (D) GitHub Actions cron: o runner não tem acesso ao Postgres local nem
  ao filesystem do Lucas. Inviável sem expor o banco ou colocar
  Postgres em cloud (mudança maior de infra, fora do escopo).
- (E) APScheduler dentro do FastAPI: requer manter a API rodando 24/7 só
  para o agendador — acopla disponibilidade do scheduler à do servidor
  HTTP, e perde o scheduler se o uvicorn cair. Anti-padrão.
**Trade-off:**
- "22:00 BRT" é responsabilidade do operador: o Task Scheduler nativo
  não tem suporte direto a fuso, dispara em hora local da máquina.
  Documentado no BACKEND_README — máquina precisa estar em
  `America/Sao_Paulo`. Em servidor UTC, ajustar `-At` para `01:00`.
- O run não é cluster-aware: se Lucas tiver mais de uma máquina rodando
  o job, ambos disparam. Aceitável — `update_prices` é idempotente
  (UPSERT por (asset_id, date)), e a probabilidade de overlap é baixa.
- Exit code `2` é uma convenção interna; nenhum monitor externo reage
  a ele ainda. Logs por run são a única observabilidade — quem operar
  precisa olhar `logs/scheduler/`.
- Quando ISSUE-009 entrou em vigor, agendamentos passariam a precisar
  `alembic upgrade head` antes de cada run? **Não.** O `update_prices`
  só faz INSERT/UPSERT em tabelas existentes; mudanças de schema não
  são iniciadas pelo job. Migrações ficam no fluxo de deploy/release,
  não no agendamento de ingestão.
**Como aplicar:**
- Para rodar manualmente:
  `python -m backend.scheduling.incremental_update [-d 5] [--log-dir DIR]`.
- Para agendar no Windows: `cd scripts && .\Register-ScheduledTask.ps1`
  (idempotente; reaplica config se já existir).
- Para mudar a hora ou o lookback: re-rode `Register-ScheduledTask.ps1`
  com `-At` e `-Days` — o script desregistra e recria.
- Para um dia migrar para orquestrador: o módulo Python já é o ponto
  de entrada; envolver `run_incremental_update` num `@flow` (Prefect)
  ou `@op` (Dagster) é trivial.
