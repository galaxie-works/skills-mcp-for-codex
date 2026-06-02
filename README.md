# skills-mcp-for-codex

![Status](https://img.shields.io/badge/status-ativo-22c55e?style=for-the-badge)
![Fonte](https://img.shields.io/badge/fonte-Codex_Global-0ea5e9?style=for-the-badge)
![Skills](https://img.shields.io/badge/skills-1207-f97316?style=for-the-badge)
![MCP](https://img.shields.io/badge/MCPs-documentados-8b5cf6?style=for-the-badge)
![Idioma](https://img.shields.io/badge/docs-pt--BR-14b8a6?style=for-the-badge)

> Repositório-memória da nossa máquina Codex: aqui ficam os skills, superpowers, MCPs e inventários que fazem o Codex trabalhar como um copiloto de verdade para Galaxie Works.

## Visao Geral

Este repositório é o **espelho versionado** da instalação local de skills do Codex.

Ele existe para evitar aquele caos clássico de skill espalhado por `.agents`, `.claude`, exports antigos, threads perdidas e pastas temporárias. A regra agora é simples:

> **Todo skill útil precisa existir em `C:\Users\consa\.codex\skills`.**

Depois disso, este repo é atualizado para registrar o estado atual, com histórico no GitHub e documentação legível.

## Painel Atual

| Area | Status | O que significa |
| --- | --- | --- |
| ![Canonical](https://img.shields.io/badge/canonico-Codex_Global-0ea5e9) | `C:\Users\consa\.codex\skills` | Fonte oficial local. Se não está aqui, ainda não está realmente consolidado. |
| ![Skills](https://img.shields.io/badge/top--level-1207-f97316) | `skills/` | Espelho dos skills instalados no global do Codex. |
| ![System](https://img.shields.io/badge/system-5-64748b) | `skills/.system` | Skills internos/runtime do Codex. |
| ![Docs](https://img.shields.io/badge/definicoes-1210-22c55e) | `docs/installed-skills.md` | Índice com nome, caminho, descrição e motivo de cada skill. |
| ![Superpowers](https://img.shields.io/badge/superpowers-14-a855f7) | `superpowers-skills/` | Superpowers instalados e documentados. |
| ![Total](https://img.shields.io/badge/capacidades-1225-ef4444) | repo inteiro | Skills + superpowers + snapshots MCP documentados. |

## Regra De Ouro

```text
Instalou skill em qualquer lugar?
        ↓
Copie/consolide para C:\Users\consa\.codex\skills
        ↓
Espelhe este repo
        ↓
Regere os docs
        ↓
Commit + push em galaxie-works/skills-mcp-for-codex
```

Nao deixar skills definitivos apenas nestes lugares:

| Local | Uso aceitavel | Risco |
| --- | --- | --- |
| `.agents\skills` | Instalação temporária feita por `npx skills add` | O Codex pode não enxergar em novas sessões globais. |
| `.claude\skills` | Compatibilidade com outros agentes | Vira duplicidade se não for consolidado. |
| exports antigos | Backup ou transporte | Fica desatualizado rápido. |
| mirrors locais | Consulta histórica | Não deve ser fonte primária. |

## Mapa Do Repositorio

| Caminho | Tipo | Para que serve |
| --- | --- | --- |
| [`skills/`](./skills) | Biblioteca | Mirror dos skills globais do Codex. |
| [`skills/.system`](./skills/.system) | Runtime | Skills internos usados pelo próprio Codex. |
| [`superpowers-skills/`](./superpowers-skills) | Superpowers | Capacidades auxiliares instaladas localmente. |
| [`mcp/`](./mcp) | MCP | Snapshot dos servidores MCP configurados. |
| [`docs/installed-skills.md`](./docs/installed-skills.md) | Inventário | Lista completa dos skills, descrições e motivo de uso. |
| [`docs/installed-superpowers.md`](./docs/installed-superpowers.md) | Inventário | Lista dos superpowers disponíveis. |
| [`docs/installed-mcps.md`](./docs/installed-mcps.md) | Inventário | MCPs configurados, transporte e notas seguras. |
| [`skill-update-sources.md`](./skill-update-sources.md) | Atualizações | Onde procurar novas versões dos skills. |

## Tags Mentais

Use estas tags para pensar no acervo sem se perder no volume:

![Produto](https://img.shields.io/badge/Produto_PO%2C_PRD%2C_Jira-2563eb)
![Marketing](https://img.shields.io/badge/Marketing_SEO%2C_ads%2C_conteudo-f97316)
![Design](https://img.shields.io/badge/Design_UI%2C_Figma%2C_Tailwind-ec4899)
![Dev](https://img.shields.io/badge/Dev_React%2C_Laravel%2C_Vercel-22c55e)
![Automacao](https://img.shields.io/badge/Automacao_MCP%2C_browser%2C_workflows-8b5cf6)
![Midia](https://img.shields.io/badge/Midia_audio%2C_video%2C_social-14b8a6)

## Como Atualizar

### 1. Consolidar o global

Todo skill novo deve terminar aqui:

```powershell
C:\Users\consa\.codex\skills
```

Se o instalador jogar em `.agents\skills`, copie o conteúdo da pasta para o global sem criar aninhamento:

```powershell
$src = "CAMINHO\PARA\.agents\skills\nome-do-skill"
$dst = "C:\Users\consa\.codex\skills\nome-do-skill"

if (-not (Test-Path -LiteralPath $dst)) {
  New-Item -ItemType Directory -Path $dst -Force | Out-Null
}

Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
```

### 2. Limpar sujeira

Antes de espelhar, remover arquivos gerados:

```powershell
Get-ChildItem "C:\Users\consa\.codex\skills" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem "C:\Users\consa\.codex\skills" -Recurse -File -Filter "*.pyc" | Remove-Item -Force
```

### 3. Atualizar o mirror

Espelhar o global para `skills/`, regenerar os docs e subir:

```powershell
git status --short
git add -A
git commit -m "Refresh canonical Codex skills mirror"
git push origin main
```

## Checklist De Qualidade

Antes de fechar qualquer atualização, validar:

| Check | Esperado |
| --- | --- |
| `C:\Users\consa\.codex\skills\nome-do-skill\SKILL.md` | Existe |
| `skills\nome-do-skill\SKILL.md` | Existe no repo |
| `__pycache__` | Zero |
| `.pyc` | Zero |
| `skill\skill` | Zero pasta aninhada acidental |
| `docs/installed-skills.md` | Regenerado com descrição |
| `git status --short` | Limpo depois do push |

## Para Que Isso Agrega

| Beneficio | Impacto pratico |
| --- | --- |
| Continuidade | Novas threads do Codex conseguem recuperar o contexto real do acervo. |
| Velocidade | Menos tempo procurando onde um skill foi parar. |
| Governança | Git mostra quando entrou, saiu ou mudou uma capacidade. |
| Operação | Ajuda a automatizar Galaxie, PO work, marketing, site, SEO, Vercel, WordPress e MCPs. |
| Segurança | Evita depender de pastas temporárias ou instalações invisíveis. |

## Links Rapidos

- [Inventario completo de skills](./docs/installed-skills.md)
- [Inventario de superpowers](./docs/installed-superpowers.md)
- [Inventario de MCPs](./docs/installed-mcps.md)
- [Fontes para atualizacoes](./skill-update-sources.md)
- [Repositorio no GitHub](https://github.com/galaxie-works/skills-mcp-for-codex)

---

> **Resumo executivo:** este repo é o mapa vivo das capacidades do Codex na máquina. Se um skill importa para o futuro da Galaxie, ele precisa estar no global, documentado aqui e versionado no GitHub.
