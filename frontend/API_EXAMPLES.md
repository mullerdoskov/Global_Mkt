# API Examples - Market Data Platform

## Exemplos de Requisições e Respostas

### 1. Últimos Preços

#### Request
```bash
GET http://localhost:8000/api/prices/latest
```

#### Response
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "last_price": 182.45,
    "price_change_percent": 2.35,
    "asset_type": "stock",
    "country": "USA",
    "sector": "Technology",
    "timestamp": "2026-03-13T15:30:00Z"
  },
  {
    "id": 2,
    "symbol": "MSFT",
    "name": "Microsoft Corporation",
    "last_price": 425.78,
    "price_change_percent": -1.20,
    "asset_type": "stock",
    "country": "USA",
    "sector": "Technology",
    "timestamp": "2026-03-13T15:30:00Z"
  }
]
```

### 2. Preço Específico

#### Request
```bash
GET http://localhost:8000/api/prices/latest?symbol=AAPL
```

#### Response
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "last_price": 182.45,
    "price_change_percent": 2.35,
    "asset_type": "stock",
    "country": "USA",
    "sector": "Technology",
    "timestamp": "2026-03-13T15:30:00Z"
  }
]
```

### 3. Histórico de Preços

#### Request
```bash
GET http://localhost:8000/api/prices/AAPL/history?period=1M
```

Períodos suportados: `1S`, `1M`, `3M`, `6M`, `1A`

#### Response
```json
[
  {
    "date": "2026-02-13",
    "open": 175.20,
    "high": 178.50,
    "low": 174.80,
    "close": 177.30,
    "volume": 52000000,
    "daily_return": 1.20,
    "cumulative_return": 1.20
  },
  {
    "date": "2026-02-14",
    "open": 177.30,
    "high": 180.45,
    "low": 177.10,
    "close": 179.80,
    "volume": 48000000,
    "daily_return": 1.41,
    "cumulative_return": 2.62
  },
  {
    "date": "2026-02-15",
    "open": 179.80,
    "high": 182.50,
    "low": 179.50,
    "close": 181.90,
    "volume": 55000000,
    "daily_return": 1.17,
    "cumulative_return": 3.82
  }
]
```

### 4. Busca de Ativos

#### Request
```bash
GET http://localhost:8000/api/assets/search?q=apple
```

#### Response
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "asset_type": "stock",
    "country": "USA",
    "sector": "Technology"
  },
  {
    "symbol": "AAPL34",
    "name": "Apple ADR Brazil",
    "asset_type": "stock",
    "country": "Brazil",
    "sector": "Technology"
  }
]
```

### 5. Setores

#### Request
```bash
GET http://localhost:8000/api/market/sectors
```

#### Response
```json
[
  {
    "sector": "Technology",
    "country": "USA",
    "avg_performance": 2.35,
    "avg_pe": 28.45,
    "avg_dividend_yield": 1.20,
    "stocks_count": 45
  },
  {
    "sector": "Financials",
    "country": "USA",
    "avg_performance": -0.85,
    "avg_pe": 12.30,
    "avg_dividend_yield": 3.45,
    "stocks_count": 38
  },
  {
    "sector": "Healthcare",
    "country": "USA",
    "avg_performance": 1.50,
    "avg_pe": 24.60,
    "avg_dividend_yield": 0.95,
    "stocks_count": 32
  }
]
```

### 6. Fundamentos

#### Request
```bash
GET http://localhost:8000/api/fundamentals/AAPL
```

#### Response
```json
{
  "symbol": "AAPL",
  "revenue": 394328000000,
  "ebitda": 130541000000,
  "net_income": 99803000000,
  "total_assets": 348515000000,
  "total_liabilities": 138524000000,
  "equity": 209991000000,
  "cash": 24193000000,
  "debt": 108949000000,
  "employees": 164000,
  "last_updated": "2026-02-28"
}
```

### 7. Múltiplos de Valuation

#### Request
```bash
GET http://localhost:8000/api/fundamentals/AAPL/valuation
```

#### Response
```json
{
  "symbol": "AAPL",
  "pe_ratio": 28.45,
  "price_to_book": 48.32,
  "ev_ebitda": 22.15,
  "roe": 95.23,
  "roa": 28.65,
  "dividend_yield": 0.42,
  "payout_ratio": 14.23,
  "debt_to_equity": 0.52,
  "market_cap": 2850000000000,
  "enterprise_value": 2890000000000
}
```

### 8. Status de Ingestão

#### Request
```bash
GET http://localhost:8000/api/ingestion/status
```

#### Response
```json
{
  "total_assets": 587,
  "total_ingested": 12450,
  "successful": 12340,
  "errors": 110,
  "partial": 0,
  "last_execution": "2026-03-13T15:00:00Z",
  "next_execution": "2026-03-13T16:00:00Z"
}
```

### 9. Histórico de Execuções

#### Request
```bash
GET http://localhost:8000/api/ingestion/executions
```

#### Response
```json
[
  {
    "execution_id": "exec_20260313_1500",
    "started_at": "2026-03-13T15:00:00Z",
    "completed_at": "2026-03-13T15:05:23Z",
    "status": "success",
    "assets_processed": 587,
    "assets_successful": 575,
    "assets_failed": 12,
    "duration_seconds": 323
  },
  {
    "execution_id": "exec_20260313_1400",
    "started_at": "2026-03-13T14:00:00Z",
    "completed_at": "2026-03-13T14:05:10Z",
    "status": "success",
    "assets_processed": 587,
    "assets_successful": 580,
    "assets_failed": 7,
    "duration_seconds": 310
  },
  {
    "execution_id": "exec_20260313_1300",
    "started_at": "2026-03-13T13:00:00Z",
    "completed_at": "2026-03-13T13:05:45Z",
    "status": "partial",
    "assets_processed": 587,
    "assets_successful": 565,
    "assets_failed": 22,
    "duration_seconds": 345
  }
]
```

## Códigos de Status HTTP

| Code | Significado | Exemplo |
|------|------------|---------|
| 200 | OK - Sucesso | Dados retornados |
| 400 | Bad Request | Parâmetro inválido |
| 404 | Not Found | Símbolo não existe |
| 500 | Server Error | Erro no backend |

## Headers Importantes

### Request
```
GET /api/prices/latest HTTP/1.1
Host: localhost:8000
Accept: application/json
Origin: http://localhost:8001
```

### Response
```
HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *
Cache-Control: max-age=300
```

## Filtros Disponíveis

### Por tipo de ativo
```bash
GET /api/prices/latest?asset_type=stock
GET /api/prices/latest?asset_type=crypto
GET /api/prices/latest?asset_type=index
```

### Por país
```bash
GET /api/prices/latest?country=USA
GET /api/prices/latest?country=Brazil
```

### Por setor
```bash
GET /api/prices/latest?sector=Technology
GET /api/prices/latest?sector=Financials
```

## Paginação (se implementada)

```bash
GET /api/prices/latest?page=1&limit=50
```

Response inclui:
```json
{
  "data": [...],
  "total": 587,
  "page": 1,
  "limit": 50,
  "pages": 12
}
```

## Exemplos de Curl

### Obter últimos preços
```bash
curl -s http://localhost:8000/api/prices/latest | jq '.[0]'
```

### Obter preço específico com formatação
```bash
curl -s http://localhost:8000/api/prices/latest?symbol=AAPL | jq '.[] | {symbol, price: .last_price, change: .price_change_percent}'
```

### Obter histórico de um mês
```bash
curl -s http://localhost:8000/api/prices/AAPL/history?period=1M | jq '.[] | {date, close}' | head -20
```

### Buscar ativo
```bash
curl -s "http://localhost:8000/api/assets/search?q=apple" | jq '.[] | {symbol, name}'
```

### Obter fundamentos
```bash
curl -s http://localhost:8000/api/fundamentals/AAPL | jq '{revenue, ebitda, net_income}'
```

### Obter status de ingestão
```bash
curl -s http://localhost:8000/api/ingestion/status | jq '.'
```

## Tratamento de Erros

### Exemplo de erro 404
```json
{
  "detail": "Symbol INVALIDSYMBOL not found",
  "status": 404,
  "timestamp": "2026-03-13T15:30:00Z"
}
```

### Exemplo de erro 400
```json
{
  "detail": "Invalid period. Must be: 1S, 1M, 3M, 6M, 1A",
  "status": 400,
  "timestamp": "2026-03-13T15:30:00Z"
}
```

## Rate Limiting

Se implementado:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1647012600
```

## Caching

Recomendações:
- `/api/prices/latest` - Cache 5 min
- `/api/prices/{symbol}/history` - Cache 30 min
- `/api/market/sectors` - Cache 1h
- `/api/fundamentals/*` - Cache 24h
- `/api/ingestion/status` - Cache 1 min

## Testes de Integração

### Python (requests)
```python
import requests

api = "http://localhost:8000/api"

# Obter preços
prices = requests.get(f"{api}/prices/latest").json()
print(f"Obtidos {len(prices)} preços")

# Buscar ativo
result = requests.get(f"{api}/assets/search?q=apple").json()
print(f"Encontrados {len(result)} resultados")

# Histórico
history = requests.get(f"{api}/prices/AAPL/history?period=1M").json()
print(f"Histórico com {len(history)} dias")
```

### JavaScript (fetch)
```javascript
const api = "http://localhost:8000/api";

// Obter preços
fetch(`${api}/prices/latest`)
  .then(r => r.json())
  .then(data => console.log(`${data.length} preços obtidos`));

// Buscar
fetch(`${api}/assets/search?q=apple`)
  .then(r => r.json())
  .then(data => console.log(`${data.length} resultados`));

// Histórico
fetch(`${api}/prices/AAPL/history?period=1M`)
  .then(r => r.json())
  .then(data => console.log(`Histórico: ${data.length} dias`));
```

## Documentação Interativa

Se usar FastAPI com Swagger:
```
http://localhost:8000/docs
```

Se usar ReDoc:
```
http://localhost:8000/redoc
```

---

**Dica:** Use a aba Network do DevTools para inspeccionar todas as requisições feitas pelo frontend!
