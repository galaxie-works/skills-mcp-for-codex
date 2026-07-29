# Guia do Manifesto para o Skills Installer

![Stack](https://img.shields.io/badge/stack-Tauri_%2B_React_%2B_TS-0ea5e9?style=for-the-badge)
![Segurança](https://img.shields.io/badge/install-safe_actions-22c55e?style=for-the-badge)
![Cross Platform](https://img.shields.io/badge/OS-Windows_macOS_Linux-f97316?style=for-the-badge)

Este guia descreve como o app instalador deve consumir o `manifest.json` deste repositório.

## Objetivo

Permitir que uma pessoa escolha categorias ou skills individuais e instale tudo com segurança em:

| Target | Pasta |
| --- | --- |
| `codex` | `~/.codex/skills` |
| `agents` | `~/.agents/skills` |

## Fluxo recomendado

~~~text
GitHub repo
  ↓
manifest.json
  ↓
Skills Installer
  ↓
seleção por categoria/skill
  ↓
download da versão escolhida
  ↓
validação de SKILL.md
  ↓
backup local se já existir
  ↓
cópia segura para o destino
  ↓
resultado por item
~~~

## Campos principais

| Campo | Uso no app |
| --- | --- |
| `categories[].id` | Chave da sidebar e filtros. |
| `categories[].name` | Nome visual da categoria. |
| `categories[].color` | Cor de badge/card. |
| `categories[].skills[]` | Lista renderizada no centro da tela. |
| `skills[].id` | ID estável do skill dentro do repo. |
| `skills[].name` | Nome amigável para UI. |
| `skills[].descriptionPtBr` | Descrição principal em português. |
| `skills[].descriptionOriginal` | Descrição original do SKILL.md, útil para busca avançada. |
| `skills[].path` | Caminho dentro do repo para copiar. |
| `skills[].installable` | Se pode ser instalado pelo app. |
| `skills[].system` | Se é skill de runtime/sistema. |
| `skills[].sourceUrl` | Link de origem quando conhecido. |

## Estados de instalação

| Estado | Como calcular |
| --- | --- |
| `Not installed` | Pasta de destino não existe. |
| `Installed` | Pasta existe e contém `SKILL.md`. |
| `Update available` | Pasta existe, mas hash/versão local difere do item baixado. |
| `Invalid local install` | Pasta existe, mas falta `SKILL.md`. |
| `Not installable` | `installable = false`, normalmente skill de sistema/runtime. |

## Instalação segura

O app não deve executar comandos arbitrários. A instalação pode ser feita com operações de arquivo:

1. baixar o zip/tarball do GitHub na versão selecionada;
2. localizar cada `skills[].path`;
3. validar `SKILL.md`;
4. criar backup com timestamp se o destino já existir;
5. copiar arquivos para `~/.codex/skills/<id>` ou `~/.agents/skills/<id>`;
6. registrar logs simples por item.

## UI sugerida

- Sidebar com categorias, contagem e checkbox "selecionar tudo".
- Área central com cards de skills.
- Busca por nome, descrição e tags.
- Filtros por status: instalado, atualização disponível, não instalado.
- Drawer/modal de detalhes com descrição em pt-BR, descrição original, origem e caminho.
- Tela de progresso com log por skill.
- Botão "Abrir pasta instalada".

## Regenerar manifesto

~~~powershell
.\tools\generate-installer-manifest.ps1
~~~

Sempre rode depois de atualizar `docs/installed-skills.md` ou mexer no acervo de `skills/`.
