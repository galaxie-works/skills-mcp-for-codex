# Guia do Manifesto para o Skills Installer

![Stack](https://img.shields.io/badge/stack-Tauri_%2B_React_%2B_TS-0ea5e9?style=for-the-badge)
![SeguranÃ§a](https://img.shields.io/badge/install-safe_actions-22c55e?style=for-the-badge)
![Cross Platform](https://img.shields.io/badge/OS-Windows_macOS_Linux-f97316?style=for-the-badge)

Este guia descreve como o app instalador deve consumir o `manifest.json` deste repositÃ³rio.

## Objetivo

Permitir que uma pessoa escolha categorias ou skills individuais e instale tudo com seguranÃ§a em:

| Target | Pasta |
| --- | --- |
| `codex` | `~/.codex/skills` |
| `agents` | `~/.agents/skills` |

## Fluxo recomendado

~~~text
GitHub repo
  â†“
manifest.json
  â†“
Skills Installer
  â†“
seleÃ§Ã£o por categoria/skill
  â†“
download da versÃ£o escolhida
  â†“
validaÃ§Ã£o de SKILL.md
  â†“
backup local se jÃ¡ existir
  â†“
cÃ³pia segura para o destino
  â†“
resultado por item
~~~

## Campos principais

| Campo | Uso no app |
| --- | --- |
| `categories[].id` | Chave da sidebar e filtros. |
| `categories[].name` | Nome visual da categoria. |
| `categories[].color` | Cor de badge/card. |
| `categories[].skills[]` | Lista renderizada no centro da tela. |
| `skills[].id` | ID estÃ¡vel do skill dentro do repo. |
| `skills[].name` | Nome amigÃ¡vel para UI. |
| `skills[].descriptionPtBr` | DescriÃ§Ã£o principal em portuguÃªs. |
| `skills[].descriptionOriginal` | DescriÃ§Ã£o original do SKILL.md, Ãºtil para busca avanÃ§ada. |
| `skills[].path` | Caminho dentro do repo para copiar. |
| `skills[].installable` | Se pode ser instalado pelo app. |
| `skills[].system` | Se Ã© skill de runtime/sistema. |
| `skills[].sourceUrl` | Link de origem quando conhecido. |

## Estados de instalaÃ§Ã£o

| Estado | Como calcular |
| --- | --- |
| `Not installed` | Pasta de destino nÃ£o existe. |
| `Installed` | Pasta existe e contÃ©m `SKILL.md`. |
| `Update available` | Pasta existe, mas hash/versÃ£o local difere do item baixado. |
| `Invalid local install` | Pasta existe, mas falta `SKILL.md`. |
| `Not installable` | `installable = false`, normalmente skill de sistema/runtime. |

## InstalaÃ§Ã£o segura

O app nÃ£o deve executar comandos arbitrÃ¡rios. A instalaÃ§Ã£o pode ser feita com operaÃ§Ãµes de arquivo:

1. baixar o zip/tarball do GitHub na versÃ£o selecionada;
2. localizar cada `skills[].path`;
3. validar `SKILL.md`;
4. criar backup com timestamp se o destino jÃ¡ existir;
5. copiar arquivos para `~/.codex/skills/<id>` ou `~/.agents/skills/<id>`;
6. registrar logs simples por item.

## UI sugerida

- Sidebar com categorias, contagem e checkbox "selecionar tudo".
- Ãrea central com cards de skills.
- Busca por nome, descriÃ§Ã£o e tags.
- Filtros por status: instalado, atualizaÃ§Ã£o disponÃ­vel, nÃ£o instalado.
- Drawer/modal de detalhes com descriÃ§Ã£o em pt-BR, descriÃ§Ã£o original, origem e caminho.
- Tela de progresso com log por skill.
- BotÃ£o "Abrir pasta instalada".

## Regenerar manifesto

~~~powershell
.\tools\generate-installer-manifest.ps1
~~~

Sempre rode depois de atualizar `docs/installed-skills.md` ou mexer no acervo de `skills/`.
