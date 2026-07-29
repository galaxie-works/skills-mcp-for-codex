# Skill update check - 2026-07-29

## Resultado executivo

- Update aplicado automaticamente: `shadcn`.
- Origem do update: `npx skills update -g -y`.
- Local atualizado pela CLI: `C:\Users\consa\.agents\skills\shadcn`.
- Sincronizacao manual feita para o canone global do Codex: `C:\Users\consa\.codex\skills\shadcn`.
- Sincronizacao manual feita para o mirror do repo: `skills/shadcn`.
- `skillfish update --json` nao encontrou updates pendentes.

## Evidencias

```text
npx skills update -g -y
Found 1 global update(s)
Updating shadcn...
Updated shadcn
Updated 1 skill(s)
```

```text
npx skillfish update --json
{
  "success": true,
  "exit_code": 0,
  "errors": [],
  "outdated": [],
  "updated": []
}
```

Hash final do `SKILL.md` do `shadcn`, alinhado entre `.agents`, `.codex` e repo:

```text
E39871B64B1BA34F1AEFC50FFEA1B162C5A0750BC42A9BA54282AC503534429B
```

## Arquivos alterados no mirror

- `skills/shadcn/SKILL.md`
- `skills/shadcn/cli.md`
- `skills/shadcn/evals/evals.json`
- `skills/shadcn/mcp.md`
- `skills/shadcn/registry.md`
- `skills/shadcn/rules/chat.md`
- `skills/shadcn/rules/composition.md`
- `skills/shadcn/rules/styling.md`

## Limites da checagem automatica

A CLI `skills list -g --json` reconheceu `1041` skills, mas apenas `2` estavam com `sourceUrl` formal. Isso significa que a maior parte dos skills instalados foi importada/copied/mirrada sem metadata suficiente para update automatico confiavel.

Resumo:

- Skills reconhecidos pela CLI: `1041`
- Skills com origem rastreavel pela CLI: `2`
- Skills sem origem formal: `1039`
- URLs unicas no `skill-update-sources.md`: `131`
- Repos GitHub derivados das fontes: `57`
- Repos GitHub acessiveis: `53`
- Repos GitHub privados/removidos/renomeados: `4`

## Fontes com alerta

O comando `npx skills update -g -y` avisou que este skill parece ter sido removido upstream:

- `ln-611-docs-structure-auditor` de `levnikolaevich/claude-code-skills`

Nao foi removido localmente porque o modo nao interativo pulou delecao, que e o comportamento seguro.

Repos derivados do inventario que nao responderam via GitHub CLI:

- `404kidwiz/claude-supercode-skills`
- `eddiebe147/claude-settings`
- `peixotorms/odinlayer-skills`
- `supercent-io/skills-template`

Esses podem ter sido removidos, renomeados, privados ou exigirem autenticacao diferente.

## Problemas de validacao encontrados

A CLI pulou alguns `SKILL.md` por frontmatter invalido ou ausente:

- `davila7-claude-code-templates_149a7f65__ai-research__data-processing-ray-data`: YAML invalido em `dependencies: [ray[data], ...]`.
- `davila7-claude-code-templates_149a7f65__ai-research__distributed-training-ray-train`: YAML invalido em `dependencies: [ray[train], ...]`.
- `davila7-claude-code-templates_149a7f65__development__agirails-agent-payments`: falta `description`.
- `davila7-claude-code-templates_149a7f65__scientific__scholar-evaluation`: faltam `name` e `description`.
- `davila7-claude-code-templates_149a7f65__video__motion-canvas`: YAML invalido com dependencia iniciando em `@`.
- `neon-postgres`: falta `description`.

Esses problemas aparecem tanto em `.claude\skills` quanto em `.codex\skills`.

## Proximo passo recomendado

Para transformar a busca de updates em rotina confiavel, precisamos enriquecer cada skill do repo com metadata de origem:

```yaml
source:
  type: github
  repo: owner/repo
  path: path/to/skill
  ref: main
  installed_commit: <commit>
```

Sem isso, conseguimos atualizar os poucos instalados via CLI, mas nao comparar automaticamente os 1000+ skills copiados de fontes historicas.
