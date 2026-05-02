---
name: "elementor-controls"
description: "Reference for Elementor widget controls: add_control, add_responsive_control, add_group_control, selectors (`{{WRAPPER}}`, `{{VALUE}}`), conditions, repeater patterns, and style/control tab structuring. Use when implementing or debugging Elementor control schemas."
---

# Elementor Controls

Use this skill when coding or debugging control definitions in `register_controls()`.

## Use for

- control type selection (`TEXT`, `SELECT`, `SLIDER`, `COLOR`, `MEDIA`, `REPEATER`, `ICONS`, etc.)
- group controls (Typography, Background, Border, Box Shadow)
- responsive controls
- conditional display (`condition`, `conditions`)
- selector templates with `{{WRAPPER}}` and value tokens

## Control structure baseline

1. Start section:
   - `$this->start_controls_section(...)`
2. Add controls:
   - `$this->add_control(...)`
   - `$this->add_responsive_control(...)`
   - `$this->add_group_control(...)`
3. End section:
   - `$this->end_controls_section()`

## High-value rules

- Always keep controls inside a section.
- Use `{{WRAPPER}}` in selectors for safe scope.
- Use proper value tokens by control type:
  - `{{VALUE}}` for text/color/select
  - `{{SIZE}}{{UNIT}}` for slider
  - `{{TOP}} {{RIGHT}} {{BOTTOM}} {{LEFT}}` patterns for dimensions
  - `{{URL}}` for media URL selectors
- Prefer `ICONS` over deprecated `ICON`.
- For grouped style controls, use `add_group_control()` with explicit `selector`.
- For repeater styling, rely on row `_id` and `elementor-repeater-item-<id>` class patterns.

## Debug checklist

- missing section wrappers
- wrong control constant/class
- malformed selector placeholders
- condition keys not matching control IDs
- responsive defaults missing `unit`
- deprecated APIs in old widget examples

