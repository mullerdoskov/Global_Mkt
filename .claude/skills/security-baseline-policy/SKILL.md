---
name: security-baseline-policy
description: Use when the user asks to draft, formalize, or update a security policy or technical baseline. Triggers: "política de segurança", "padrão de senha/criptografia/log/acesso", "baseline de hardening", "classificação de dado", "gestão de segredos", "política LGPD", "política de retenção". Output in PT-BR: policy in prose plus technical-standards table, with optional Brazilian energy-trading sector layer. Not for threat modeling, pentest, incident response, or NDA review.
---

# Security Baseline Policy

Skill para gerar políticas de segurança e padrões técnicos base em PT-BR para times de software, com calibração opcional para comercializadoras do setor elétrico brasileiro.

## Quando usar

Casos típicos:
- "Monta a política de senhas pro Energy Ops"
- "Qual o padrão de criptografia em repouso na AWS pra Postgres com dados de contratos?"
- "Preciso de uma política de retenção de log que respeite LGPD"
- "Define o baseline de hardening pra um novo serviço FastAPI"
- "Documento de classificação de dados — como faço?"
- "Formaliza essas regras de acesso que combinamos"

Não use para threat model, pentest, resposta a incidente, revisão de NDA, ou avaliação de fornecedor — outras skills cobrem isso.

## Estrutura do entregável

Sempre dois artefatos no mesmo documento, nesta ordem:

1. **Política (prosa, PT-BR)** — texto publicável: objetivo, escopo, papéis, regras numeradas, exceções, vigência. Tom executivo mas concreto. LGPD citada quando aplicável.
2. **Apêndice A — Padrões Técnicos (tabela)** — parâmetros concretos: algoritmo, força, protocolo, retenção, escopo. Tom de engenharia. Sem prosa.

A política é o "porquê e o quê", o apêndice é o "como". Os dois caminham juntos — política sem números é vaga, tabela sem política é descontextualizada.

## Detecção de contexto

Antes de escrever, varra o histórico da conversa e arquivos anexos. Tente extrair sozinho:

- **Tema da política** — senha, criptografia, retenção, classificação, hardening, etc.
- **Escopo de aplicação** — produto inteiro? componente específico? toda a empresa?
- **Stack relevante** — Python, FastAPI, Postgres, AWS, etc., quando mencionado.
- **Tipo de dado** — pessoal (LGPD), de trading (sigilo competitivo), público.
- **Setor** — se for comercializadora, ACL, CCEE, ONS, trading de energia, ative a seção setorial.

**Pergunte SÓ se um destes estiver crítico e ausente.** Não faça onda de perguntas. O default é: declare as premissas no início do documento ("Premissas: stack X, escopo Y, dado tipo Z") e siga.

## Espinha da política (ordem fixa)

Toda política gerada segue esta estrutura, em três blocos. Algumas seções podem ser enxutas (1-2 parágrafos) quando o tema da política não as exige; nenhuma é omitida.

### Front matter

1. **Aprovação e assinatura** — quadro com aprovador (CEO/CISO/DPO conforme cabível), data de aprovação, próximo ciclo de revisão. Em política informal de um único time, fica leve (responsável + data). Em política corporativa, vira ata.
2. **Histórico de versões** — tabela markdown: versão, data, autor, resumo da mudança. Primeira versão é v1.0.

### Corpo — moldura

3. **Objetivo** — uma frase. Por que o documento existe.
4. **Escopo** — onde se aplica (sistemas, times, dados, ambientes). Diga também onde NÃO se aplica.
5. **Referências normativas** — base legal e padrões: LGPD (Lei 13.709/2018), ISO/IEC 27001, NIST CSF quando relevante, regulamentação setorial (CCEE, ANEEL, ONS) quando contexto for comercializadora. Cite versão/ano.
6. **Definições** — termos técnicos da política. Curtas, operacionais. Termos LGPD quando há dado pessoal: titular, controlador, operador, dado pessoal, dado pessoal sensível.
7. **Glossário** — siglas e jargão técnico, separado das definições. Pode ser tabela. Se ficar curto (≤5 itens), fundir com Definições.
8. **Princípios norteadores** — moldura conceitual: defense in depth, least privilege, secure by default, separation of duties, fail secure. 4-6 princípios, 1 frase cada. Ancora as Regras.

### Corpo — operacional

9. **Papéis e responsabilidades** — quem aprova, quem implementa, quem audita. Use os papéis do organograma do projeto quando o usuário os mencionar (PO, Tech Lead, DevOps, etc.). Tabela RACI quando útil.
10. **Regras** — corpo da política. Numerar (R1, R2, ...) para auditoria. "Deve" é vinculante; "Recomenda-se" é orientação.
11. **Métricas e indicadores** — KPIs (cobertura, ex: % de serviços com MFA) e KRIs (risco, ex: nº de senhas vazadas detectadas/mês). 4-8 indicadores, com fórmula e periodicidade. Sem inventar — só métricas que se medem com a stack atual ou que se compromete a instrumentar.
12. **Treinamento e conscientização** — obrigatoriedade (público, periodicidade), forma de comprovação. Exemplo padrão: onboarding + reciclagem anual + treinamento ad-hoc após incidente.
13. **Comunicação de incidentes e canal de denúncia** — onde reportar suspeita ou incidente, prazo (sugerido: imediato; máximo 24h), confidencialidade do reportante, vedação de retaliação. **Esta seção é nível-política** ("ligue para X"); o procedimento operacional de resposta é outra política, fora do escopo desta skill.
14. **Exceções e desvios** — como se pede exceção, quem aprova, prazo máximo da exceção (sugerido: 90 dias renovável uma vez), registro obrigatório.
15. **Sanções por descumprimento** — geralmente referência cruzada à política de RH e ao contrato de trabalho/prestação de serviço. Não invente punições. Texto padrão: "O descumprimento sujeita o colaborador às sanções previstas em [política de RH / código de conduta], sem prejuízo das responsabilidades civis, criminais e administrativas cabíveis."

### Back matter

16. **Vigência e revisão** — data de entrada em vigor, periodicidade de revisão (default: anual), gatilhos extra de revisão (mudança regulatória, incidente significativo, mudança de stack ou arquitetura).
17. **Apêndice A — Padrões Técnicos** — tabela markdown com parâmetros concretos.

## Apêndice A — formato

Tabela markdown, três colunas mínimas. Pode adicionar coluna "Justificativa" quando há decisão polêmica.

| Item | Padrão | Escopo de aplicação |
|------|--------|---------------------|
| ...  | ...    | ...                 |

Para cada item, valor concreto. Nada de "criptografia forte" — diga "AES-256-GCM em repouso, TLS 1.3 em trânsito, rotação anual de chave em KMS".

## Padrões base

Defaults a usar quando o tema cair em uma destas áreas. Adapte se o contexto pedir, mas não enfraqueça sem justificativa.

### Autenticação
- Senhas: mínimo 12 caracteres, sem complexidade obrigatória, validação contra base de senhas vazadas (HaveIBeenPwned ou equivalente).
- MFA obrigatório para acesso administrativo; recomendado para usuários com acesso a dado Confidencial ou Restrito.
- SSO via OIDC/SAML quando viável, com IdP corporativo.
- Sessão: token de acesso curto (15-60 min), refresh com rotação, revogação imediata em logout/comprometimento.

### Criptografia
- Em trânsito: TLS 1.3. TLS 1.2 só com cipher suites autorizadas e prazo de saída.
- Em repouso: AES-256-GCM. Banco gerenciado: criptografia transparente (RDS encryption, etc.) habilitada.
- Chaves: gerenciadas em KMS (AWS KMS, GCP KMS, Vault). Rotação anual ou imediata em comprometimento.

### Gestão de segredos
- Nunca em código. Nunca em arquivo `.env` versionado. Nunca em variável de pipeline em texto plano.
- Cofre: AWS Secrets Manager, Vault, ou equivalente.
- Acesso por IAM/RBAC, log de acesso habilitado, alerta em padrão de acesso anômalo.
- Rotação automática quando suportado pelo serviço.

### Logs e auditoria
- Logar: autenticação, autorização, mudança de configuração, acesso a dado Confidencial/Restrito, ações privilegiadas.
- Retenção: 12 meses online, 5 anos arquivado (alinhar com auditorias regulatórias e LGPD).
- NUNCA logar: senha, token, dado pessoal sensível em claro, número completo de cartão.
- Mascaramento obrigatório para CPF, conta bancária, e-mail (parcial).

### Classificação de dados
Quatro níveis padrão:
- **Público**: sem restrição.
- **Interno**: dentro da empresa, sem autorização específica.
- **Confidencial**: autorização explícita; inclui dado pessoal LGPD.
- **Restrito**: acesso por exceção; inclui dado pessoal sensível, posições de trading, estratégia comercial, segredos de negócio.

### Hardening base (serviços web)
- Container roda sem privilégio (não-root).
- Imagem-base oficial e atualizada; scan de CVE no pipeline (gate de bloqueio em High/Critical).
- Headers HTTP de segurança: HSTS, CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy.
- Rate limit em endpoints públicos e em endpoints de autenticação (anti brute force).
- Healthcheck separado de endpoint funcional, sem expor versão/dependências.

### LGPD (incluir sempre que dado pessoal estiver no escopo)
- Base legal documentada para cada finalidade de tratamento.
- Política de retenção por categoria de dado.
- Procedimento de atendimento ao titular (acesso, correção, eliminação, portabilidade, oposição).
- Encarregado (DPO) nomeado quando aplicável; canal de contato publicado.
- Registro de operações (ROPA) mantido e atualizado.
- Comunicação de incidente: avaliar em até 72h e notificar ANPD/titular conforme gravidade.

## Seção opcional — setor elétrico (comercializadora)

Ative quando o contexto envolver comercializadora de energia, ACL, CCEE, ONS, ou trading de energia.

### Categorias de dado típicas
- **Posição de portfólio e estratégia comercial** → Restrito. Vazamento gera dano competitivo direto.
- **Contratos bilaterais** → Confidencial. Cláusula contratual de sigilo costuma somar à LGPD.
- **Dados de medição e SCDE** → Confidencial. Origem regulatória (CCEE).
- **Dados de cliente final (consumidor livre)** → Confidencial; LGPD aplicável.
- **Curvas e projeções de preço** → Interno se públicas (PLD oficial), Restrito se proprietárias (modelo interno).
- **Modelos quantitativos (precificação, otimização)** → Restrito; código e parâmetros tratados como segredo de negócio.

### Considerações específicas
- Acesso a CCEE e ONS: certificado digital ICP-Brasil; política de custódia, prazo de validade monitorado, log de uso.
- Dados adquiridos de terceiros (previsão hidrológica, projeções de mercado): cláusulas de redistribuição costumam restringir uso interno; mapear no documento de classificação.
- Integrações com CCEE: tipicamente exigem IP fixo de saída e podem exigir VPN; documentar no padrão de rede.
- Sistemas de trading com decisão automatizada: log de decisão (quem/quando/por quê) com retenção estendida (mín. 5 anos).

## Tom e estilo

- PT-BR formal mas direto. Voz ativa.
- "Deve" é vinculante. "Recomenda-se" é orientação. Use com cuidado.
- Numeração de regras (R1, R2, ...) sempre.
- Sem floreio executivo. O leitor é técnico, jurídico ou auditor.
- Mantenha siglas consagradas em inglês (TLS, MFA, SSO, RBAC, KMS). Traduza o resto.
- Documento alvo: 6-12 páginas. Se passar, fatie em política mãe + políticas-filha temáticas.

## Checklist antes de entregar

Antes de devolver o documento ao usuário, valide:

- [ ] Front matter presente: aprovação/assinatura e histórico de versões.
- [ ] Moldura completa: objetivo, escopo, referências normativas, definições, glossário (ou fundido com definições se ≤5 itens), princípios norteadores.
- [ ] Operacional completo: papéis, regras numeradas (R1, R2...), métricas/KPIs com fórmula, treinamento, comunicação de incidentes, exceções, sanções.
- [ ] Back matter: vigência/revisão e Apêndice A.
- [ ] Apêndice traz parâmetros concretos (algoritmo, comprimento, prazo, escopo) — sem termos vagos.
- [ ] LGPD foi tratada quando há dado pessoal no escopo, com base legal citada.
- [ ] Seção setorial está presente quando o contexto é comercializadora/setor elétrico.
- [ ] Métricas declaradas são instrumentáveis com a stack atual (ou há compromisso explícito de instrumentar).
- [ ] Sanções referenciam política de RH/contrato — não inventam punições.
- [ ] Comunicação de incidentes traz CANAL e prazo, não procedimento operacional.
- [ ] Premissas de contexto declaradas no topo (escopo, stack, tipo de dado).
- [ ] Linguagem PT-BR, voz ativa, sem floreio.
- [ ] Documento cabe em 6-12 páginas; se não, dividir em política mãe + filhas.
