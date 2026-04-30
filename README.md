# Market Platform Unified

Plataforma unificada de dados de mercado financeiro — fusão dos projetos **Emergent FinTracker** (design system React) e **Market Data Platform** (backend de ingestão real via yfinance).

## Visão Geral

| Camada | Stack | Descrição |
|--------|-------|-----------|
| **Backend** | FastAPI + SQLAlchemy + yfinance | 12 endpoints REST, ~600 tickers, 9 tabelas SQL |
| **Frontend** | React + Tailwind + Recharts | 4 páginas, dark theme, design system "E1 Tactical Finance" |
| **Banco** | PostgreSQL (prod) / SQLite (dev) | Schema relacional com países, setores GICS, preços OHLCV, fundamentos |
| **Ingestão** | yfinance + pipeline resumível | Rate-limit, backoff exponencial, checkpoint em arquivo |

## Início Rápido

### 1. Configuração

```bash
cd market_platform_unified

# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Editar .env com URL do banco de dados

# Instalar dependências do backend
pip install -r backend/requirements.txt
```

### 2. Setup do banco

```bash
# Com PostgreSQL
python -m backend.cli db-init

# Ou com SQLite (alterar MARKET_DB_URL no .env)
# MARKET_DB_URL=sqlite:///market_db.sqlite
```

### 3. Ingestão de dados

```bash
# Ingestão completa (~600 ativos, demora ~2h com rate-limit)
python -m backend.cli ingest-all

# Ou ingestão resumível (pode parar e retomar)
python -m backend.ingest_resumable

# Ou só preços (mais rápido)
python -m backend.cli ingest-prices

# Atualização incremental (últimos 5 dias)
python -m backend.cli update
```

### 4. Iniciar o backend

```bash
# Desenvolvimento
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# Ou via CLI
python -m backend.app
```

A API fica disponível em `http://localhost:8000/docs` (Swagger UI).

### 5. Abrir o frontend

A partir da ISSUE-007 o backend serve o SPA estático. Abrir
`http://localhost:8000/` no navegador — o `frontend/index.html` é entregue
pelo FastAPI via `StaticFiles`, mesmo origin que a API. (O acesso via
`file://` deixou de ser suportado: a entrada `"null"` no `CORS_ORIGINS` foi
removida.)

## Endpoints da API

| # | Método | Path | Descrição |
|---|--------|------|-----------|
| 1 | GET | `/api/assets` | Lista ativos com filtros e paginação |
| 2 | GET | `/api/assets/search?q=` | Busca por símbolo ou nome |
| 3 | GET | `/api/assets/{symbol}` | Detalhes de um ativo + último preço |
| 4 | GET | `/api/prices/{symbol}/history` | Série histórica OHLCV |
| 5 | GET | `/api/prices/{symbol}/returns` | Retorno diário + acumulado |
| 6 | GET | `/api/prices/latest` | Snapshot: último preço de todos os ativos |
| 7 | GET | `/api/market/summary` | Resumo dos 16 índices globais |
| 8 | GET | `/api/market/sectors` | Performance por setor GICS |
| 9 | GET | `/api/market/countries` | Países com contagem de ativos |
| 10 | GET | `/api/fundamentals/{symbol}` | DRE, balanço, FCF (4 trimestres) |
| 11 | GET | `/api/fundamentals/{symbol}/valuation` | Múltiplos: P/L, P/VP, EV/EBITDA, ROE |
| 12 | GET | `/api/ingestion/status` | Status e log da ingestão |

## Estrutura do Projeto

```
market_platform_unified/
├── .env.example                     # Template de variáveis
├── README.md                        # Este arquivo
├── backend/
│   ├── app.py                       # FastAPI principal
│   ├── cli.py                       # CLI (db-init, ingest, update, status)
│   ├── ingest_resumable.py          # Pipeline resumível com checkpoint
│   ├── requirements.txt
│   ├── api/
│   │   ├── router.py                # Agregador de routers
│   │   ├── models.py                # Modelos Pydantic (request/response)
│   │   ├── assets.py                # Endpoints de ativos
│   │   ├── prices.py                # Endpoints de preços
│   │   ├── market.py                # Endpoints de mercado
│   │   ├── fundamentals.py          # Endpoints de fundamentos
│   │   └── ingestion.py             # Endpoint de status de ingestão
│   ├── config/
│   │   ├── settings.py              # Pydantic-settings centralizado
│   │   ├── logging_config.py        # Logging rotativo 10MB
│   │   └── symbols.py               # ~600 tickers (BR, US, UK, DE, FR, NL, CH)
│   ├── db/
│   │   ├── connection.py            # Engine SQLAlchemy (PostgreSQL + SQLite)
│   │   └── schema.py                # 9 tabelas ORM com índices
│   ├── data/
│   │   ├── calendar.py              # Calendário de dias úteis
│   │   └── sectors_gics.py          # 34 setores GICS + 12 países
│   ├── ingestion/
│   │   ├── yf_client.py             # Cliente yfinance (rate-limit, backoff)
│   │   ├── loader.py                # Pipeline de ingestão de preços
│   │   └── fundamentals_loader.py   # Ingestão de DRE, balanço, FCF, valuations
│   └── sql/
│       └── useful_queries.sql       # 11 queries analíticas prontas
└── frontend/
    └── index.html                   # App React standalone (4 páginas)
```

## Cobertura de Ativos (~600 tickers)

| Tipo | Quantidade | Exemplos |
|------|-----------|----------|
| Ações BR | ~80 | PETR4.SA, VALE3.SA, ITUB4.SA |
| Ações US | ~120 | AAPL, MSFT, NVDA, JPM |
| Ações UK | ~30 | SHEL.L, AZN.L, HSBA.L |
| Ações DE | ~21 | SAP.DE, SIE.DE, ALV.DE |
| Ações FR | ~20 | MC.PA, TTE.PA, AIR.PA |
| Ações NL/CH | ~20 | ASML.AS, NESN.SW |
| Índices | 16 | ^GSPC, ^BVSP, ^GDAXI, ^FTSE |
| Commodities | 15 | GC=F, CL=F, BZ=F, ZS=F |
| FX | 16 | USDBRL=X, EURUSD=X, DX-Y.NYB |
| Cripto | 10 | BTC-USD, ETH-USD, SOL-USD |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MARKET_DB_URL` | `postgresql+psycopg2://...` | URL do banco de dados |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Origens CORS |
| `API_PREFIX` | `/api` | Prefixo da API |
| `HOST` | `0.0.0.0` | Host do servidor |
| `PORT` | `8000` | Porta do servidor |
| `DEBUG` | `false` | Modo debug |

## Comandos CLI

```bash
python -m backend.cli db-init              # Cria tabelas + popula dados base
python -m backend.cli ingest-prices        # Ingestão de preços OHLCV (90 dias)
python -m backend.cli ingest-fundamentals  # DRE, balanço, FCF, valuations
python -m backend.cli ingest-all           # Preços + fundamentos
python -m backend.cli update               # Atualização incremental (5 dias)
python -m backend.cli status               # Contagem de registros
python -m backend.cli test-db              # Testa conexão com o banco
```

## Licença

Projeto interno — Inteligência de Mercado.
