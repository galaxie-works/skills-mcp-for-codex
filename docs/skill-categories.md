# Categorias dos Skills

![Manifest](https://img.shields.io/badge/manifest-ready-22c55e?style=for-the-badge)
![Idioma](https://img.shields.io/badge/descricoes-pt--BR-14b8a6?style=for-the-badge)
![Installer](https://img.shields.io/badge/Tauri_Installer-ready-8b5cf6?style=for-the-badge)

> Mapa visual para navegar o acervo de skills por intenção de uso. Este arquivo foi gerado a partir de `docs/installed-skills.md` e alimenta o `manifest.json` usado pelo app instalador.

## Resumo

| Métrica | Valor |
| --- | ---: |
| Categorias | 12 |
| Skills no manifesto | 1211 |
| Skills instaláveis | 1206 |
| Skills de sistema/runtime | 5 |

## Categorias

| Categoria | ID | Skills | Instaláveis | Descrição |
| --- | --- | ---: | ---: | --- |
| <span style="color:#ec4899">&#9679;</span> **Frontend, UI e Design System** | `frontend-ui` | 112 | 112 | Skills para criar interfaces, componentes, layouts, Tailwind, React, shadcn, animações e experiências visuais bonitas. |
| <span style="color:#2563eb">&#9679;</span> **WordPress, Sites e CMS** | `wordpress-web` | 10 | 10 | Skills para WordPress, Elementor, GenerateBlocks, auditoria de sites, páginas institucionais e publicação web. |
| <span style="color:#f97316">&#9679;</span> **Marketing, Growth e SEO** | `marketing-growth` | 78 | 78 | Skills para SEO, conteúdo, anúncios, analytics, social media, funis, posicionamento e crescimento comercial. |
| <span style="color:#14b8a6">&#9679;</span> **Produto, Operação e PO** | `product-ops` | 43 | 43 | Skills para priorização, backlog, PRD, discovery, gestão de produto, rotinas executivas e automação do dia a dia. |
| <span style="color:#8b5cf6">&#9679;</span> **Automação, Agentes e MCP** | `automation-agents` | 50 | 50 | Skills para browser automation, agentes, MCPs, workflows, integrações e execução assistida por ferramentas. |
| <span style="color:#0ea5e9">&#9679;</span> **Backend, APIs e Arquitetura** | `backend-architecture` | 56 | 56 | Skills para APIs, Laravel, bancos, autenticação, arquitetura, padrões backend e integrações complexas. |
| <span style="color:#22c55e">&#9679;</span> **DevOps, Cloud e Deploy** | `devops-cloud` | 54 | 54 | Skills para Vercel, Azure, CI/CD, GitHub Actions, deploy, infraestrutura, ambientes e observabilidade. |
| <span style="color:#ef4444">&#9679;</span> **Qualidade, Testes e Segurança** | `quality-security` | 235 | 235 | Skills para QA, auditoria, acessibilidade, testes, lint, revisão, segurança e hardening. |
| <span style="color:#f59e0b">&#9679;</span> **Conteúdo, Áudio, Vídeo e Mídia** | `content-media` | 93 | 93 | Skills para escrita, documentação, storytelling, áudio, vídeo, imagens, apresentações e conteúdo multimídia. |
| <span style="color:#6366f1">&#9679;</span> **Dados, IA e Pesquisa** | `data-ai` | 353 | 353 | Skills para dados, IA, modelos, pesquisa, análise, ciência, bancos vetoriais e experimentação. |
| <span style="color:#64748b">&#9679;</span> **Negócios, Finanças e Estratégia** | `business-strategy` | 22 | 22 | Skills para estratégia, CFO/CMO/COO, pricing, vendas, customer research, planejamento e tomada de decisão. |
| <span style="color:#475569">&#9679;</span> **Sistema, Runtime e Utilitários** | `system-runtime` | 105 | 100 | Skills internos, utilitários técnicos e capacidades de suporte que mantêm o ambiente Codex funcionando. |

## Amostras por Categoria

| Categoria | Exemplos de skills |
| --- | --- |
| **Frontend, UI e Design System** | ``2d Games``, ``3d Games``, ``3d web Experience``, ``Accessibility Auditor``, ``ai Elements``, ``ai Product``, ``ai sdk``, ``Algolia Search`` |
| **WordPress, Sites e CMS** | ``Elementor Addon Architecture``, ``Elementor Content``, ``Elementor Controls``, ``Elementor Development``, ``Elementor Hooks``, ``Elementor Widget Development``, ``Elementor Widgets``, ``seo Wordpress Manager`` |
| **Marketing, Growth e SEO** | ``ab Test Setup``, ``ad Creative``, ``ad Creative``, ``ai Image Generation``, ``ai Video Generation``, ``Analytics Tracking``, ``Apify Trend Analysis``, ``app Store Optimization`` |
| **Produto, Operação e PO** | ``Agile Product Owner``, ``ai Wrapper Product``, ``Backend to Frontend Handoff Docs``, ``Brand Guidelines``, ``Daily Meeting Update``, ``Data Privacy Compliance``, ``Difficult Workplace Conversations``, ``Discord bot Architect`` |
| **Automação, Agentes e MCP** | ``Agent Management``, ``Agent Messaging``, ``Agent Teams``, ``Agirails Agent Payments``, ``Bright Data mcp``, ``Browser Automation``, ``Chat sdk``, ``Claude api`` |
| **Backend, APIs e Arquitetura** | ``api Contract Checker``, ``api Design Principles``, ``api Error Taxonomy``, ``API Integration Specialist``, ``api Patterns``, ``api Request Builder``, ``Architecture Patterns``, ``Architecture Review`` |
| **DevOps, Cloud e Deploy** | ``ai Gateway``, ``Auth``, ``Azure ai``, ``Azure Functions``, ``Azure Hosted Copilot sdk``, ``Azure Messaging``, ``Azure Quotas``, ``Azure Upgrade`` |
| **Qualidade, Testes e Segurança** | ``Accessibility``, ``Accessibility Basic Check``, ``Active Directory Attacks``, ``Agent Browser``, ``Agent Development``, ``Agent Tool Builder``, ``ai seo``, ``Analytics`` |
| **Conteúdo, Áudio, Vídeo e Mídia** | ``Agent Browser``, ``Agent md Refactor``, ``Agile Product Owner``, ``Algorithmic art``, ``Architecture``, ``Artist Workspace``, ``Audio Analyzer``, ``Audio Converter`` |
| **Dados, IA e Pesquisa** | ``Adaptyv``, ``Address Github Comments``, ``Aeon``, ``Agent Evaluation``, ``Agent Manager Skill``, ``Agent Memory mcp``, ``Agent Memory Systems``, ``ai Agents Architect`` |
| **Negócios, Finanças e Estratégia** | ``app Builder``, ``Caching Strategy Helper``, ``ceo Advisor``, ``Competitor Alternatives``, ``Complexity Guardrails``, ``Content Creator``, ``Copywriting``, ``cto Advisor`` |
| **Sistema, Runtime e Utilitários** | ``Adapt``, ``Algorithmic art``, ``Bolder``, ``Brainstorming``, ``Brand Designer``, ``Brand Guidelines``, ``bug Repro Plan``, ``Canvas Design`` |

## Como usar no app

O app deve usar `manifest.json` como fonte de verdade para:

- montar a sidebar de categorias;
- permitir checkbox por categoria ou por skill;
- pesquisar por `name`, `descriptionPtBr`, `descriptionOriginal` e `tags`;
- mostrar status `Installed`, `Update available` ou `Not installed`;
- validar `hasSkillFile` antes de habilitar instalação;
- copiar apenas itens com `installable = true`;
- tratar skills com `system = true` como leitura/runtime, não como instalação comum.

## Paleta sugerida

As cores no manifesto foram pensadas para uma UI com cards, filtros e badges:

- `frontend-ui`: rosa energia para UI/design.
- `wordpress-web`: azul web/CMS.
- `marketing-growth`: laranja performance.
- `product-ops`: teal operação.
- `automation-agents`: violeta automação.
- `backend-architecture`: azul técnico.
- `devops-cloud`: verde deploy.
- `quality-security`: vermelho atenção.
- `content-media`: âmbar criação.
- `data-ai`: índigo IA/dados.
- `business-strategy`: slate executivo.
- `system-runtime`: cinza utilitário.
