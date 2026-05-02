---
name: "elementor-development"
description: "Build and maintain Elementor addons/widgets in WordPress with correct bootstrap, compatibility checks, modern manager registration hooks, controls/rendering patterns, and asset dependency wiring. Use for extension-level Elementor engineering."
---

# Elementor Development

Use this skill for extension-level Elementor engineering: addon bootstrap, registration lifecycle, widget class structure, and compatibility-safe initialization.

## Trigger Scope

- addon/plugin architecture
- compatibility gates (WordPress/PHP/Elementor)
- manager wiring (widgets, controls, dynamic tags, finder, categories)
- widget class skeleton and render lifecycle
- deprecation-safe APIs and registration methods

## Core Workflow

1. Define runtime contract:
   - minimum PHP version
   - minimum Elementor version
   - failure behavior (clear admin notice, no partial boot)
2. Build startup boundaries:
   - `plugins_loaded` for addon bootstrap
   - `did_action('elementor/loaded')` gate before Elementor classes
3. Use a central plugin class and register managers with current hooks:
   - `elementor/widgets/register`
   - `elementor/controls/register`
   - `elementor/dynamic_tags/register`
   - `elementor/finder/register`
   - `elementor/elements/categories_registered`
4. Keep assets policy split:
   - register handles centrally
   - consume dependencies per widget via `get_script_depends()` / `get_style_depends()`
5. Implement widget lifecycle consistently:
   - `register_controls()`
   - `render()`
   - `content_template()`
6. Validate no deprecated APIs are used.

## Recommended Layout

```text
elementor-addon/
  elementor-addon.php
  includes/
    plugin.php
    widgets/
    controls/
    dynamic-tags/
    finder/
  assets/
    js/
    css/
    images/
```

## Guardrails

- Always include `defined('ABSPATH') || exit;`
- Never touch Elementor classes before compatibility checks pass
- Prefer `register()` / `unregister()` manager methods
- Prefer current hooks over legacy aliases
- Keep bootstrap logic separate from feature logic
- Use localized strings for all user-visible labels
- Avoid global enqueue unless truly shared

## Common mistakes to avoid

- Using old `elementor/widgets/widgets_registered` instead of `elementor/widgets/register`
- Calling `register_widget_type()` instead of manager `register()`
- Skipping `did_action('elementor/loaded')` checks
- Forgetting plugin header dependency (`Requires Plugins: elementor`)

## Quick skeleton

```php
defined('ABSPATH') || exit;

add_action('plugins_loaded', static function () {
    \Vendor\Addon\Plugin::boot();
});
```

## Skill Routing

- if task is mostly control APIs and selectors: use `elementor-controls`
- if task is mostly hook orchestration/lifecycle filters: use `elementor-hooks`
- if task is mostly persisted page JSON/content operations: use `elementor-content`
- if task is mostly addon foundation/boot boundaries: use `elementor-addon-architecture`

## Note

This skill was hardened from cross-source Elementor skill references on SkillsMP and your installed stack, focusing on practical reliability for Codex execution.
