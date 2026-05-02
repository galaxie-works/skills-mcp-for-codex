# codex-skills-for-galaxie

Faithful Git mirror of the skills currently installed on this machine.

## Source Of Truth

This repository now mirrors the local Codex installation instead of a smaller curated subset.

Source folders:

- `C:\Users\consa\.codex\skills`
- `C:\Users\consa\.codex\superpowers\skills`

## Current Inventory

- `1123` top-level installed skills
- `5` installed system skills inside `skills/.system`
- `1128` installed skill definitions total
- `14` installed superpowers
- `5` configured MCP servers
- `1147` documented capabilities total

## Repo Layout

- [skills](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\skills): mirrored skill folders from the local Codex install, including `.system`
- [superpowers-skills](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\superpowers-skills): mirrored superpower folders from the local Codex install
- [mcp](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\mcp): snapshot of configured MCP servers from the local Codex config
- [docs/installed-skills.md](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\docs\installed-skills.md): full index of installed skills with path, description, and why each capability matters
- [docs/installed-superpowers.md](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\docs\installed-superpowers.md): full index of installed superpowers with path, description, and why they matter
- [docs/installed-mcps.md](G:\OneDrive - Galaxie Works Ltd\Galaxie Works Ltd\About Galaxie\Development\codex-skills-for-galaxie\docs\installed-mcps.md): inventory of configured MCP servers, transports, endpoints, and safe notes

## Why This Exists

The goal is continuity.

You mentioned needing the full skill picture documented so you can keep moving without depending on partial thread context. This repo now serves that purpose:

- exact snapshot of what is installed locally
- searchable Git history for skills and superpowers
- documentation of what each installed capability does
- easier handoff into future planning and automation work

## Important Note

This repo is now intentionally broader than the earlier curated subset. That means skills related to WordPress, Elementor, content writing, SEO, product operations, design, debugging, and many other areas are included whenever they are present in the local Codex installation.

## Updating The Mirror

When the local skill installation changes, refresh this repository from:

- `C:\Users\consa\.codex\skills`
- `C:\Users\consa\.codex\superpowers\skills`

Then regenerate the inventory docs so the documentation stays faithful to the machine state.

For the canonical source map of where to check updates, open [skill-update-sources.md](./skill-update-sources.md).
