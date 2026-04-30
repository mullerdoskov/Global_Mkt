# Skills do ecossistema — espelho local

Este diretório espelha as `SKILL.md` dos agents do ecossistema multi-agent
de Lucas que são relevantes para a operação da **Market Data Platform**.

## Por que existir

A Routine `MDP Sprint Worker` executa em ambiente headless (sem chat
interativo). Quando o harness do Claude Code carrega skills, ele lê do
plugin `anthropic-skills` instalado no perfil do usuário. Em runs
agendados, queremos que essa visibilidade seja **explícita** no repo
para que:

1. Reviewers humanos vejam quais agents/skills moldam o estilo das
   decisões automatizadas (ADR formal, gate QA, PSCW, defesa contra
   prompt injection na ingestão).
2. O run consiga referenciar a skill por path quando precisar
   pontualmente (ex.: `<repo>/.claude/skills/architect-of-software/SKILL.md`
   ao escrever um ADR).
3. O contrato de comportamento da Routine fique sob versionamento —
   se uma skill upstream mudar, a divergência aparece num diff.

## Fonte autoritativa

A fonte autoritativa **não é este diretório**. É o plugin instalado
em `~/AppData/Roaming/Claude/.../skills-plugin/.../skills/<nome>/`.
Os arquivos aqui são **cópias congeladas** no momento do commit —
podem ficar fora de sincronia com a versão upstream. Para ressincar,
re-executar a issue ISSUE-022 (ou variante) com diff de comparação.

## Skills incluídas (13)

Selecionadas por relevância à MDP. Critério: skill que a Routine
provavelmente vai invocar ou referenciar ao trabalhar em backend,
arquitetura, segurança, DevOps, QA ou ingestão de dados deste
projeto.

| Skill | Por que está aqui |
|---|---|
| `newgen` | Operador do ecossistema (33 agents). É o "shell" das outras. |
| `backend-senior-engineer` | Persona principal da Routine para hard code (Python + Postgres + FastAPI). |
| `architect-of-software` | ADRs formais (DECISIONS.md) e desenho proporcional ao porte. |
| `pscw` | Política de Segurança para Claude Workforce v1.0 — R1-R28. |
| `pscw-aware-architect` | Defesa contra prompt injection na ingestão de dados externos (yfinance, Brapi, Alpha Vantage). |
| `qa-engineer` | Gate QA antes de marcar PR como ready (smoke + edge cases + regressão). |
| `agente-devops` | CI/CD, IaC, agendamento (ISSUE-015/021/023 — Task Scheduler, GitHub Actions, pg_dump). |
| `aquisicao-tratamento-dados` | Pipeline de aquisição → PostgreSQL — núcleo do produto MDP. |
| `security-baseline-policy` | Baselines técnicas (criptografia, log, retenção, segredos). |
| `gerente-de-projeto` | Cronograma, PROGRESS.md, status report ao COO. |
| `project-flow-architect` | Orquestrador — fluxograma multi-agent quando issue grande exige composição. |
| `coo-agent` | Governança operacional — valida se issue resolve problema de negócio. |
| `front-end-dev` | Telas e componentes — relevante para ISSUE-018 (watchlist UI já entregue) e ISSUE-019 (Vite + React, Sprint 3 opcional). |

## Skills NÃO incluídas (e por quê)

- `docx`, `pptx`, `pdf`, `xlsx`, `canvas-design`, `algorithmic-art`,
  `web-artifacts-builder`: formato/asset, não engenharia da MDP.
- `pmo-live-companion`, `pm-prd-companion`, `ux-designer-mercado-eletrico`:
  product/UX, fora do escopo da Routine atual (engenharia-only).
- `mcp-builder`, `ai-router`, `consolidate-memory`, `schedule`,
  `setup-cowork`, `skill-creator`: meta-tools de plataforma, não de
  produto.

Se um run futuro precisar de uma destas, abrir issue separada para
adicionar.

## Atualização

Não editar os SKILL.md aqui à mão. O fluxo é:
1. Editar o SKILL.md upstream no plugin install.
2. Abrir issue para ressincar (ISSUE-022-followup).
3. Run da Routine copia os arquivos de novo (mesmo script da Run #18).

Diff entre upstream e este espelho é a fonte de verdade para detectar
drift.
