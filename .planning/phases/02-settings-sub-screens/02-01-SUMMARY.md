---
phase: 02-settings-sub-screens
plan: 01
subsystem: ui-widgets
status: complete
tags: [kivy, kivymd, ui-components, touchscreen, config-management]

requires:
  - 01-01-PLAN.md  # BaseDebugSubScreen pattern
  - monitoni.core.config  # ConfigManager for auto-save

provides:
  - NumpadDialog: On-screen numeric keypad with validation
  - SettingsCard: Grouped settings section with coral header
  - HoldButton: Hold-to-activate button with safe release detection
  - LiveStatusCard: Real-time hardware status polling with async support
  - NumpadField: Tap-to-edit numeric config field with auto-save
  - Config helpers: update_config_value, get_section_defaults, reset_section_to_defaults, show_confirm_dialog

affects:
  - 02-02-PLAN.md  # LED Control screen will use these widgets
  - 02-03-PLAN.md  # Relay Control screen will use these widgets
  - 02-04-PLAN.md  # Sensor Settings screen will use these widgets
  - 02-05-PLAN.md  # Audio Settings screen will use these widgets
  - All future settings sub-screens

tech-stack:
  added:
    - kivy.clock: Clock.schedule_interval for polling
    - asyncio: Support for async status callbacks
    - yaml: Read default.yaml for reset-to-defaults
  patterns:
    - touch.grab pattern: Ensures on_touch_up fires even if finger moves off button
    - Strong reference Clock scheduling: Lambda prevents weak reference garbage collection
    - Dot-notation config paths: Build nested dicts from "hardware.modbus.port" strings
    - Risky path confirmation: RISKY_PATHS list triggers confirmation dialogs

key-files:
  created:
    - monitoni/ui/debug_screens/widgets.py
  modified: []

decisions:
  - decision: Use touch.grab pattern for HoldButton
    rationale: Ensures release callback fires even if user's finger slides off button during hold
    alternatives: Simple collide_point check would miss finger-off-button releases

  - decision: Support both sync and async callbacks in LiveStatusCard
    rationale: Hardware status may come from async APIs (e.g., network requests)
    alternatives: Force all callbacks to be sync would limit flexibility

  - decision: RISKY_PATHS hardcoded list for confirmation dialogs
    rationale: Simple, explicit list of hardware-critical settings that need extra confirmation
    alternatives: Could use metadata in config schema, but adds complexity

  - decision: NumpadField combines display + NumpadDialog for convenience
    rationale: Most settings screens need this pattern, convenience widget reduces duplication
    alternatives: Each screen could manually wire MDTextField + NumpadDialog

  - decision: Config helpers use dot-notation paths
    rationale: Readable, concise syntax for nested config ("hardware.modbus.port")
    alternatives: Nested dict access would be more verbose

metrics:
  duration: ~2.5 minutes
  tasks: 2
  commits: 2
  files_created: 1
  lines_added: 787
  completed: 2026-02-06
---

# Phase 2 Plan 1: Shared Widget Library Summary

**One-liner:** Reusable widget library with numeric keypad, hold buttons, live status polling, auto-save config fields, and German-labeled confirmations for all settings screens.

## What Was Built

Created `monitoni/ui/debug_screens/widgets.py` containing the complete shared widget library that all 7 settings sub-screens will compose from.

### Components

**NumpadDialog:**
- Modal dialog with 3x4 numeric keypad (digits 0-9, decimal point, backspace)
- Touch-friendly 60dp button height for 400px wide touchscreen
- Validates input against min/max bounds before submission
- Coral accent OK button, near-black numpad keys
- German labels: "ABBRECHEN" (cancel), "OK" (confirm)

**SettingsCard:**
- MDCard subclass for grouping related settings
- Near-black background (0.12, 0.12, 0.12), 10dp rounded corners
- Coral accent section header
- Auto-height from child content via minimum_height binding
- add_content() method for adding child widgets

**HoldButton:**
- MDRaisedButton subclass for hold-to-activate hardware control
- touch.grab pattern ensures on_touch_up fires even if finger moves off button
- Visual feedback: changes to coral (#F24033) while held
- Safety: on_pre_leave cleanup prevents stuck activation if widget removed during hold
- Default 60dp height for touch-friendliness

**LiveStatusCard:**
- MDCard that polls hardware state and displays with color indicators
- Clock.schedule_interval with lambda for strong reference (avoids weak ref GC)
- Supports both sync and async status callbacks
- Returns list of (label, value, color) tuples for display
- Error handling: shows "ERROR" in red without crashing polling loop
- cleanup() and on_pre_leave() cancel scheduled events

**NumpadField:**
- Convenience widget combining label + tappable value display + NumpadDialog
- Opens numpad on tap, auto-saves to config via update_config_value
- Shows confirmation dialog for risky hardware paths (RISKY_PATHS list)
- Invokes optional on_value_changed callback after successful update
- 50dp height row layout: label (60%) + value button (40%)

**Config Helpers:**
- `update_config_value()`: Builds nested dict from dot-notation path, saves to local.yaml via ConfigManager.save_local(), returns (success, needs_confirmation) tuple
- `get_section_defaults()`: Reads default.yaml to get factory values for a config section
- `reset_section_to_defaults()`: Restores config section to defaults from default.yaml
- `show_confirm_dialog()`: Shows confirmation with German labels and coral OK button

**RISKY_PATHS list:**
```python
hardware.modbus.port
hardware.modbus.slave_address
hardware.gpio.door_sensor_pin
vending.motor.relay_channel
vending.motor.spindle_lock_relay
```

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 955a06f | Created NumpadDialog, SettingsCard, config helpers, show_confirm_dialog |
| 2 | a07bf95 | Created HoldButton, LiveStatusCard, NumpadField |

## Technical Implementation

### Touch Safety Pattern
HoldButton uses Kivy's touch.grab() API to ensure release detection:
```python
def on_touch_down(self, touch):
    if self.collide_point(*touch.pos):
        touch.grab(self)  # Receive on_touch_up even if finger moves
        self._holding = True
        # ...

def on_touch_up(self, touch):
    if touch.grab_current is self:
        touch.ungrab(self)
        # Release hardware
```

### Clock Polling Pattern
LiveStatusCard uses lambda to prevent weak reference garbage collection:
```python
# Strong reference via lambda
self._update_event = Clock.schedule_interval(
    lambda dt: self._update_status(),
    update_interval
)

# Cleanup
self._update_event.cancel()
```

### Async Support Pattern
LiveStatusCard detects async callbacks and handles properly:
```python
if inspect.iscoroutinefunction(self.get_status_callback):
    asyncio.create_task(self._update_status_async())
    # Updates UI via Clock.schedule_once from async context
else:
    status_items = self.get_status_callback()
    self._display_status(status_items)
```

### Config Path Pattern
Dot-notation paths converted to nested dicts:
```python
"hardware.modbus.port" -> {"hardware": {"modbus": {"port": value}}}
```

## Verification

All success criteria met:
- ✅ widgets.py exists with all 5 widget classes and 4 helper functions
- ✅ Coral accent (#F24033) and near-black (#1F1F1F) aesthetic applied consistently
- ✅ German labels: "ABBRECHEN", "OK" for user-facing dialogs
- ✅ HoldButton uses touch.grab pattern for safe release detection
- ✅ LiveStatusCard uses Clock.schedule_interval with strong reference
- ✅ Config auto-save via update_config_value with dot-notation paths
- ✅ Reset-to-defaults reads from default.yaml
- ✅ Python syntax valid (py_compile check passed)

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Ready to proceed:** Yes

All 7 settings sub-screens (02-02 through 02-08) can now be built using these shared components.

**Blocks nothing.**

**Usage pattern for screens:**
```python
from monitoni.ui.debug_screens.widgets import (
    NumpadField, HoldButton, LiveStatusCard, SettingsCard,
    show_confirm_dialog, reset_section_to_defaults
)

# Create settings card
card = SettingsCard("LED Brightness")

# Add numeric field with auto-save
brightness_field = NumpadField(
    label="Brightness",
    config_path="hardware.wled.brightness",
    config_manager=config_manager,
    allow_decimal=True,
    min_value=0.0,
    max_value=1.0
)
card.add_content(brightness_field)

# Add hold button for hardware test
test_btn = HoldButton(
    text="Test Relay 3",
    on_hold=lambda: hardware.relay_on(3),
    on_release_hold=lambda: hardware.relay_off(3)
)
card.add_content(test_btn)

# Add live status display
status = LiveStatusCard(
    title="Relay Status",
    get_status_callback=hardware.get_relay_status
)
card.add_content(status)
```

## Self-Check: PASSED

**Created files:**
- ✅ monitoni/ui/debug_screens/widgets.py exists

**Commits:**
- ✅ 955a06f exists (Task 1)
- ✅ a07bf95 exists (Task 2)
