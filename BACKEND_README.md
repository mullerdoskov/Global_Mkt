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
│   └── ingestion.py          # GET /api/ingestion (novo)
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

```bash
# Cria tabelas
python -m backend.cli db-init

# Testa conexão
python -m backend.cli db-test
```

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
- `db/connection.py` — engine SQLAlchemy
- `db/schema.py` — 9 tabelas ORM
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
