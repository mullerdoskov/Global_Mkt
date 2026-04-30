# Referência de Paths Absolutos — Backend FastAPI Unified

## Diretório Raiz do Projeto

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/
```

## Estrutura Completa com Paths Absolutos

### Backend Principal

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/
├── __init__.py
├── app.py                                [FastAPI app principal]
├── cli.py                                [CLI para ingestão]
├── ingest_resumable.py                   [Ingestão com checkpoint]
├── requirements.txt                      [Dependências Python]
```

### Configurações

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/config/
├── __init__.py
├── settings.py                           [Pydantic-settings — novo]
├── logging_config.py                     [Logging rotativo — copiado]
└── symbols.py                            [360 tickers — copiado]
```

### Database

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/db/
├── __init__.py
├── connection.py                         [SQLAlchemy engine — copiado]
└── schema.py                             [9 tabelas ORM — copiado]
```

### Data (Referência)

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/data/
├── __init__.py
├── calendar.py                           [Calendário dias úteis — copiado]
└── sectors_gics.py                       [34 setores + 12 países — copiado]
```

### Ingestion (Coleta de Dados)

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/ingestion/
├── __init__.py
├── yf_client.py                          [Cliente yfinance — copiado]
├── loader.py                             [Pipeline ingestão — copiado]
└── fundamentals_loader.py                [Fundamentos — copiado]
```

### API REST (Endpoints)

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/api/
├── __init__.py
├── router.py                             [Agregador de routers — novo]
├── models.py                             [30+ modelos Pydantic — novo]
├── assets.py                             [GET /api/assets (3) — novo]
├── prices.py                             [GET /api/prices (3) — novo]
├── market.py                             [GET /api/market (3) — novo]
├── fundamentals.py                       [GET /api/fundamentals (2) — novo]
└── ingestion.py                          [GET /api/ingestion (1) — novo]
```

### SQL (Queries Úteis)

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/sql/
└── useful_queries.sql                    [10 queries de análise — novo]
```

### Logs (Criado em Runtime)

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/logs/
├── market_platform.log                   [Log principal (rotativo 10MB)]
└── checkpoint.txt                        [Progresso de ingestão]
```

### Configuração do Projeto

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/
├── .env.example                          [Template de configuração — novo]
├── BACKEND_README.md                     [Documentação — novo]
├── ESTRUCTURA_FINAL.txt                  [Resumo visual — novo]
├── CHECKLIST_VALIDACAO.md                [Validação — novo]
└── PATHS_REFERENCE.md                    [Este arquivo — novo]
```

## Comandos com Paths Absolutos

### Setup Inicial

```bash
cd /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified

# Ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/backend/requirements.txt

# Copiar template .env
cp /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/.env.example \
   /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/.env
```

### Executar CLI

```bash
# Inicializar banco
python -m backend.cli db-init

# Testar conexão
python -m backend.cli db-test

# Ingerir preços
python -m backend.cli ingest-prices -p 90d

# Ingestão resumível
python -m backend.cli ingest-resumable

# Ingerir fundamentos
python -m backend.cli ingest-fundamentals
```

### Executar Backend

```bash
# Desenvolvimento
python -m backend.app

# Ou com uvicorn diretamente
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# Produção (sem reload)
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Import Statements

### Dentro do Package Backend

```python
from backend.config.settings import settings
from backend.config.symbols import ALL_STOCKS, INDICES, COMMODITIES
from backend.config.logging_config import setup_logging
from backend.db.connection import get_session, test_connection, engine
from backend.db.schema import Asset, Company, PriceDaily, FinancialStatement
from backend.data.calendar import generate_trading_calendar
from backend.data.sectors_gics import SECTORS_GICS, COUNTRIES
from backend.ingestion.yf_client import YFinanceClient
from backend.ingestion.loader import ingest_prices, upsert_prices
from backend.api.models import AssetInfo, PriceBar, AssetDetail
from backend.api.router import api_router
```

## Arquivos de Interesse

### Para Desenvolvedores

- **Type Hints**: Ver `backend/api/models.py` (30+ modelos)
- **Endpoints**: Ver `backend/api/` (5 módulos)
- **Banco de Dados**: Ver `backend/db/schema.py` (9 tabelas)
- **Ingestão**: Ver `backend/ingestion/` (3 módulos)
- **CLI**: Ver `backend/cli.py` (7 comandos)

### Para DBA/Analistas

- **Queries SQL**: `backend/sql/useful_queries.sql`
- **Schema DDL**: `backend/db/schema.py`
- **Logging**: `backend/logs/market_platform.log`
- **Checkpoint**: `backend/logs/checkpoint.txt`

### Para DevOps

- **Requirements**: `backend/requirements.txt` (13 pacotes)
- **Configuração**: `.env.example` (variáveis de ambiente)
- **App Entry**: `backend/app.py` (FastAPI app)
- **Health Check**: `GET http://localhost:8000/health`

## Variáveis de Ambiente

Ver arquivo `.env.example` em:
```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/.env.example
```

Principais variáveis:
- `MARKET_DB_URL` — Conexão com banco (PostgreSQL ou SQLite)
- `CORS_ORIGINS` — Origens CORS permitidas
- `API_PREFIX` — Prefixo da API (/api por padrão)
- `DEBUG` — Mode debug (false em produção)

## Documentação Completa

1. **BACKEND_README.md** — Setup, endpoints, CLI, troubleshooting
   ```
   /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/BACKEND_README.md
   ```

2. **ESTRUCTURA_FINAL.txt** — Resumo visual da estrutura
   ```
   /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/ESTRUCTURA_FINAL.txt
   ```

3. **CHECKLIST_VALIDACAO.md** — Validação completa
   ```
   /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/CHECKLIST_VALIDACAO.md
   ```

4. **PATHS_REFERENCE.md** — Este arquivo
   ```
   /sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/PATHS_REFERENCE.md
   ```

## Exemplos de Requisições HTTP

```bash
# Listar ativos
curl http://localhost:8000/api/assets

# Buscar ativo
curl "http://localhost:8000/api/assets/search?q=PETR"

# Detalhes de um ativo
curl http://localhost:8000/api/assets/PETR3.SA

# Preços históricos
curl "http://localhost:8000/api/prices/AAPL/history?period=90d"

# Retornos
curl "http://localhost:8000/api/prices/AAPL/returns?period=90d"

# Últimos preços
curl http://localhost:8000/api/prices

# Resumo de mercado
curl http://localhost:8000/api/market/summary

# Performance por setor
curl "http://localhost:8000/api/market/sectors?period=90d"

# Países
curl http://localhost:8000/api/market/countries

# Fundamentos
curl http://localhost:8000/api/fundamentals/PETR3.SA

# Valuation
curl http://localhost:8000/api/fundamentals/PETR3.SA/valuation

# Status de ingestão
curl http://localhost:8000/api/ingestion/status

# Health check
curl http://localhost:8000/health
```

## Documentação Interativa (Swagger)

```
http://localhost:8000/docs       — Swagger UI (interativo)
http://localhost:8000/redoc      — ReDoc (leitura)
http://localhost:8000/openapi.json — OpenAPI spec
```

## Estrutura de Diretórios Estendida

```
/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/
│
├── backend/                              [Pacote principal]
│   ├── __init__.py
│   ├── app.py                            [FastAPI app principal]
│   ├── cli.py                            [CLI]
│   ├── ingest_resumable.py               [Ingestão com checkpoint]
│   ├── requirements.txt
│   │
│   ├── config/                           [Configurações]
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── logging_config.py
│   │   └── symbols.py
│   │
│   ├── db/                               [Database]
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── schema.py
│   │
│   ├── data/                             [Dados de referência]
│   │   ├── __init__.py
│   │   ├── calendar.py
│   │   └── sectors_gics.py
│   │
│   ├── ingestion/                        [Ingestão de dados]
│   │   ├── __init__.py
│   │   ├── yf_client.py
│   │   ├── loader.py
│   │   └── fundamentals_loader.py
│   │
│   ├── api/                              [API REST]
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── models.py
│   │   ├── assets.py
│   │   ├── prices.py
│   │   ├── market.py
│   │   ├── fundamentals.py
│   │   └── ingestion.py
│   │
│   ├── sql/                              [SQL queries]
│   │   └── useful_queries.sql
│   │
│   └── logs/                             [Logs (runtime)]
│       ├── market_platform.log
│       └── checkpoint.txt
│
├── frontend/                             [Frontend React — outro projeto]
│
├── .env.example                          [Template .env]
├── BACKEND_README.md                     [Documentação]
├── ESTRUCTURA_FINAL.txt                  [Resumo visual]
├── CHECKLIST_VALIDACAO.md                [Validação]
└── PATHS_REFERENCE.md                    [Este arquivo]
```

## Informações de Versão

- **Python**: 3.8+
- **FastAPI**: 0.110.0+
- **SQLAlchemy**: 2.0.0+
- **Pydantic**: 2.6.0+
- **Backend Version**: 1.0.0

## Status Final

✅ Backend FastAPI Unified — COMPLETO E PRONTO PARA USO

All absolute paths reference:
`/sessions/hopeful-determined-heisenberg/mnt/Global_Mkt/market_platform_unified/`

Leia `BACKEND_README.md` para instruções completas de setup e uso.
