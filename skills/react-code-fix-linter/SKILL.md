---
name: react-code-fix-linter
description: Use when fixing React linting, formatting, or pre-commit CI readiness issues. Runs repository-specific formatting and lint commands, focuses on changed files when supported, and reports remaining manual fixes.
metadata:
  source: https://mcpmarket.com/tools/skills/react-code-fix-linter
  alternate_source: https://eliteai.tools/agent-skills/fix-25
---

# React Code Fix & Linter

Use this skill when a React project has formatting problems, lint errors, or needs a final pre-commit quality pass.

## Workflow

1. Inspect the repository scripts before running commands:
   - `package.json`
   - lockfile/package manager
   - lint/format scripts
   - project conventions for changed-file formatting
2. Prefer the repository's own commands over generic defaults.
3. If the project defines them, run:
   - `yarn prettier`
   - `yarn linc`
4. If those commands do not exist, choose the closest project-native equivalents:
   - `npm run format`, `pnpm format`, or `yarn format`
   - `npm run lint`, `pnpm lint`, or `yarn lint`
   - `npm run typecheck`, `pnpm typecheck`, or `yarn typecheck`
5. Fix actionable errors directly.
6. Report remaining manual fixes clearly, with file paths and commands already tried.

## Guardrails

- Do not invent formatting rules. Use the repo's configured Prettier, ESLint, TypeScript, and framework settings.
- Do not run destructive cleanup commands.
- Do not format the whole repository if the project provides a changed-files-only command.
- Do not hide lint failures. If something remains, state exactly what failed and why.

## Output

Summarize:

- commands run;
- files changed;
- errors fixed;
- remaining failures, if any;
- whether the project appears ready for commit or CI.
