# Phase 04 Plan 02: Maintenance Mode + Integration Summary

**One-liner:** Maintenance mode toggle with full-screen display screen, consolidated app routing, and debug menu wiring for both Phase 4 screens

---

## Performance

- **Duration:** Multiple sessions (with bug fixes and user testing)
- **Completed:** 2026-03-23
- **Tasks:** 4/4 (100%)
- **Deviations:** 3 (see below)

---

## What Was Accomplished

### Objective
Built the Maintenance Mode screen (toggle + machine status), integrated maintenance check into customer screen routing, created a full-screen MaintenanceDisplayScreen, and wired both Phase 4 screens (QR Management + Maintenance) into the debug menu.

### Delivered
1. **Maintenance Screen** - Debug sub-screen with:
   - MDSwitch toggle for maintenance mode with red thumb/track when active
   - LiveStatusCard showing real-time hardware health (relay, LED, door, audio)
   - Config persistence via `update_config_value("system.maintenance_mode", ...)`

2. **MaintenanceDisplayScreen** - Full-screen customer-facing display:
   - Coral "!" icon with configurable maintenance message
   - "Please try again later" subtitle
   - Hidden 5-tap debug access in top-right corner (same pattern as customer screen)
   - Reads `system.maintenance_message` from config on each `on_enter()`

3. **App Routing Consolidation** - Single routing point:
   - `app.switch_to_customer()` delegates to `_go_to_customer_or_maintenance()`
   - App startup checks maintenance mode, starts on maintenance display if active
   - Customer screen no longer checks maintenance mode itself (moved to app level)

4. **Debug Menu Integration** - Both screens wired:
   - "QR Codes" and "Wartung & Status" appear in debug menu
   - Both screens registered in DebugScreen sub_screen_classes

---

## Task Commits

| Task | Description | Commits | Files |
|------|-------------|---------|-------|
| 1 | Create Maintenance Screen + config defaults | 946345d | maintenance_screen.py, default.yaml |
| 2 | Wire screens into debug menu | b489819 | __init__.py, menu_screen.py, debug_screen.py |
| 3 | Integrate maintenance check into customer screen | 6217396 | customer_screen.py |
| 4 | Checkpoint fixes + MaintenanceDisplayScreen | 89483bb, 6db1109, 730cedc | app.py, customer_screen.py, maintenance_screen.py, maintenance_display_screen.py |

---

## Files Created

- `monitoni/ui/debug_screens/maintenance_screen.py` - Maintenance toggle + machine status
- `monitoni/ui/maintenance_display_screen.py` - Full-screen maintenance display (149 lines)

---

## Files Modified

- `monitoni/ui/app.py` - Added MaintenanceDisplayScreen, consolidated routing
- `monitoni/ui/customer_screen.py` - Removed maintenance check (moved to app routing)
- `monitoni/ui/debug_screens/__init__.py` - Added exports for new screens
- `monitoni/ui/debug_screens/menu_screen.py` - Added menu entries
- `monitoni/ui/debug_screen.py` - Registered sub-screens
- `config/default.yaml` - Added maintenance_mode and maintenance_message defaults

---

## Decisions Made

1. **Full-screen MaintenanceDisplayScreen** - Instead of just blocking product selection, maintenance mode replaces the entire customer screen with a dedicated display. Clearer for customers.

2. **App-level routing** - `_go_to_customer_or_maintenance()` is the single routing point, replacing the per-button check in customer_screen. Simpler and catches all entry paths.

3. **bind(active=callback) for MDSwitch** - KivyMD 1.2.0 reliable dispatch pattern. `bind(on_active=...)` was unreliable.

4. **Red thumb/track colors** - `thumb_color_active = ERROR_RED`, `track_color_active = [1, 0.3, 0.3, 0.5]` for visual danger signal when maintenance active.

5. **MDSwitch alignment deferred** - 12dp right padding is "good enough"; thumb slightly overflows card border. Deferred to design system overhaul.

---

## Deviations from Plan

### 1. Full-screen display instead of status message
- **Plan:** Customer screen blocks product selection with orange status message
- **Actual:** Created dedicated MaintenanceDisplayScreen that replaces customer screen entirely
- **Reason:** User feedback during testing — a status message wasn't clear enough for customers

### 2. App-level routing instead of customer screen check
- **Plan:** Check maintenance mode in `_on_level_selected` handler
- **Actual:** Routing consolidated in `app._go_to_customer_or_maintenance()`
- **Reason:** Single routing point catches all entry paths (startup, screen switches)

### 3. MDSwitch binding pattern
- **Plan:** Use `bind(on_active=...)` with Clock.schedule_once
- **Actual:** Use `bind(active=...)` directly
- **Reason:** `on_active` was unreliable in KivyMD 1.2.0; `active` property binding works consistently

---

## Issues Encountered

- MDSwitch `bind(on_active=...)` unreliable dispatch in KivyMD 1.2.0 — switched to `bind(active=...)`
- SystemConfig pydantic model needed maintenance fields added (fix commit 6db1109)
- MDSwitch thumb overflows card border at right edge — accepted cosmetic debt

---

## Metadata

**Phase:** 04-maintenance-features
**Plan:** 02
**Subsystem:** ui-maintenance, app-routing
**Tags:** maintenance-mode, mdswitch, kivymd, routing, touchscreen

**Requires:**
- Phase 01: BaseDebugSubScreen, SettingsCard, LiveStatusCard
- Phase 02: Widget library patterns
- Plan 04-01: QR Management Screen

**Provides:**
- Maintenance mode toggle with config persistence
- Full-screen maintenance display for customers
- Consolidated app routing (customer vs maintenance)
- Complete debug menu with all Phase 4 screens

**Affects:**
- Phase 05: MDSwitch alignment cosmetic debt
- Future: Design system overhaul for consistent switch styling

**Key Files:**
- Created: monitoni/ui/maintenance_display_screen.py
- Created: monitoni/ui/debug_screens/maintenance_screen.py
- Modified: monitoni/ui/app.py, monitoni/ui/customer_screen.py

**Key Decisions:**
- Full-screen MaintenanceDisplayScreen over inline status message
- App-level routing via _go_to_customer_or_maintenance()
- bind(active=) over bind(on_active=) for MDSwitch in KivyMD 1.2.0

---

## Self-Check: PASSED

All features verified through user testing.
Phase 4 functionally complete.
