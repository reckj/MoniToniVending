---
created: 2026-02-06T14:15
title: Create design system for centralized UI styling
area: ui
files:
  - monitoni/ui/customer_screen.py
  - monitoni/ui/debug_screen.py
  - monitoni/ui/debug_screens/base.py
  - monitoni/ui/debug_screens/menu_screen.py
---

## Problem

UI styling is currently scattered across multiple Python files with hardcoded values:
- Colors defined inline (e.g., `md_bg_color = (0.95, 0.25, 0.2, 1)`)
- Font sizes, heights, padding all embedded in widget constructors
- Changing the look requires editing multiple files
- No single source of truth for the visual design

This makes rapid iteration on the visual design slow and error-prone.

## Solution

Create a centralized design system, options:

1. **Python module approach** (`ui/theme.py`):
   - Define color palette, typography scale, spacing values as constants
   - Import and reference in all UI files
   - Kivy-native, no external dependencies

2. **YAML/JSON config approach**:
   - Design tokens in a config file
   - Load at app startup
   - Easy for non-developers to tweak

3. **KV language approach**:
   - Use Kivy's `.kv` files for styling
   - Separate structure from style
   - Native Kivy pattern

TBD: Choose approach based on team preference and iteration speed needs.
