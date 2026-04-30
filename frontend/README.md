# Market Data Platform - Frontend

Frontend React standalone para a plataforma unificada de dados de mercado financeiro.

## Arquivo Principal

**`index.html`** - Arquivo HTML completo e autossuficiente (49KB)

## Características

### Páginas Implementadas

1. **Dashboard** (`#/`)
   - Indicadores dos índices principais (S&P 500, Ibovespa, DAX, FTSE)
   - Grade de últimos preços dos ativos
   - Busca rápida de símbolos
   - Filtros por tipo de ativo (stock, index, commodity, fx, crypto)
   - Gráfico de performance por setor

2. **Detalhe do Símbolo** (`#/symbol/:symbol`)
   - Informações do ativo (preço, variação, país, tipo)
   - Gráfico de preço histórico com seletor de período (1S, 1M, 3M, 6M, 1A)
   - Gráfico de retorno diário e acumulado
   - Tabela OHLCV
   - Fundamentos (receita, EBITDA, lucro líquido)
   - Múltiplos de valuation (P/L, P/VP, EV/EBITDA, ROE, Dividend Yield)

3. **Setores GICS** (`#/sectors`)
   - Tabela com todos os setores e múltiplos médios
   - Filtro por país
   - Gráfico de performance por setor

4. **Status da Ingestão** (`#/ingestion`)
   - Resumo de ativos e preços ingeridos
   - Barra de progresso da taxa de sucesso
   - Tabela de últimas execuções com status

### Design System

Implementa fielmente o design system "emergent":

- **Tema**: Dark (background: #09090B, foreground: #FAFAFA)
- **Cores**:
  - Primary/Accent: #22C55E (verde)
  - Destructive: #EF4444 (vermelho)
  - Card: #18181B com borda #27272A
  - Muted: #A1A1AA
- **Tipografia**:
  - Headings: Chivo
  - Body: Manrope
  - Dados numéricos: JetBrains Mono
- **Componentes**:
  - Recharts para gráficos com tema dark
  - lucide-react para ícones
  - Layout responsivo (Sidebar + Topbar + Main Content)

### Stack Tecnológico

- React 18+ (via CDN)
- TailwindCSS
- Recharts
- lucide-react
- Fetch API para consumo de API

## Como Usar

### Ambiente Local (com Backend FastAPI)

1. Abra o arquivo `index.html` em um navegador:
   ```bash
   open index.html
   ```

2. O frontend detectará automaticamente se está rodando em localhost:
   - Local: `http://localhost:8000/api`
   - Produção: `/api` (mesmo domínio)

3. Certifique-se que o backend FastAPI está rodando em `http://localhost:8000`

### Endpoints Consumidos

O frontend faz requisições para os seguintes endpoints:

- `GET /api/prices/latest` - Últimos preços dos ativos
- `GET /api/prices/latest?symbol={symbol}` - Preço específico
- `GET /api/prices/{symbol}/history?period={period}` - Histórico de preços
- `GET /api/assets/search?q={query}` - Busca de ativos
- `GET /api/market/sectors` - Dados de setores
- `GET /api/fundamentals/{symbol}` - Dados fundamentalistas
- `GET /api/fundamentals/{symbol}/valuation` - Múltiplos de valuation
- `GET /api/ingestion/status` - Status da ingestão
- `GET /api/ingestion/executions` - Histórico de execuções

## Componentes Reutilizáveis

### `PriceChange`
Exibe variação percentual com cor (verde ou vermelho) e ícone opcional.

```jsx
<PriceChange value={2.5} showIcon={true} />
```

### `FormattedValue`
Formata números com locale pt-BR e casas decimais customizáveis.

```jsx
<FormattedValue value={1234.56} decimals={2} prefix="R$" suffix="M" />
```

### `Card`
Container com estilo do design system.

```jsx
<Card onClick={() => {}}>
    Conteúdo
</Card>
```

### `DataTable`
Tabela responsiva com loading e empty state.

```jsx
<DataTable
    columns={[{ key: 'symbol', label: 'Símbolo' }]}
    data={prices}
    loading={false}
/>
```

### `LoadingSpinner`
Spinner de carregamento.

### `EmptyState`
Mensagem quando não há dados.

## Responsividade

Layout totalmente responsivo:
- **Mobile**: Stack vertical, sidebar drawer
- **Tablet**: Grid 2 colunas
- **Desktop**: Grid 3-4 colunas, sidebar fixo

## Navegação

Usa hash routing (`window.location.hash`):
- `#/` - Dashboard
- `#/symbol/AAPL` - Detalhe do símbolo AAPL
- `#/sectors` - Página de setores
- `#/ingestion` - Status da ingestão

## Performance

- Arquivo único sem transpilação necessária
- Carregamento via CDN de dependências
- Lazy loading de dados com fetch
- Loading states para melhor UX

## Customização

Para modificar cores, edite a seção `tailwind.config` no `<head>`:

```javascript
colors: {
    primary: '#22C55E',
    destructive: '#EF4444',
    // ... outras cores
}
```

## Limitações

- Não é uma SPA completa (sem build step)
- Requer browser moderno com suporte a ES6+
- CORS deve estar configurado no backend se estiver em domínio diferente

## Próximos Passos

Para transformar em produção:

1. Migrar para Vite ou Create React App
2. Adicionar TypeScript
3. Implementar autenticação JWT
4. Adicionar cache com service workers
5. Otimizar bundle com code splitting
6. Adicionar testes unitários e E2E
