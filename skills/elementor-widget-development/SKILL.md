---
name: "elementor-widget-development"
description: "Develop custom Elementor widgets in WordPress using Widget_Base lifecycle, controls API, render/content_template patterns, and dependency methods. Use for real widget implementation and debugging."
---

# Elementor Widget Development

Use this skill for custom widget coding.

## Core lifecycle

- `get_name()`
- `get_title()`
- `get_icon()`
- `get_categories()`
- `register_controls()`
- `render()`
- `content_template()`

## Optional high-value methods

- `get_keywords()`
- `get_script_depends()`
- `get_style_depends()`
- `has_widget_inner_wrapper()`
- `is_dynamic_content()`

## Implementation baseline

1. Register widget on `elementor/widgets/register`.
2. Keep control schema clean and grouped by content/style concerns.
3. Use scoped selectors (`{{WRAPPER}}`) in style controls.
4. Keep rendering defensive:
   - sanitize output
   - handle empty settings
5. Keep editor template coherent with PHP render output.

## Debug checklist

- widget not appearing in panel (registration/category mismatch)
- control values not applying (selector/value token issues)
- editor/frontend mismatch (`content_template()` drift)
- missing asset handles from `get_script_depends()`/`get_style_depends()`

