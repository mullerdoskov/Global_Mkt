# Market Platform Unified — Backend FastAPI

Backend unificado que funde o `emergent` (frontend design system) com o `market_platform` (dados reais de yfinance).

## Estrutura do Projeto

```
backend/
├── __init__.py
├── app.py                    # FastAPI app principal com CORS, routers, lifecycle
├── cli.py                    # CLI para ingestão e gerenciamento
├── ingest_resumable.py       # Ingestão resumível com checkpoint (intacto)
├── config/
│   ├── __init__.py
│   ├── settings.py           # Configurações Pydantic (novo)
│   ├── logging_config.py     # Logging rotativo (copiado intacto)
│   └── symbols.py            # ~600 tickers (copiado intacto)
├── db/
│   ├── __init__.py
│   ├── connection.py         # SQLAlchemy engine (copiado intacto)
│   └── schema.py             # 9 tabelas ORM (copiado intacto)
├── data/
│   ├── __init__.py
│   ├── calendar.py           # Calendário dias úteis (copiado intacto)
│   └── sectors_gics.py       # 34 setores + 12 países (copiado intacto)
├── ingestion/
│   ├── __init__.py
│   ├── yf_client.py          # Cliente yfinance com rate-limit (copiado intacto)
│   ├── loader.py             # Pipeline OHLCV (copiado intacto)
│   └── fundamentals_loader.py # DRE/balanço/FCF (copiado intacto)
├── api/
│   ├── __init__.py
│   ├── router.py             # Agregador de routers (novo)
│   ├── models.py             # Modelos Pydantic (novo)
│   ├── assets.py             # GET /api/assets (novo)
│   ├── prices.py             # GET /api/prices (novo)
│   ├── market.py             # GET /api/market (novo)
│   ├── fundamentals.py       # GET /api/fundamentals (novo)
│   ├── ingestion.py          # GET /api/ingestion (novo)
│   └── export.py             # GET /api/export/{symbol}.csv (novo)
├── sql/
│   └── useful_queries.sql    # Queries para análise (novo)
├── requirements.txt          # Dependências Python
└── logs/                      # Diretório de logs (criado em runtime)
```

## Setup Inicial

### 1. Ambiente Virtual

```bash
cd /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar Dependências

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configurar .env

```bash
cp .env.example .env
```

Editar `.env`:

```env
# PostgreSQL (produção)
MARKET_DB_URL=postgresql+psycopg2://postgres:SUA_SENHA@localhost:5432/market_db

# Ou SQLite (desenvolvimento)
MARKET_DB_URL=sqlite:///market_db.sqlite

CORS_ORIGINS=http://localhost:3000,http://localhost:5173
DEBUG=false
```

### 4. Inicializar Banco de Dados

A criação canônica de tabelas é feita pelo Alembic (ver
[Migrações de schema](#migrações-de-schema)). Em ambiente vazio, basta:

```bash
# Aplica todas as migrações pendentes (cria as 9 tabelas)
alembic upgrade head

# Testa conexão
python -m backend.cli db-test
```

> Compatibilidade: o startup do FastAPI ainda chama `create_all_tables()`
> como rede de segurança (idempotente — não recria tabelas existentes).
> Em produção, **rode `alembic upgrade head` antes de subir a API**;
> evoluções de schema só são aplicadas via migração, nunca via
> `create_all_tables`.

## Migrações de schema

A partir de ISSUE-009, mudanças de schema do banco são versionadas via
[Alembic](https://alembic.sqlalchemy.org/). A configuração lê
`MARKET_DB_URL` do ambiente (mesmo contrato do backend desde ISSUE-004).
Comandos rodam a partir da raiz `market_platform_unified/`:

```bash
# Aplicar todas as migrações pendentes
alembic upgrade head

# Ver versão atual
alembic current

# Ver histórico
alembic history --verbose

# Gerar nova migração a partir das mudanças no Base.metadata
alembic revision --autogenerate -m "descreve a mudanca"

# Reverter última migração (uso raro em prod)
alembic downgrade -1
```

Fluxo recomendado para evoluir o schema:

1. Editar `backend/db/schema.py` (adicionar coluna, índice, tabela).
2. Rodar `alembic revision --autogenerate -m "..."`.
3. Inspecionar o arquivo gerado em `alembic/versions/` — o autogenerate
   acerta tabelas e colunas, mas pode errar `server_default`, ENUMs
   Postgres e renomeações (que aparecem como drop+create).
4. Rodar `alembic upgrade head` localmente. Confirmar que os testes
   continuam passando.
5. Commitar `schema.py` + a nova migração no mesmo PR.

O teste `tests/test_alembic_migration.py::test_no_drift_entre_metadata_e_migration_head`
falha se alguém alterar `schema.py` sem gerar migração — gate no CI.

## Rate limiting

A partir de ISSUE-010, todos os endpoints sob `/api` são limitados via
[slowapi](https://github.com/laurentS/slowapi). A chave de identificação é o
endereço IP remoto (`get_remote_address`); o limite default é
**60 requisições por minuto por IP**.

Endpoints fora do gate (não limitados):
- `GET /health`
- `GET /api/info`
- Frontend estático servido pelo `StaticFiles` em `/`
- `/docs`, `/redoc`, `/openapi.json`

### Configuração

Variáveis de ambiente (ver `.env.example`):

```env
# Vocabulário do `limits`: <count>/<seconds|minute|hour|day>
RATE_LIMIT_DEFAULT=60/minute

# Limite mais agressivo para o endpoint de exportação CSV (ISSUE-017).
# Aplica-se a `/api/export/{symbol}.csv` apenas — demais endpoints seguem
# `RATE_LIMIT_DEFAULT`. Valor inicial 10/min/IP.
RATE_LIMIT_EXPORT=10/minute

# Em produção: true. Em testes: false (já configurado em conftest.py).
RATE_LIMIT_ENABLED=true
```

Quando `RATE_LIMIT_ENABLED=false`, o `Limiter` é instanciado em modo no-op:
decoradores e middleware seguem montados mas não bloqueiam — útil para os
testes (que disparam várias chamadas em sequência da mesma origem) e para
dev local quando se quer eliminar o gate como variável.

### Resposta quando o limite é excedido

Status `429 Too Many Requests` com corpo JSON descrevendo o limite atingido:

```json
{ "error": "Rate limit exceeded: 60 per 1 minute" }
```

O cabeçalho `Retry-After` (em segundos) também é emitido pelo `slowapi`.

### Onde mexer no código

- `backend/api/_limiter.py` — instância única do `Limiter` lida por
  `app.py` e por cada router.
- `backend/app.py` — registra `app.state.limiter`, exception handler e
  `SlowAPIMiddleware`.
- Cada `backend/api/*.py` — endpoints decorados com
  `@limiter.limit(settings.rate_limit_default)` e recebem `request: Request`
  como parâmetro nomeado (exigido pelo slowapi).

Para tornar o limite mais estrito num endpoint específico, troque o
argumento do decorador (ex.: `@limiter.limit("10/minute")`). Para isentar
um endpoint do gate, remova o decorador.

## Cache HTTP

A partir de ISSUE-011, endpoints de mercado pesados (`/api/market/summary`
e `/api/market/sectors`) são cacheados via
[fastapi-cache2](https://github.com/long2ice/fastapi-cache). TTL padrão é
**15 minutos** (`CACHE_TTL_MARKET = 900` em `backend/api/market.py`). A
chave de cache inclui método HTTP, path e query string — `/api/market/sectors`
com `period=90d` e com `period=180d` são entradas distintas.

### Backends de cache

`backend/api/_cache.py` escolhe o backend automaticamente:

| Cenário | Backend | Quando usar |
|---|---|---|
| `REDIS_URL` setada e ping ok | `RedisBackend` | Produção, multi-worker, multi-instância |
| `REDIS_URL` ausente | `InMemoryBackend` | Dev local single-process |
| `REDIS_URL` setada mas ping falhou | `InMemoryBackend` (com `WARNING` no log) | Tolerância a Redis indisponível em prod |
| `CACHE_ENABLED=false` | qualquer backend, mas decorador vira no-op | Testes, debug local |

`InMemoryBackend` é process-local — em multi-worker (`uvicorn --workers N`)
cada worker mantém sua própria cópia, então a primeira request de cada
worker miss-cache. Para cache distribuído, configure Redis (ver abaixo).

### Subir Redis local

```bash
# Sobe Redis (e Postgres, opcional) via docker-compose
docker compose -f docker-compose.dev.yml up -d redis

# Confere
docker compose -f docker-compose.dev.yml ps
docker exec mp-redis redis-cli ping  # PONG

# Configure o .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env
```

### Configuração

Variáveis de ambiente (ver `.env.example`):

```env
# Opcional. Sem essa variável, cache é process-local.
REDIS_URL=redis://localhost:6379/0

# Em produção: true. Em testes: false (já configurado em conftest.py).
CACHE_ENABLED=true
```

### Onde mexer no código

- `backend/api/_cache.py` — escolha de backend, `init_cache_sync` e
  `init_cache_async`. Lifespan chama `init_cache_async`; o módulo já chama
  `init_cache_sync()` no import como fallback síncrono (essencial para
  testes que pulam o lifespan).
- `backend/api/market.py` — endpoints decorados com
  `@cache(expire=CACHE_TTL_MARKET, namespace="market")`.
- Para cachear outro endpoint, importe `from fastapi_cache.decorator import cache`
  e adicione o decorador. O handler pode ser sync ou async — fastapi-cache2
  rodaria handlers sync via `run_in_threadpool` automaticamente.

### Invalidação

Não há invalidação manual implementada — o TTL controla expiração. Para
forçar limpeza:

```python
from fastapi_cache import FastAPICache
await FastAPICache.clear(namespace="market")  # apaga só /api/market/*
await FastAPICache.clear()                    # apaga tudo
```

## Agendamento

A partir de ISSUE-015, a atualização incremental diária é disparada por
um agendador externo (Windows Task Scheduler ou cron) via wrappers em
`scripts/`. A lógica fica no módulo Python
`backend.scheduling.incremental_update` — testável e independente de
shell.

### Quem chama o quê

```
Windows Task Scheduler  ──►  scripts/scheduled_update.ps1
cron / WSL              ──►  scripts/scheduled_update.sh
                                    │
                                    │ ativa venv, carrega .env, delega
                                    ▼
                       python -m backend.scheduling.incremental_update
                                    │
                                    │ chama update_prices(lookback_days)
                                    ▼
                       backend.ingestion.loader.update_prices
                       (mesmo pipeline do `python -m backend.cli update-prices`)
```

### Exit codes

Propagados do módulo Python para o agendador:

| Código | Significado | Como reagir |
|---|---|---|
| `0` | Run OK, todas as ingestões bem-sucedidas | Task Scheduler marca verde, sem ação |
| `2` | Run completo mas com `errors > 0` (ex.: rate-limit em 1 ticker) | Inspecionar log do run; sem reagendamento automático |
| `1` | Falha não recuperada (exception) | Ação humana — checar conectividade, env, banco |

A diferenciação `1 vs 2` evita que cada falha parcial de yfinance
(comum: 429 esporádico em 1 de ~600 tickers) marque o run inteiro como
FAILED no Task Scheduler. Logs por run ficam em
`<repo>/logs/scheduler/incremental_update_YYYY-MM-DDTHHMMSSZ.log`
(timestamp em UTC). O destino pode ser sobrescrito via env
`SCHEDULER_LOG_DIR` ou flag `--log-dir`.

### Rodar manualmente

```bash
# Padrão: lookback 5 dias, log em <repo>/logs/scheduler/
python -m backend.scheduling.incremental_update

# Customizar lookback
python -m backend.scheduling.incremental_update -d 10

# Custom log dir
python -m backend.scheduling.incremental_update --log-dir C:\ProgramData\MDP\logs
```

### Agendar no Windows Task Scheduler

A partir de PowerShell elevado (ou simplesmente sob o usuário que vai
rodar a task — não exige admin se a task rodar como o próprio usuário):

```powershell
cd <repo>\scripts
.\Register-ScheduledTask.ps1                    # 22:00 local, lookback 5
.\Register-ScheduledTask.ps1 -At "21:30" -Days 10
```

O script é **idempotente**: se a task já existir, é desregistrada e
recriada com a nova configuração. Verificar:

```powershell
Get-ScheduledTask -TaskName "MDP Incremental Update" | Format-List *
```

Desregistrar:

```powershell
Unregister-ScheduledTask -TaskName "MDP Incremental Update" -Confirm:$false
```

> **Hora local vs BRT.** O Task Scheduler nativo só dispara em hora
> local da máquina. Garanta que a máquina alvo esteja em
> `America/Sao_Paulo` (default em estações de trabalho BR) antes de
> assumir que "22:00" é "22:00 BRT". Em servidor UTC, ajuste `-At`
> para `01:00` (= 22:00 BRT no horário padrão).

### Agendar no Linux / WSL via cron

Tornar o `.sh` executável e adicionar à crontab:

```bash
chmod +x <repo>/scripts/scheduled_update.sh
crontab -e
# Diário às 22h local — máquina precisa estar em America/Sao_Paulo
0 22 * * * /caminho/para/<repo>/scripts/scheduled_update.sh >> /var/log/mdp_wrapper.log 2>&1
```

### Onde mexer no código

- `backend/scheduling/incremental_update.py` — lógica do run agendado
  (exit codes, log per-run, plumbing para `update_prices`).
- `scripts/scheduled_update.ps1` — wrapper PowerShell (ativa venv,
  carrega `.env`, delega).
- `scripts/scheduled_update.sh` — wrapper Bash (mesma estrutura).
- `scripts/Register-ScheduledTask.ps1` — registra o job no Windows
  Task Scheduler de forma idempotente.

Para um dia migrar para um orquestrador (Prefect/Dagster), o módulo
Python já é o ponto de entrada — basta envolvê-lo numa flow/job.

## Backups do PostgreSQL

A partir de ISSUE-023, o PostgreSQL é backupeado **semanalmente** via
`pg_dump`, disparado pelo Windows Task Scheduler ou cron usando
wrappers em `scripts/`. Diferente do agendamento (ISSUE-015), aqui não
há módulo Python — `pg_dump` faz o trabalho e os scripts só fazem
environment setup.

### Pré-requisitos

- `pg_dump` no PATH. Em Windows: `winget install PostgreSQL.PostgreSQL`.
  Em Linux: `apt install postgresql-client`.
- `MARKET_DB_URL` apontando para PostgreSQL. URLs `sqlite:` são
  rejeitadas (use cópia de filesystem para SQLite).

### Quem chama o quê

```
Windows Task Scheduler  ──►  scripts/backup_postgres.ps1
cron / WSL              ──►  scripts/backup_postgres.sh
                                    │
                                    │ carrega .env, valida URL,
                                    │ pg_dump -Fc -f <dump>,
                                    │ purge mtime > BACKUP_RETENTION_DAYS
                                    ▼
                       backups/postgres/market_db_<UTC>.dump
                       logs/backups/backup_<UTC>.log
```

### Exit codes

| Código | Significado |
|---|---|
| `0` | Dump OK e retenção concluída |
| `1` | Falha hard (pg_dump não no PATH, URL ausente / sqlite, dump não-zero) |
| `2` | Dump OK mas retenção gerou warnings (ex.: arquivo bloqueado) |

### Configuração

| Env / flag | Default | Descrição |
|---|---|---|
| `BACKUP_DIR` | `<repo>/backups/postgres/` | Onde salvar os `.dump` |
| `BACKUP_RETENTION_DAYS` | `90` | Idade max em dias antes de purgar |
| `BACKUP_LOG_DIR` | `<repo>/logs/backups/` | Onde escrever logs do wrapper |

### Rodar manualmente

```powershell
# Windows
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup_postgres.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup_postgres.ps1 -RetentionDays 180
```

```bash
# Linux / WSL
./scripts/backup_postgres.sh
./scripts/backup_postgres.sh --retention-days 180
```

### Agendar no Windows Task Scheduler

```powershell
cd <repo>\scripts
.\Register-BackupTask.ps1                   # domingo 03:00, retenção 90
.\Register-BackupTask.ps1 -At "04:00" -RetentionDays 180
.\Register-BackupTask.ps1 -DayOfWeek Saturday
```

Idempotente. Verificar:

```powershell
Get-ScheduledTask -TaskName "MDP Postgres Backup" | Format-List *
Unregister-ScheduledTask -TaskName "MDP Postgres Backup" -Confirm:$false
```

### Agendar no Linux / cron

```bash
chmod +x <repo>/scripts/backup_postgres.sh
crontab -e
# Domingo 03:00 hora local
0 3 * * 0 /caminho/para/<repo>/scripts/backup_postgres.sh >> /var/log/mdp_backup.log 2>&1
```

### Restaurar de um dump

`pg_dump -Fc` gera formato custom; restaure com `pg_restore`:

```bash
# Restore completo num DB vazio
pg_restore --dbname="postgresql://user:pass@host:5432/market_db_restore" \
           --clean --if-exists \
           backups/postgres/market_db_2026-04-30T030000Z.dump

# Restore parcial (apenas uma tabela)
pg_restore --dbname="..." --table=prices_daily \
           backups/postgres/market_db_2026-04-30T030000Z.dump
```

> **Off-host não está incluído.** O backup mora no mesmo disco do
> servidor. Falha de hardware leva o dump junto. Próxima evolução
> natural: `aws s3 cp` / `rclone copy` no fim do wrapper. Issue
> dedicada quando o requisito for formal.

## OS 12 ENDPOINTS REST

### 1. Assets (`/api/assets`)

```
GET /api/assets
  Parâmetros: ?asset_type=stock&country=BR&sector=Energia&page=1&page_size=20
  Retorna: Lista de ativos com filtros e paginação

GET /api/assets/search?q=PETR
  Parâmetros: q (obrigatório, min 1 char)
  Retorna: Ativos cujo símbolo/nome contém "PETR"

GET /api/assets/{symbol}
  Exemplo: /api/assets/PETR3.SA
  Retorna: Detalhes completos (company info, último preço)
```

### 2. Preços (`/api/prices`)

```
GET /api/prices/{symbol}/history?period=90d&interval=1d
  Exemplo: /api/prices/AAPL/history?period=90d
  Retorna: Série histórica OHLCV (open, high, low, close, volume)

GET /api/prices/{symbol}/returns?period=90d
  Retorna: Retorno diário + acumulado (em percentual)

GET /api/prices?asset_type=stock
  Retorna: Snapshot com últimos preços de todos os ativos
```

### 3. Mercado (`/api/market`)

```
GET /api/market/summary
  Retorna: Últimos preços dos 16 índices globais (S&P 500, Ibovespa, DAX, etc.)

GET /api/market/sectors?period=90d
  Retorna: Performance média por setor GICS

GET /api/market/countries
  Retorna: Contagem de ativos por país
```

### 4. Fundamentos (`/api/fundamentals`)

```
GET /api/fundamentals/{symbol}
  Exemplo: /api/fundamentals/PETR3.SA
  Retorna: DRE, balanço, FCF dos últimos 4 trimestres

GET /api/fundamentals/{symbol}/valuation
  Retorna: Múltiplos de valuation (P/E, P/B, EV/EBITDA, ROE, margens, etc.)
```

### 5. Ingestão (`/api/ingestion`)

```
GET /api/ingestion/status
  Retorna: Status geral (últimos 10 logs, contagem sucesso/erro)
```

## Ingestão de Dados

### Opção 1: Pipeline Padrão

```bash
# Ingere preços (90 dias)
python -m backend.cli ingest-prices -p 90d

# Filtra por tipos
python -m backend.cli ingest-prices -p 90d -t stock,index

# Atualiza últimos 5 dias
python -m backend.cli update-prices -d 5

# Ingere fundamentos (apenas ações)
python -m backend.cli ingest-fundamentals
```

### Opção 2: Ingestão Resumível (com Checkpoint)

```bash
# Começa/retoma ingestão
python -m backend.cli ingest-resumable -p 90d

# Reseta checkpoint se houver erro crítico
python -m backend.cli reset-checkpoint

# Retoma novamente
python -m backend.cli ingest-resumable
```

## Executar o Backend

### Desenvolvimento

```bash
# Auto-reload ativado
python -m backend.app

# Ou diretamente com uvicorn
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Produção

```bash
# Sem auto-reload, worker processes
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Documentação Interativa

```
Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
```

## Banco de Dados

### 9 Tabelas

1. **countries** — Países (12)
2. **sectors_gics** — Setores (34)
3. **companies** — Empresas (mestre)
4. **assets** — Ativos (stocks, índices, commodities, FX, cripto)
5. **trading_calendar** — Calendário dias úteis
6. **prices_daily** — Preços históricos (fato)
7. **financial_statements** — DRE, balanço, FCF (fato)
8. **valuation_multiples** — Múltiplos de valuation (fato)
9. **ingestion_log** — Log de ingestão (auditoria)

### PostgreSQL ou SQLite

O código suporta ambos. Configure em `.env`:

```env
# PostgreSQL
MARKET_DB_URL=postgresql+psycopg2://user:password@localhost:5432/market_db

# SQLite (arquivo local)
MARKET_DB_URL=sqlite:///market_db.sqlite
```

## Tickers Disponíveis

### Ações (~240)
- Brasil (80): PETR3.SA, VALE3.SA, ITUB4.SA, BBDC4.SA, etc.
- EUA (120): AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, etc.
- UK (30): SHEL.L, AZN.L, HSBA.L, BP.L, etc.
- Alemanha (21): SAP.DE, SIE.DE, ALV.DE, etc.
- França (20): MC.PA, TTE.PA, AIR.PA, etc.
- Holanda/Suíça (20): ASML.AS, NESN.SW, etc.

### Índices (16)
S&P 500, NASDAQ, Dow Jones, Ibovespa, FTSE 100, DAX, CAC 40, AEX, Euro Stoxx 50, Nikkei 225, Hang Seng, Shanghai, ASX 200, TSX, VIX, Russell 2000

### Commodities (15)
Ouro, Prata, Platina, WTI, Brent, Gás Natural, Gasolina, Milho, Soja, Trigo, Café, Açúcar, Algodão, Cobre

### FX (16)
USD/BRL, EUR/BRL, EUR/USD, GBP/USD, USD/JPY, EUR/GBP, etc.

### Cripto (10)
BTC-USD, ETH-USD, BNB-USD, SOL-USD, XRP-USD, ADA-USD, DOGE-USD, AVAX-USD, DOT-USD, MATIC-USD

## Queries Úteis

Veja `backend/sql/useful_queries.sql` para:
- Última data de atualização por ativo
- Retorno acumulado (90d)
- Média de volume
- Performance por setor
- Distribuição país/setor
- E muito mais...

## Tratamento de Erros

### API Responses

```json
// Success
{
  "symbol": "PETR3.SA",
  "count": 90,
  "prices": [...]
}

// Error
{
  "detail": "Asset 'INVALID' not found"
}
```

### Logs

```
logs/market_platform.log         # Arquivo rotativo (10MB, 5 backups)
logs/checkpoint.txt              # Progresso de ingestão
```

## Performance

- Rate limit yfinance: ~8 req/min (evita bloqueio 429)
- Batch processing: 5 tickers/batch
- Paginação: máx 100 itens/página
- Índices otimizados em: symbol, asset_type, asset_id, date, company_id, etc.

## Arquivos Copiados Intactos (não modificar)

- `config/symbols.py` — 600 tickers
- `config/logging_config.py` — logging rotativo
- `db/connection.py` — engine SQLAlchemy (modificado: ISSUE-004 — sem credencial hardcoded)
- `db/schema.py` — 9 tabelas ORM (fonte da verdade para o autogenerate do Alembic — ver `alembic/`)
- `data/calendar.py` — calendário dias úteis
- `data/sectors_gics.py` — 34 setores + 12 países
- `ingestion/yf_client.py` — cliente yfinance com rate-limit
- `ingestion/loader.py` — pipeline ingestão
- `ingestion/fundamentals_loader.py` — fundamentos
- `ingest_resumable.py` — ingestão com checkpoint (SAGRADO)

## Troubleshooting

### Erro: "Connection refused"
```bash
# PostgreSQL não está rodando
# Ative o serviço ou use SQLite em desenvolvimento
```

### Erro: "429 Too Many Requests"
```bash
# yfinance está bloqueando
# Aguarde alguns minutos ou use --reset-checkpoint
python -m backend.cli reset-checkpoint
python -m backend.cli ingest-resumable
```

### Erro: "No module named 'backend.db'"
```bash
# Adicione o diretório raiz ao PYTHONPATH
export PYTHONPATH=/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified:$PYTHONPATH
```

## Próximos Passos

1. **Frontend React**: Integrar com endpoints FastAPI (http://localhost:8000/api)
2. **Cache**: Adicionar Redis para cache de preços frequentemente acessados
3. **WebSocket**: Real-time price updates
4. **Alerts**: Notificações quando preços atingem limiares
5. **Export**: CSV, Excel, PDF dos relatórios

## Versão

**1.0.0** — Lançamento inicial com 12 endpoints, 9 tabelas, 600+ tickers
