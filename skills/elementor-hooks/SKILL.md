---
name: "elementor-hooks"
description: "Elementor lifecycle and extension hook map for PHP and JS: init/registration hooks, render filters, frontend/editor enqueue hooks, control injection hooks, and common Pro hooks. Use when wiring behavior through actions/filters rather than direct widget edits."
---

# Elementor Hooks

Use this skill for hook-first Elementor customization.

## Use for

- lifecycle gates (`elementor/loaded`, `elementor/init`)
- manager registration hooks
- render interception and output filters
- frontend/editor enqueue lifecycle
- control injection via section hooks
- JS hooks in frontend/editor integrations

## Core registration hooks

- `elementor/widgets/register`
- `elementor/controls/register`
- `elementor/dynamic_tags/register`
- `elementor/finder/register`
- `elementor/elements/categories_registered`

## Render and output hooks

- `elementor/widget/render_content` (filter widget HTML)
- `elementor/frontend/before_render`
- `elementor/frontend/after_render`
- element-type scoped render hooks where needed

## Control injection hooks

- `elementor/element/before_section_start`
- `elementor/element/after_section_start`
- `elementor/element/before_section_end`
- `elementor/element/after_section_end`

Use stack/section-targeted variants for precise injections.

## Asset lifecycle hooks

- frontend register/enqueue before/after hooks
- editor register/enqueue before/after hooks
- preview enqueue hooks

## Guardrails

- do not hook features before `elementor/loaded`
- keep hooks idempotent and avoid duplicate registration
- avoid broad global filters when a narrower hook exists
- for Pro hooks, always degrade gracefully if Pro is inactive

