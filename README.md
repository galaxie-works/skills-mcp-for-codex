# skills-mcp-for-codex

Faithful Git mirror of every Codex skill and MCP snapshot consolidated on this machine.

## Source Of Truth

This repository mirrors the canonical global Codex skill folder. Any skill discovered in workspace `.agents\skills`, `.claude\skills`, exports, or older mirrors should be consolidated here first:

- `C:\Users\consa\.codex\skills`
- `C:\Users\consa\.codex\superpowers\skills`

## Current Inventory

- `1207` top-level skills in `skills/`
- `5` system skills inside `skills/.system`
- `1210` documented skill definitions total
- `14` installed superpowers
- `1` MCP snapshot files
- `1225` documented capabilities total

## Repo Layout

- [skills](./skills): mirrored skill folders from the local Codex global install, including `.system`
- [superpowers-skills](./superpowers-skills): mirrored superpower folders from the local Codex install
- [mcp](./mcp): snapshot of configured MCP servers from the local Codex config
- [docs/installed-skills.md](./docs/installed-skills.md): full index of installed skills with path, description, and why each capability matters
- [docs/installed-superpowers.md](./docs/installed-superpowers.md): full index of installed superpowers with path and description
- [docs/installed-mcps.md](./docs/installed-mcps.md): inventory of configured MCP servers, transports, endpoints, and safe notes
- [skill-update-sources.md](./skill-update-sources.md): where to check for future skill updates

## Operating Rule

`C:\Users\consa\.codex\skills` is the canonical skill library. Do not leave usable skills only in workspace `.agents\skills`, `.claude\skills`, or temporary exports. Consolidate them into the global folder, then refresh this mirror and regenerate the docs.

## Updating The Mirror

1. Consolidate all local skill roots into `C:\Users\consa\.codex\skills`.
2. Remove generated cache files such as `__pycache__` and `.pyc`.
3. Mirror the global skills folder into `skills/`.
4. Regenerate `docs/installed-skills.md` so descriptions stay current.
5. Commit and push to `galaxie-works/skills-mcp-for-codex`.
