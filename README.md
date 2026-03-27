# Market Platform Unified v2.0

Plataforma de dados de mercado financeiro para Inteligência de Mercado.
Backend FastAPI + PostgreSQL + yfinance com CLI versátil.

## Quick Start

```cmd
git clone https://github.com/SEU_USER/Global_Mkt.git
cd Global_Mkt

:: Setup completo (cria venv, instala deps, inicializa banco)
market.bat setup

:: Iniciar API
market.bat server

:: Ou use o menu interativo
market.bat
```

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + SQLAlchemy + Pydantic v2 |
| Banco | PostgreSQL 17 |
| Ingestão | yfinance (batch download, rate-limit, backoff) |
| Frontend | React 18 standalone (em desenvolvimento) |

## CLI

```cmd
:: ── Banco ──
python -m backend.cli db-init
python -m backend.cli db-status
python -m backend.cli db-reset

:: ── Ingestão com filtros ──
python -m backend.cli ingest-prices --type stock --country BR --start 2025-01-01 --end 2025-12-31
python -m backend.cli ingest-prices --type index --period 6mo
python -m backend.cli ingest-prices --symbols "PETR4.SA,VALE3.SA,AAPL" --period 1y
python -m backend.cli ingest-fundamentals --country BR

:: ── Consultas ──
python -m backend.cli list-assets --type etf --country US
python -m backend.cli search petrobras
python -m backend.cli show PETR4.SA
python -m backend.cli prices AAPL --period 30d
python -m backend.cli top-movers --country BR --limit 10

:: ── Gerenciamento ──
python -m backend.cli add-asset TICKER.SA "Nome" stock BR
python -m backend.cli remove-asset TICKER.SA
python -m backend.cli delete-prices PETR4.SA --start 2024-01-01

:: ── Exportação ──
python -m backend.cli export prices --country BR -o precos_br.csv
python -m backend.cli export assets --type stock -o ativos.csv
```

## API REST

Swagger UI: `http://localhost:8000/docs`

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/assets` | Lista assets (paginação + filtros) |
| `GET /api/assets/search?q=` | Busca por símbolo/nome |
| `GET /api/assets/{symbol}` | Detalhe + último preço |
| `GET /api/prices` | Último preço de cada asset |
| `GET /api/prices/{sym}/history` | Histórico OHLCV |
| `GET /api/prices/{sym}/returns` | Retornos diários + acumulado |
| `GET /api/market/summary` | Resumo (índices) |
| `GET /api/market/sectors` | Performance por setor GICS |
| `GET /api/market/countries` | Países + contagem |
| `GET /api/fundamentals/{sym}` | Demonstrativos financeiros |
| `GET /api/fundamentals/{sym}/valuation` | Múltiplos (P/E, EV/EBITDA, etc) |
| `GET /api/ingestion/status` | Status do pipeline |

## Cobertura

371 tickers: 250 stocks (BR, US, EU, Ásia, Latam), 41 ETFs, 20 índices, 20 commodities, 20 pares FX, 20 cryptos.
22 países, 27 setores GICS.

## Requisitos

- Python 3.10+
- PostgreSQL 17 (com banco `market_db` criado)

## Licença

Uso interno — Inteligência de Mercado.
