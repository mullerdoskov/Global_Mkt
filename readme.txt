# Relatório de Contexto — Market Platform Unified

Data: 2026-03-14
Autor: Lucas (Inteligência de Mercado) + Claude
Status: **EM DESENVOLVIMENTO — backend funcional com bug pendente no endpoint de preços**

---

## 1. O que é este projeto

Fusão de dois projetos anteriores numa plataforma única de dados de mercado financeiro:

- **Emergent FinTracker**: tinha um design system completo (dark theme, React/Tailwind/shadcn/Recharts) mas backend com dados 100% mock e frontend sem código-fonte (só configs)
- **market_platform**: backend robusto com ingestão real via yfinance, ~600 tickers, 9 tabelas PostgreSQL, pipeline resumível — mas UI era Streamlit básico

O objetivo foi pegar a lógica de negócio real do market_platform e servir via FastAPI + frontend React moderno seguindo o design system do Emergent.

---

## 2. Stack definida

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + SQLAlchemy + yfinance |
| Banco | PostgreSQL 17 (produção) / SQLite (dev) |
| Frontend | React 18 (standalone HTML via CDN) + Tailwind + SVG charts |
| Ingestão | yfinance com rate-limit, backoff, pipeline resumível |

---

## 3. Estrutura de pastas

```
C:\Users\lucas\Documents\Global_Mkt\market_platform_unified\
├── .env                          # PostgreSQL ativo
├── .env.example
├── README.md                     # Documentação principal em PT-BR
├── RELATORIO_CONTEXTO.md         # ESTE ARQUIVO
├── backend/
│   ├── app.py                    # FastAPI principal (lifespan, CORS, error handlers)
│   ├── cli.py                    # CLI: db-init, ingest-prices, ingest-all, update, status
│   ├── ingest_resumable.py       # Pipeline resumível com checkpoint
│   ├── requirements.txt
│   ├── api/
│   │   ├── router.py             # Agregador de 5 sub-routers
│   │   ├── models.py             # ~30 modelos Pydantic (request/response)
│   │   ├── assets.py             # GET /api/assets, /api/assets/search, /api/assets/{symbol}
│   │   ├── prices.py             # GET /api/prices, /api/prices/{sym}/history, /returns ⚠️ BUG
│   │   ├── market.py             # GET /api/market/summary, /sectors, /countries
│   │   ├── fundamentals.py       # GET /api/fundamentals/{sym}, /{sym}/valuation
│   │   └── ingestion.py          # GET /api/ingestion/status
│   ├── config/
│   │   ├── settings.py           # Pydantic-settings (MARKET_DB_URL, CORS, etc)
│   │   ├── logging_config.py     # Logging rotativo 10MB
│   │   └── symbols.py            # ~600 tickers organizados por tipo e país
│   ├── db/
│   │   ├── connection.py         # Engine SQLAlchemy (pool_size=5, max_overflow=10)
│   │   └── schema.py             # 9 tabelas ORM: countries, sectors_gics, companies, assets,
│   │                             #   trading_calendar, prices_daily, financial_statements,
│   │                             #   valuation_multiples, ingestion_log
│   ├── data/
│   │   ├── calendar.py           # Calendário de dias úteis
│   │   └── sectors_gics.py       # 34 setores GICS + 12 países + mapa ticker→setor
│   ├── ingestion/
│   │   ├── yf_client.py          # Cliente yfinance (rate-limit, backoff exponencial, User-Agent rotation)
│   │   ├── loader.py             # Pipeline de ingestão de preços (upsert)
│   │   └── fundamentals_loader.py # Ingestão de DRE, balanço, FCF, valuations
│   └── sql/
│       └── useful_queries.sql    # 11 queries analíticas prontas
└── frontend/
    └── index.html                # App React standalone (~700 linhas, 4 páginas)
```

---

## 4. Banco de dados (PostgreSQL — market_db)

### Dados atuais confirmados:
- **360 assets** na tabela `assets`
- **30.043 registros** na tabela `prices_daily`
- Tabelas criadas: 9 (todas verificadas no startup)

### Schema principal (enums):
- `AssetType`: stock, index, commodity, fx, crypto, etf
- `PeriodType`: quarterly, annual
- `IngestionStatus`: success, error, partial

### Conexão:
```
MARKET_DB_URL=postgresql+psycopg2://postgres:141592@localhost:5432/market_db
```

---

## 5. API REST — Endpoints implementados

| # | Método | Path | Response Model | Status |
|---|--------|------|---------------|--------|
| 1 | GET | `/api/assets` | `AssetListResponse {total, page, page_size, assets[]}` | ✅ OK |
| 2 | GET | `/api/assets/search?q=` | `AssetListResponse {assets[]}` | ✅ OK |
| 3 | GET | `/api/assets/{symbol}` | `AssetDetail {symbol, name, asset_type, company, latest_price}` | ✅ OK |
| 4 | GET | `/api/prices` | `LatestPricesResponse {as_of, count, prices[]}` | ⚠️ **BUG** |
| 5 | GET | `/api/prices/{symbol}/history?period=90d` | `PriceHistoryResponse {symbol, period, interval, count, prices[]}` | ✅ OK |
| 6 | GET | `/api/prices/{symbol}/returns?period=90d` | `ReturnsResponse {symbol, period, count, returns[]}` | ✅ OK |
| 7 | GET | `/api/prices/debug` | JSON livre (contagens + amostra) | ✅ Debug |
| 8 | GET | `/api/market/summary` | `MarketSummaryResponse {as_of, indices[]}` | ✅ OK |
| 9 | GET | `/api/market/sectors` | `SectorsResponse {period, as_of, sectors[]}` | ✅ OK |
| 10 | GET | `/api/market/countries` | `CountriesResponse {total_countries, countries[]}` | ✅ OK |
| 11 | GET | `/api/fundamentals/{symbol}` | `FinancialsResponse {symbol, company_name, quarters[]}` | ✅ OK |
| 12 | GET | `/api/fundamentals/{symbol}/valuation` | `ValuationResponse {symbol, company_name, multiples{}}` | ✅ OK |
| 13 | GET | `/api/ingestion/status` | `IngestionStatusResponse {total_assets, success_count, error_count, recent_logs[]}` | ✅ OK |

---

## 6. BUG PENDENTE — GET /api/prices

### Sintoma:
`http://localhost:8000/api/prices` retorna **Internal Server Error** (500).

### Causa provável:
A query SQL com subquery correlacionada `WHERE p.date = (SELECT MAX(p2.date) ...)` pode estar falhando por:
1. **Enum cast**: `a.asset_type` é um enum PostgreSQL — resolvido com `::text` na query
2. **Performance**: subquery correlacionada em 360 assets × 30k preços pode ser lenta
3. **Exception handler do app.py** (linhas 99-118) intercepta o erro antes do endpoint e retorna `HTTPException` genérico

### Diagnóstico pendente:
1. Acessar `http://localhost:8000/api/prices/debug` para confirmar que a conexão funciona
2. Checar o terminal do uvicorn para ver o traceback completo (o `raise` no except agora propaga o erro)
3. Se a query é o problema, alternativa: usar `DISTINCT ON` do PostgreSQL:
```sql
SELECT DISTINCT ON (a.id) a.symbol, a.name, a.asset_type::text, p.close, p.date
FROM assets a
JOIN prices_daily p ON p.asset_id = a.id
ORDER BY a.id, p.date DESC
```

### Possível fix no exception handler:
O `general_exception_handler` em `app.py` (linha 109) retorna um `HTTPException` mas isso causa loop — deveria retornar `JSONResponse`:
```python
from starlette.responses import JSONResponse

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Erro não tratado: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

---

## 7. Frontend — Estado atual

### Funciona:
- Layout: sidebar (MARKET DATA) + topbar (Inteligência de Mercado) + conteúdo
- 4 rotas via hash: `#/`, `#/symbol/{sym}`, `#/sectors`, `#/ingestion`
- Busca de ativos (`/api/assets/search`)
- Gráfico de barras de Setores (`/api/market/sectors`) ✅ confirmado visualmente
- Filtros por tipo de ativo (stock, index, commodity, fx, crypto)
- Design: dark theme (#09090B), verde/vermelho, fontes Chivo/Manrope/JetBrains Mono

### Não funciona (depende do bug acima):
- Cards de preços no Dashboard (consome `GET /api/prices`)
- Detalhe do símbolo: gráfico histórico + OHLCV + fundamentos + múltiplos

### Mapeamento Frontend → API (já corrigido):
| Frontend chama | Endpoint real | Extração |
|---|---|---|
| `/prices` | `GET /api/prices` | `response.prices[]` |
| `/assets/search?q=` | `GET /api/assets/search?q=` | `response.assets[]` |
| `/prices/{sym}/history?period=90d` | `GET /api/prices/{sym}/history?period=90d` | `response.prices[]` |
| `/market/sectors` | `GET /api/market/sectors` | `response.sectors[]` (campo: `avg_return_pct` → mapeado para `avg_performance`) |
| `/fundamentals/{sym}` | `GET /api/fundamentals/{sym}` | `response.quarters[0]` |
| `/fundamentals/{sym}/valuation` | `GET /api/fundamentals/{sym}/valuation` | `response.multiples` |
| `/ingestion/status` | `GET /api/ingestion/status` | `response.success_count`, `error_count`, `recent_logs[]` |

### Conversão de períodos no frontend:
```javascript
const periodMap = { '1S': '7d', '1M': '30d', '3M': '90d', '6M': '180d', '1A': '365d' };
```

### CORS:
O `.env` tem `CORS_ORIGINS=http://localhost:3000,http://localhost:5173`. O `app.py` adiciona `"null"` para suportar `file://`. Se o frontend for servido via HTTP (`python -m http.server 3000`), funciona sem problemas.

---

## 8. Arquivos preservados intactos do market_platform original

Estes arquivos foram copiados SEM alteração (verificado via `diff`):
- `db/schema.py` — 9 tabelas ORM
- `db/connection.py` — Engine SQLAlchemy
- `config/symbols.py` — ~600 tickers
- `config/logging_config.py`
- `config/settings.py`
- `data/calendar.py`
- `data/sectors_gics.py`
- `ingestion/yf_client.py` — cliente yfinance
- `sql/useful_queries.sql`

**Imports corrigidos** (de `from db.` para `from backend.db.`):
- `ingestion/loader.py`
- `ingestion/fundamentals_loader.py`
- `ingest_resumable.py`

---

## 9. Como rodar (Windows)

```cmd
cd C:\Users\lucas\Documents\Global_Mkt\market_platform_unified

# Backend
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000

# Frontend (opção 1: abrir direto)
start frontend\index.html

# Frontend (opção 2: servir via HTTP — evita problemas de CORS)
cd frontend && python -m http.server 3000

# Ingestão
python -m backend.cli db-init
python -m backend.cli ingest-prices
python -m backend.cli ingest-fundamentals

# Pipeline resumível
python -m backend.ingest_resumable
```

Swagger UI: `http://localhost:8000/docs`

---

## 10. Próximos passos prioritários

1. **RESOLVER o bug do GET /api/prices** — acessar `/api/prices/debug` e checar traceback no uvicorn
2. **Testar todas as 4 páginas** com dados reais
3. **Adicionar change_pct** ao endpoint de preços (calcular variação diária)
4. **Considerar servir frontend via FastAPI** (StaticFiles) para evitar problemas de CORS com `file://`
5. **Adicionar paginação** ao endpoint de preços (360 ativos de uma vez pode ser pesado)
6. **Opcional**: migrar frontend standalone para projeto Vite/React real

---

## 11. Dependências Python (requirements.txt)

```
fastapi>=0.100.0
uvicorn>=0.25.0
sqlalchemy>=2.0
psycopg2-binary>=2.9
yfinance>=0.2.40
pandas>=2.0
numpy>=1.24
python-dotenv>=1.0
pydantic-settings>=2.0
beautifulsoup4>=4.12
requests>=2.31.0
colorama>=0.4
six>=1.5
```