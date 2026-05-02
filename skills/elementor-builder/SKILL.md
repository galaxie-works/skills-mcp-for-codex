---
name: "elementor-builder"
description: "Execution-first Elementor page building workflow: container/flex layout strategy, global style system, responsive passes, and JSON/page-structure sanity checks. Use when creating or restructuring Elementor pages end-to-end."
---

# Elementor Builder

Use this skill when the user wants to build or restructure pages, not only code plugin internals.

## Execution posture

- build first, comment later
- structure before cosmetics
- global styles before per-widget overrides
- mobile/tablet sanity pass before finish

## Workflow

1. Define page goal and sections.
2. Create container/flex skeleton.
3. Apply global tokens (colors, typography, buttons).
4. Fill content modules (heading, text, image, button, etc.).
5. Run responsive pass:
   - spacing
   - hierarchy
   - overflow
6. Validate Elementor data model sanity:
   - IDs unique
   - widget nesting valid
   - no orphan nodes

## Guardrails

- avoid style duplication across widgets
- avoid hardcoding everything in widget-level styles
- avoid desktop-only composition
- keep component naming and section labels intentional

