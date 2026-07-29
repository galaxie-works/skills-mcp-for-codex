# Instalação prioritária de skills - 2026-07-29

## Resultado executivo

Instalação e espelhamento concluídos para o lote prioritário pedido em 2026-07-29.

- Skills esperados no lote: `109`
- Skills verificados em `C:\Users\consa\.agents\skills`: `109`
- Skills verificados em `C:\Users\consa\.codex\skills`: `109`
- Skills espelhados na repo `skills-mcp-for-codex\skills`: `109`

O ponto mais importante: a regra operacional foi aplicada. Tudo que entrou pelo instalador foi sincronizado para o canone global do Codex em `C:\Users\consa\.codex\skills`.

## Fontes instaladas

| Fonte | Resultado | Observação |
|---|---:|---|
| `https://github.com/microsoft/azure-skills` | 34 skills | Pacote Azure/Microsoft para AI, deploy, app onboarding, AKS, quotas, storage, compliance e migração. |
| `https://github.com/anthropics/skills` | 18 skills | Pacote de documentos, design, frontend, artefatos web e criação de skills. |
| `https://github.com/coreyhaines31/marketingskills` | 49 skills | Pacote completo de marketing, incluindo `cold-email`, copy, SEO, CRO, ads, launch, pricing e lifecycle. |
| `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill` | 7 skills | Pacote de UI/UX, design system, brand, slides e `ui-ux-pro-max`. |
| `https://github.com/pbakaus/impeccable` | 1 skill | `impeccable`, usado para design, redesign, critique, audit e polish de interfaces. |

## Skills importantes confirmados

- `cold-email`: instalado e verificado em `C:\Users\consa\.codex\skills\cold-email`.
- `impeccable`: instalado e verificado em `C:\Users\consa\.codex\skills\impeccable`.
- `ui-ux-pro-max`: instalado e verificado em `C:\Users\consa\.codex\skills\ui-ux-pro-max`.
- `azure-ai`: instalado e verificado em `C:\Users\consa\.codex\skills\azure-ai`.
- `azure-app-onboard`: instalado e verificado em `C:\Users\consa\.codex\skills\azure-app-onboard`.
- `frontend-design`: instalado e verificado em `C:\Users\consa\.codex\skills\frontend-design`.
- `brand-guidelines`: instalado e verificado em `C:\Users\consa\.codex\skills\brand-guidelines`.

## Sobre o `critique`

O comando abaixo foi testado explicitamente:

```powershell
npx skills add https://github.com/pbakaus/impeccable --skill critique -g -y --copy --full-depth
```

Resultado: o CLI informou que nao existe um skill separado chamado `critique` nesse repo. O unico skill exposto e `impeccable`.

Isso nao bloqueia o uso: o `SKILL.md` do `impeccable` instalado declara suporte a `critique`, `audit`, `polish`, `redesign`, `frontend interface`, `visual hierarchy`, `accessibility`, `motion`, `typography`, `layout`, `color` e design systems.

Uso recomendado em prompt:

```text
Use o skill impeccable para fazer uma critique/audit desta interface antes de propor mudanças.
```

## Alertas do instalador

- Alguns destinos globais falharam porque `Eve` e `PromptScript` nao suportam instalação global. Isso nao afetou o Codex.
- O pacote Azure pulou estes `SKILL.md` internos por frontmatter incompleto:
  - `azure-app-onboard\deploy\SKILL.md`
  - `azure-app-onboard\prepare\SKILL.md`
  - `azure-app-onboard\scaffold\SKILL.md`
- O relatório de risco do CLI marcou alguns skills Azure como risco maior por poderem orientar deploy, validação, infraestrutura ou finetuning. Isso e esperado para skills operacionais e nao significa erro de instalação.

## Evidencias locais

Log bruto da instalação:

```text
C:\Users\consa\.codex\tmp\skills-install-priority-20260729.log
```

Backup antes da sincronização para o global do Codex:

```text
G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\.codex-backups\priority-skills-install-20260729-104742\codex-before
```

Backup antes da sincronização para a repo:

```text
G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\.codex-backups\priority-skills-install-20260729-104825\repo-before
```

## Por que agrega para a Galaxie

- Azure/Microsoft: ajuda a desenhar, validar, estimar e operar infraestrutura cloud sem depender de memoria solta.
- Anthropic: reforça geração de documentos, artefatos, apresentações, design e frontend com padrões mais maduros.
- MarketingSkills: cobre prospecção, cold email, SEO, CRO, ads, conteúdo, lançamento, pricing e retenção, que são exatamente alavancas de fundador solo.
- UI/UX Pro Max e Impeccable: elevam a qualidade visual das interfaces e ajudam a evitar UI genérica, especialmente nos dashboards, docs, landing pages e instalador de skills.
