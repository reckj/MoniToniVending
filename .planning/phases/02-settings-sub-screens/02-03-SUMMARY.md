---
phase: 02-settings-sub-screens
plan: 03
subsystem: ui
tags: [kivy, kivymd, hardware-testing, led, gpio, sensors, touchscreen, settings]

# Dependency graph
requires:
  - phase: 02-01
    provides: Shared widget library (NumpadField, SettingsCard, LiveStatusCard, HoldButton, config helpers)
provides:
  - LED configuration screen with brightness, color testing, zone mapping, and animation previews
  - Sensor configuration screen with GPIO settings and live door state monitoring
  - Hardware testing interfaces for commissioning new machines
affects: [02-04, 02-05, setup-wizard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Async pattern for hardware calls via asyncio.create_task()"
    - "Clock polling pattern for real-time sensor data (200ms updates)"
    - "Color-coded visual feedback for hardware states"
    - "Risky config path confirmations for GPIO settings"

key-files:
  created:
    - monitoni/ui/debug_screens/led_screen.py
    - monitoni/ui/debug_screens/sensor_screen.py
  modified: []

key-decisions:
  - "LED brightness stored in led.animations.idle.brightness path (no direct hardware.wled.brightness field)"
  - "IP address input via text dialog instead of numpad (string vs numeric)"
  - "Zone mapping uses direct pixel range (start/end) editable per-level"
  - "Sensor door status prominently displayed with H3 font and color-coded background"
  - "Clock.schedule_interval for 200ms sensor polling instead of LiveStatusCard (need sync callback)"
  - "GPIO pin, pull mode, and active state all trigger confirmation dialogs (RISKY_PATHS)"

patterns-established:
  - "Large status displays for critical hardware states (door sensor)"
  - "Test buttons alongside configuration (zone tests, individual and all-zones)"
  - "Reset-to-defaults restores factory config from default.yaml"
  - "Cleanup pattern: cancel async tasks and Clock events in on_pre_leave"

# Metrics
duration: 3min
completed: 2026-02-06
---

# Phase 2 Plan 3: LED and Sensor Settings Screens Summary

**LED and sensor testing screens with zone mapping, animation previews, and live 200ms door monitoring for machine commissioning**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-06T14:51:27Z
- **Completed:** 2026-02-06T14:54:53Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- LED screen provides full WLED configuration (pixel count, IP, FPS), brightness control, color testing (6 presets + custom picker), zone mapping with per-level tests, and animation previews
- Sensor screen provides GPIO configuration (pin, pull mode, active state) with real-time door monitoring at 200ms update rate
- Zone mapping allows operators to verify all LED zones light up correctly during commissioning
- Live door status displayed prominently with H3 font and color-coded background (green=closed, coral=open, red=error, gray=disconnected)
- All settings auto-save to local.yaml immediately via ConfigManager
- Reset-to-defaults buttons restore factory config from default.yaml

## Task Commits

Each task was committed atomically:

1. **Task 1: Build LEDSettingsScreen** - `4bec8f9` (feat)
2. **Task 2: Build SensorSettingsScreen** - `2065bea` (feat)

**Plan metadata:** _(will be added in final commit)_

## Files Created/Modified

- `monitoni/ui/debug_screens/led_screen.py` - LED configuration and testing screen with WLED connection settings, brightness control, color test buttons (Red, Green, Blue, White, Yellow, Off) + custom color picker, zone mapping editable per-level with individual zone tests, animation preview buttons for all config animations, live status card, and reset to defaults
- `monitoni/ui/debug_screens/sensor_screen.py` - Sensor configuration and testing screen with GPIO pin config via numpad, pull/active selectors with confirmation dialogs, enabled toggle, prominent live door status updating every 200ms with color-coded display, sensor info summary, and reset to defaults

## Decisions Made

**LED brightness storage:** Brightness is stored in `led.animations.idle.brightness` path (0.0-1.0 float) rather than a dedicated `hardware.wled.brightness` field, since the config model doesn't have a direct brightness field at the WLED level.

**IP address input method:** Used text dialog for IP address input instead of numpad since IP addresses are strings, not pure numeric values.

**Zone mapping approach:** Zones are editable as direct pixel ranges (start/end) per level, stored in `led.zones` as list of `[start, end]` pairs. Individual "Test" buttons light up each zone in green for 2 seconds; "Test All Zones" cycles through all zones with different colors.

**Sensor polling pattern:** Used `Clock.schedule_interval` at 200ms for door state polling instead of LiveStatusCard because we need fine-grained control over the polling loop and error handling. The async pattern (`_poll_door` → `_async_poll_door` → `Clock.schedule_once` for UI update) ensures thread-safe UI updates.

**GPIO confirmations:** GPIO pin, pull mode, and active state all trigger confirmation dialogs since they're in RISKY_PATHS (hardware-critical settings).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

LED and sensor screens complete. Ready for next settings screens (02-04: Relay and Motor, 02-05: Network and Stats).

These screens provide essential hardware testing interfaces for commissioning new machines:
- Operators can verify all LED zones light up correctly
- Operators can confirm door sensor responds properly
- Zone mapping can be adjusted on-site for different LED strip configurations

## Self-Check: PASSED

All files created and all commits verified.

---
*Phase: 02-settings-sub-screens*
*Completed: 2026-02-06*
