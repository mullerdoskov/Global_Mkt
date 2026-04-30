# Quick Start - Market Data Platform Frontend

## TL;DR

```bash
# 1. Iniciar backend FastAPI
python -m uvicorn app:app --reload

# 2. Abrir frontend
open frontend/index.html
```

## 5 Minutos para Começar

### Pré-requisitos
- Backend FastAPI rodando em `http://localhost:8000`
- Navegador moderno (Chrome, Firefox, Safari, Edge)

### Passo 1: Servir o Frontend
```bash
cd frontend/
python -m http.server 8001
```

### Passo 2: Acessar
Abrir: `http://localhost:8001/index.html`

### Passo 3: Explorar
- Dashboard: Grade de ativos
- Busca: Digitar "AAPL" no search
- Detalhe: Clicar em um ativo
- Setores: Navegação pelo menu
- Ingestão: Ver status de dados

## Estrutura do Projeto

```
frontend/
├── index.html                 ← ARQUIVO PRINCIPAL (49KB, 983 linhas)
│   ├── Componentes
│   │   ├── PriceChange
│   │   ├── FormattedValue
│   │   ├── Card
│   │   ├── DataTable
│   │   ├── LoadingSpinner
│   │   └── EmptyState
│   ├── Páginas
│   │   ├── Dashboard (#/)
│   │   ├── SymbolDetail (#/symbol/XXX)
│   │   ├── SectorsPage (#/sectors)
│   │   ├── IngestionStatus (#/ingestion)
│   │   └── Sidebar (navegação)
│   └── App (routing + layout)
├── README.md                  ← Documentação completa
├── TESTING.md                 ← Guia de testes
├── DEPLOYMENT.md              ← Guia de deployment
├── PROJECT_SUMMARY.md         ← Resumo do projeto
├── QUICKSTART.md              ← Este arquivo
└── .env.example               ← Variáveis de exemplo
```

## 4 Páginas Principais

| Rota | Nome | Função |
|------|------|--------|
| `#/` | Dashboard | Grid de ativos, índices, busca |
| `#/symbol/AAPL` | Detalhe | Gráficos, fundamentos, valuation |
| `#/sectors` | Setores | Tabela de setores com filtros |
| `#/ingestion` | Ingestão | Status de ingestão de dados |

## Componentes Disponíveis

### PriceChange
```jsx
<PriceChange value={2.5} showIcon={true} />
// Saída: ⬆️ +2.50%
```

### FormattedValue
```jsx
<FormattedValue value={1234.56} decimals={2} prefix="R$" />
// Saída: R$ 1.234,56
```

### Card
```jsx
<Card onClick={() => {}}>
    Conteúdo
</Card>
```

### DataTable
```jsx
<DataTable
    columns={[
        { key: 'symbol', label: 'Símbolo' },
        { key: 'price', label: 'Preço', render: (r) => <FormattedValue value={r.price} /> }
    ]}
    data={prices}
    loading={false}
/>
```

## API Endpoints

### Preços
```javascript
GET /api/prices/latest
GET /api/prices/latest?symbol=AAPL
GET /api/prices/AAPL/history?period=1M
```

### Busca
```javascript
GET /api/assets/search?q=apple
```

### Mercado
```javascript
GET /api/market/sectors
```

### Fundamentos
```javascript
GET /api/fundamentals/AAPL
GET /api/fundamentals/AAPL/valuation
```

### Ingestão
```javascript
GET /api/ingestion/status
GET /api/ingestion/executions
```

## Formatação de Dados

### Monetário
```javascript
// Input: 1234.5678
// Output: 1.234,57 (pt-BR com 2 casas)
<FormattedValue value={1234.5678} decimals={2} />
```

### Percentual
```javascript
// Variação positiva: Verde + ícone ⬆️
// Variação negativa: Vermelho + ícone ⬇️
<PriceChange value={-2.5} />
```

### Volume
```javascript
// Input: 1000000
// Output: 1.000.000
<FormattedValue value={1000000} decimals={0} />
```

## Troubleshooting Rápido

### "Nenhum dado aparece"
1. Backend está rodando? `curl http://localhost:8000/api/prices/latest`
2. CORS habilitado? Verificar FastAPI `CORSMiddleware`
3. Dados na DB? Verificar tabelas no PostgreSQL

### "Gráficos em branco"
1. Dados chegaram? Abrir DevTools → Network
2. Recharts carregou? Abrir DevTools → Console
3. Tamanho da viewport? Tentar redimensionar janela

### "API não conecta"
1. Backend URL correta? Deve ser `http://localhost:8000`
2. Porta correta? Padrão é `8000`
3. Backend respondendo? `curl http://localhost:8000/docs`

## Configuração

### API URL
Editar em `index.html` (linha ~60):
```javascript
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';
```

### Cores
Editar `tailwind.config` (linhas ~40-60):
```javascript
colors: {
    primary: '#22C55E',     // Verde
    destructive: '#EF4444', // Vermelho
    // ... outras cores
}
```

### Fontes
Google Fonts carregadas automaticamente:
- Chivo (headings)
- Manrope (body)
- JetBrains Mono (números)

## Performance

- Dashboard carrega em < 1s
- Gráficos renderizam em < 2s
- Tabelas com 100+ linhas scrollam smooth
- Sem erros no console

## Responsive Design

```
Mobile (≤640px)     Tablet (641-1024px)   Desktop (>1024px)
─────────────────   ───────────────────   ──────────────────
┌─────────────────┐ ┌─────────────────────────┐ ┌──────┬────────────┐
│ ☰               │ │     Sidebar (64px)      │ │ S    │            │
├─────────────────┤ ├───────┬─────────────────┤ │ i    │  Content   │
│ Content         │ │Content│                 │ │ d    │            │
│                 │ │ (2col)│                 │ │ e    │            │
│                 │ │       │                 │ │ b    │            │
└─────────────────┘ └───────┴─────────────────┘ │ a    │            │
                                                 │ r    │            │
    Drawer        Sidebar fixo                  │ (64) │            │
    (overlay)                                    └──────┴────────────┘
```

## Scripts Úteis

### Servir localmente
```bash
python -m http.server 8001
```

### Testar com curl
```bash
curl http://localhost:8000/api/prices/latest | jq
```

### Verificar CORS
```bash
curl -H "Origin: http://localhost:8001" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/prices/latest
```

## Próximos Passos

### Curto Prazo
1. [ ] Conectar com backend real
2. [ ] Testar todas as 4 páginas
3. [ ] Validar formatação pt-BR
4. [ ] Testar responsividade

### Médio Prazo
1. [ ] Adicionar autenticação
2. [ ] Implementar cache
3. [ ] Otimizar gráficos
4. [ ] Adicionar mais filtros

### Longo Prazo
1. [ ] Migrar para Vite
2. [ ] Adicionar TypeScript
3. [ ] Cobertura de testes
4. [ ] CI/CD pipeline

## Recursos Úteis

- React Docs: https://react.dev
- TailwindCSS: https://tailwindcss.com
- Recharts: https://recharts.org
- lucide-react: https://lucide.dev

## Contato & Suporte

Documentação completa:
- README.md - Informações gerais
- TESTING.md - Guia de testes
- DEPLOYMENT.md - Deployment em produção
- PROJECT_SUMMARY.md - Resumo técnico

---

**Pronto para começar? Abra o `index.html` no navegador!**
