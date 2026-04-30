# Guia de Testes - Market Data Platform Frontend

## Testes Manuais

### 1. Dashboard

**Teste 1.1: Carregamento inicial**
- [ ] Abrir `index.html` no navegador
- [ ] Verificar se índices principais carregam (S&P 500, Ibovespa, DAX, FTSE)
- [ ] Verificar se últimos preços aparecem em grid
- [ ] Verificar se gráfico de setores carrega

**Teste 1.2: Busca rápida**
- [ ] Digitar "AAPL" no campo de busca
- [ ] Verificar se aparecem resultados
- [ ] Clicar em resultado e navegar para detalhe

**Teste 1.3: Filtro por tipo**
- [ ] Clicar em "Stock"
- [ ] Verificar se apenas stocks aparecem
- [ ] Clicar em "Crypto"
- [ ] Verificar se apenas criptos aparecem
- [ ] Clicar em "Todos"

### 2. Detalhe do Símbolo

**Teste 2.1: Navegação**
- [ ] Clique em um ativo do dashboard
- [ ] Url deve conter `#/symbol/SIMBOLO`
- [ ] Header deve mostrar símbolo, nome, preço

**Teste 2.2: Seletor de período**
- [ ] Clicar em "1S" (1 semana)
- [ ] Gráfico deve atualizar
- [ ] Clicar em "1A" (1 ano)
- [ ] Tabela OHLCV deve atualizar

**Teste 2.3: Gráficos**
- [ ] Hover sobre gráfico de preço
- [ ] Tooltip deve aparecer com data e preço
- [ ] Gráfico de retorno deve mostrar barras (diário) e linha (acumulado)

**Teste 2.4: Dados fundamentalistas**
- [ ] Scroll para fundamentos
- [ ] Deve aparecer: Receita, EBITDA, Lucro Líquido
- [ ] Deve aparecer: P/L, P/VP, EV/EBITDA, ROE, Dividend Yield

### 3. Setores

**Teste 3.1: Listagem**
- [ ] Navegar para `#/sectors`
- [ ] Tabela de setores deve aparecer
- [ ] Colunas: Setor, País, Performance, P/L Médio, Dividend Yield

**Teste 3.2: Filtro por país**
- [ ] Clicar em "Todos os países"
- [ ] Clicar em um país específico
- [ ] Tabela deve filtrar

**Teste 3.3: Gráfico**
- [ ] Scroll até gráfico de barras
- [ ] Deve mostrar performance média por setor

### 4. Status da Ingestão

**Teste 4.1: Sumário**
- [ ] Navegar para `#/ingestion`
- [ ] Deve mostrar cards: Total de Ativos, Preços Ingeridos, Sucessos, Erros
- [ ] Barra de progresso deve indicar taxa de sucesso

**Teste 4.2: Histórico**
- [ ] Scroll até tabela de execuções
- [ ] Deve listar últimas execuções com status (success/error/partial)
- [ ] Datas devem estar formatadas em pt-BR

## Responsividade

### Mobile (320px - 640px)
- [ ] Menu hamburger apareça
- [ ] Clicar abre sidebar como drawer
- [ ] Sidebar fecha ao navegar
- [ ] Cards em single column
- [ ] Gráficos adaptam altura

### Tablet (641px - 1024px)
- [ ] Sidebar fixo
- [ ] Grid 2 colunas
- [ ] Índices em 2x2 grid

### Desktop (1025px+)
- [ ] Sidebar fixo
- [ ] Grid 3-4 colunas
- [ ] Índices em 1x4 grid

## Testes de Carregamento

**Teste de Loading States**
- [ ] Dashboard: Aguardar carregamento de preços
- [ ] Detalhe: Trocar período e observar loading
- [ ] Setores: Esperar carregamento da tabela

**Teste de Empty State**
- [ ] Buscar por símbolo inexistente
- [ ] Deverá mostrar mensagem "Nenhum dado"

## Testes de Formatação

**Números**
- [ ] Valores monetários devem ter 2 casas decimais
- [ ] Volumes devem ter 0 casas decimais
- [ ] Separador de milhares (. ou ,) deve seguir pt-BR
- [ ] Percentuais devem mostrar + ou - e símbolo %

**Cores**
- [ ] Positivo: Verde (#22C55E)
- [ ] Negativo: Vermelho (#EF4444)
- [ ] Muted: Cinza (#A1A1AA)

**Tipografia**
- [ ] Headings: Chivo
- [ ] Body: Manrope
- [ ] Números: JetBrains Mono

## Testes de API

**Teste de Integração com Backend**

1. Certificar-se que backend FastAPI está rodando
2. Abrir DevTools (F12)
3. Ir para Network tab
4. Recarregar página
5. Verificar requisições:
   - `GET /api/prices/latest` - 200 OK
   - `GET /api/market/sectors` - 200 OK
   - `GET /api/ingestion/status` - 200 OK

**Teste de Error Handling**

1. Desligar backend
2. Recarregar frontend
3. Deve mostrar loading spinner
4. Deverá exibir empty state ou mensagem amigável

## Testes de Performance

- [ ] Primeira carga < 3s (com cache)
- [ ] Dashboard deve ser interativo < 1s
- [ ] Gráficos com 100+ pontos devem renderizar < 2s
- [ ] Scroll não deve travar

## Checklist Final

- [ ] Todas 4 páginas funcionam
- [ ] Navegação via hash routing funciona
- [ ] API endpoints são consumidos corretamente
- [ ] Valores formatados em pt-BR
- [ ] Layout responsivo em 3 breakpoints
- [ ] Cores seguem design system
- [ ] Ícones carregam via lucide
- [ ] Gráficos renderizam com tema dark
- [ ] Loading states funcionam
- [ ] Sidebar mobile funciona
- [ ] Sem erros no console
