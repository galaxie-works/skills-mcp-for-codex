---
name: "elementor-addon-architecture"
description: "Design universal Elementor addon foundations in WordPress: bootstrap boundaries, compatibility gates, manager registration maps, and asset loading policy. Use for plugin architecture decisions before widget implementation."
---

# Elementor Addon Architecture

Use this skill before coding widgets when addon foundation is unclear.

## Trigger scope

- addon bootstrap design
- initialization order and failure behavior
- registration surface mapping
- central asset policy

## Workflow

1. Define contract:
   - supported WP/PHP/Elementor versions
   - dependency and failure policy
2. Build startup phases:
   - WordPress-safe boot
   - Elementor wiring only after compatibility passes
3. Map managers explicitly:
   - widgets
   - controls
   - dynamic tags
   - finder
   - categories
4. Set asset policy:
   - central handle registration
   - per-widget dependency consumption
5. Validate behavior:
   - deterministic boot path
   - no partial initialization

## Registration map

- widgets -> `elementor/widgets/register`
- controls -> `elementor/controls/register`
- dynamic tags -> `elementor/dynamic_tags/register`
- finder -> `elementor/finder/register`
- categories -> `elementor/elements/categories_registered`

## Guardrails

- never instantiate Elementor classes before compatibility gate
- never mix bootstrapping and feature logic in the same file
- prefer modern manager `register()` APIs
- provide clear admin notices on incompatibility

