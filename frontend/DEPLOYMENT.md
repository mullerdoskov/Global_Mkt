# Guia de Deployment - Market Data Platform Frontend

## Opções de Deployment

### 1. Desenvolvimento Local

**Pré-requisitos:**
- Navegador moderno (Chrome, Firefox, Safari, Edge)
- Backend FastAPI rodando em `http://localhost:8000`

**Passos:**
```bash
cd frontend/
open index.html
```

Ou servir com um servidor HTTP:
```bash
python -m http.server 8001
```

Acesso: `http://localhost:8001/index.html`

### 2. Integração com Backend FastAPI

**Configurar CORS no backend:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou lista específica de domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Servir frontend junto ao backend:**
```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

Acesso: `http://localhost:8000/`

### 3. Docker

**Dockerfile:**
```dockerfile
FROM nginx:alpine

COPY frontend/index.html /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
    }
}
```

**Build:**
```bash
docker build -t market-platform-frontend .
docker run -p 80:80 market-platform-frontend
```

### 4. Netlify

**netlify.toml:**
```toml
[build]
  command = "echo 'Frontend estático'"
  publish = "."

[[redirects]]
  from = "/api/*"
  to = "http://backend-url/api/:splat"
  status = 200
```

**Deploy:**
```bash
npm install -g netlify-cli
netlify deploy --dir .
```

### 5. Vercel

**vercel.json:**
```json
{
  "buildCommand": "echo 'Static site'",
  "outputDirectory": ".",
  "rewrites": [
    {
      "source": "/api/:match*",
      "destination": "https://backend-url/api/:match*"
    }
  ]
}
```

**Deploy:**
```bash
npm install -g vercel
vercel
```

### 6. AWS S3 + CloudFront

**Upload para S3:**
```bash
aws s3 cp index.html s3://my-bucket/index.html \
  --content-type "text/html" \
  --cache-control "max-age=3600"
```

**CloudFront Distribution:**
- Origin: S3 bucket
- Default Root: `index.html`
- Behavior para `/api/*`: Proxy para backend API

### 7. GitHub Pages

**Limitações:** Requer ajuste de hash routing

**Passos:**
1. Fork do repositório
2. Ativar GitHub Pages em Settings
3. Branch: `main` ou `gh-pages`

**Nota:** Hash routing já funciona sem configuração extra

### 8. Railway.app

**railway.toml:**
```toml
[build]
  builder = "static"

[deploy]
  startCommand = "python -m http.server 8000"
```

**Deploy:**
```bash
railway up
```

## Configuração de API em Produção

### Variável de Ambiente

Editar `index.html`:
```javascript
const API_BASE = process.env.REACT_APP_API_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api');
```

### Proxy em Nginx

```nginx
location /api/ {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Proxy em Apache

```apache
ProxyPreserveHost On
ProxyPass /api http://backend:8000/api
ProxyPassReverse /api http://backend:8000/api
```

## Security Headers

Adicionar em servidor:
```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self' cdn.tailwindcss.com unpkg.com fonts.googleapis.com
```

## Performance

### Compressão

```nginx
gzip on;
gzip_types text/plain text/html text/css application/javascript;
gzip_min_length 1000;
```

### Cache

```nginx
location /index.html {
    add_header Cache-Control "public, max-age=3600";
}

location /api {
    add_header Cache-Control "no-cache";
}
```

## Monitoramento

### Google Analytics (opcional)

Adicionar ao `index.html`:
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Sentry (opcional)

```html
<script src="https://browser.sentry-cdn.com/7.0.0/bundle.min.js"></script>
<script>
  Sentry.init({ dsn: "YOUR_SENTRY_DSN" });
</script>
```

## Troubleshooting

### CORS Errors

**Sintoma:** "Access to XMLHttpRequest at 'http://...' has been blocked by CORS policy"

**Solução:**
1. Verificar CORS no backend
2. Usar proxy em produção
3. Usar `/api` com mesmo domínio

### API não conecta

**Sintoma:** "Failed to fetch from API"

**Checklist:**
- [ ] Backend está rodando?
- [ ] URL API está correta?
- [ ] CORS configurado?
- [ ] Firewall permite conexão?
- [ ] DNS resolve corretamente?

### Gráficos não renderizam

**Sintoma:** Blank charts

**Checklist:**
- [ ] Recharts carregou do CDN?
- [ ] Dados da API chegaram?
- [ ] Console sem erros?
- [ ] Tamanho de viewport OK?

## Rollback

### Se houver problema em produção

```bash
# Restaurar versão anterior
git revert HEAD
git push

# Ou servir versão anterior
aws s3 cp s3://my-bucket/backups/index.html.bak s3://my-bucket/index.html
```

## Checklist de Deployment

- [ ] Backend está rodando e acessível
- [ ] CORS configurado
- [ ] Variáveis de ambiente corretas
- [ ] Security headers configurados
- [ ] Cache headers implementado
- [ ] SSL/TLS habilitado (HTTPS)
- [ ] Gzip compressão ativa
- [ ] Testes de integração passando
- [ ] Performance benchmarks OK (< 3s load)
- [ ] Monitoramento ativo
- [ ] Plano de rollback em lugar
