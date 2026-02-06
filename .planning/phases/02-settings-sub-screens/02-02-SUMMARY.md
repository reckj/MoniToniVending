---
phase: 02-settings-sub-screens
plan: 02
subsystem: ui-settings
status: complete
tags: [kivy, kivymd, relay-control, motor-control, hardware-testing, modbus, touchscreen]

requires:
  - phase: 02-01
    provides: Shared widget library (NumpadField, HoldButton, LiveStatusCard, SettingsCard)

provides:
  - RelaySettingsScreen: Modbus config, 32 relay test buttons, cascade test, door lock mapping, live status
  - MotorSettingsScreen: Motor timing config, full sequence test, individual component tests, timing visualization, live status

affects:
  - 02-03-PLAN.md  # LED settings screen
  - 02-04-PLAN.md  # Sensor settings screen
  - 02-05-PLAN.md  # Audio settings screen
  - Future hardware testing workflows

tech-stack:
  added: []
  patterns:
    - Cascade test pattern: Sequential hardware activation with hold-to-cancel
    - Async motor sequence: Spindle open -> delay -> motor on -> motor off -> delay -> spindle close
    - Door lock channel list editing: List mutation with confirmation dialogs
    - Safety cleanup pattern: on_pre_leave deactivates all hardware before screen exit

key-files:
  created:
    - monitoni/ui/debug_screens/relay_screen.py
    - monitoni/ui/debug_screens/motor_screen.py
  modified: []

decisions:
  - decision: Port field uses simple tappable button showing current value
    rationale: Port is a string path (/dev/ttySC0) not a number - operator rarely changes this, simple display is sufficient
    alternatives: Could add text input dialog, but adds complexity for rare operation

  - decision: Door lock channel editing uses custom list mutation logic
    rationale: Config uses list of relay channels, need to rebuild list when individual level changes
    alternatives: Could use nested config paths but list approach matches default.yaml structure

  - decision: Cascade test runs 100ms per relay (3.2 seconds for full cycle)
    rationale: Fast enough to verify all relays quickly, slow enough to visually confirm activation
    alternatives: Could make configurable, but fixed timing keeps UI simple

  - decision: Motor test uses async sequence with sleep delays
    rationale: Spindle must open before motor starts (safety), delays must be precise
    alternatives: Could use Clock.schedule_once but async/await is clearer for sequential steps

  - decision: Individual motor/spindle test buttons for diagnostic troubleshooting
    rationale: Operators need to test components separately to isolate failures
    alternatives: Could omit but would reduce diagnostic capability

metrics:
  duration: 2 min
  tasks: 2
  commits: 2
  files_created: 2
  lines_added: 796
  completed: 2026-02-06
---

# Phase 2 Plan 2: Relay and Motor Settings Screens Summary

**One-liner:** Relay screen with 32 hold-to-activate test buttons, cascade test, and Modbus config; Motor screen with full spindle sequence, timing parameters, and safety cleanup.

## What Was Built

Created two critical hardware testing screens providing full configuration and diagnostic capabilities for relay and motor subsystems.

### RelaySettingsScreen

**Modbus Configuration Card:**
- Port display (string field, tap to view info)
- Baudrate (1200-115200, numeric)
- Slave address (1-247, numeric)
- Timeout (0.1-10.0s, decimal)
- All Modbus settings trigger confirmation dialogs (risky hardware changes)

**Relay Testing Card:**
- "Alle testen (Kaskade)" button: Activates relays 1-32 sequentially (100ms each) while held
- 32 individual relay buttons (R1-R32) in 4x8 grid
- Hold-to-activate pattern: relay ON while held, OFF on release
- Touch-friendly 50dp button height

**Door Lock Mapping Card:**
- One numpad field per vending level (1-10) for relay channel assignment
- "Entsperr-Dauer" (unlock duration) field: 5-120 seconds
- Custom list mutation logic to update relay_channels array
- Confirmation dialogs for channel changes (risky paths)

**Live Status Card:**
- Shows motor relay (R1), spindle relay (R12), and first 3 door locks
- Green for ON, dim for OFF, red for ERROR
- Updates every 1.0 second
- Gracefully handles disconnected relay controller

**Safety:**
- on_pre_leave stops cascade test and deactivates all relays
- Cascade test cancellable by releasing button

### MotorSettingsScreen

**Motor Configuration Card:**
- Motor relay channel (1-32, with confirmation)
- Spindle lock relay (1-32, with confirmation)
- Spin delay (50-5000ms)
- Spindle pre-delay (0-2000ms)
- Spindle post-delay (0-2000ms)
- All fields auto-save and update timing visualization

**Motor Test Card:**
- "Motor testen" button (80dp, prominent): Full sequence with hold-to-activate
  - Sequence: Spindle open -> wait pre-delay -> motor ON (while held) -> motor OFF -> wait post-delay -> spindle close
- "Spindel-Schloss testen" button: Direct spindle relay control
- "Motor direkt testen" button: Direct motor relay control (bypasses spindle)
- Individual tests help diagnose component failures

**Timing Visualization Card:**
- 6-step sequence display showing current timing values
- Updates dynamically when timing parameters change
- Format:
  ```
  Sequenz:
  1. Spindel öffnen (Relay 12)
  2. Warte 200ms
  3. Motor AN (Relay 1) - solange gehalten
  4. Motor AUS
  5. Warte 100ms
  6. Spindel schließen
  ```

**Live Status Card:**
- Motor relay (R1) and spindle relay (R12) current states
- Green for ON, dim for OFF, red for ERROR
- Updates every 0.5 seconds

**Safety:**
- on_pre_leave deactivates both motor and spindle relays
- Motor test stop sequence properly shuts down (motor off -> delay -> spindle close)
- Scheduled events tracked and cancelled on release

## Task Commits

Each task was committed atomically:

1. **Task 1: Build RelaySettingsScreen** - `3aa5edc` (feat)
2. **Task 2: Build MotorSettingsScreen** - `56e87d2` (feat)

**Plan metadata:** (to be committed after SUMMARY creation)

## Files Created/Modified

**Created:**
- `monitoni/ui/debug_screens/relay_screen.py` (415 lines) - Full relay testing and configuration screen
- `monitoni/ui/debug_screens/motor_screen.py` (381 lines) - Motor timing configuration and safe test functions

**Modified:**
None

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-06T14:51:34Z
- **Completed:** 2026-02-06T14:54:05Z
- **Tasks:** 2/2
- **Files created:** 2

## Decisions Made

1. **Port field as simple display button** - String path (/dev/ttySC0) rarely changes, operator just needs to view current value. Full text editing would add complexity for minimal benefit.

2. **Door lock channel list mutation logic** - Config stores relay_channels as list. Custom editing logic rebuilds list when individual level changes. Matches default.yaml structure cleanly.

3. **Cascade test timing: 100ms per relay** - Fast enough for quick verification (3.2s full cycle), slow enough to visually confirm each relay activates. Fixed timing keeps UI simple.

4. **Motor test uses async sequence with sleep delays** - Spindle must open before motor starts (mechanical safety requirement). Async/await provides clear sequential flow with precise timing. More readable than Clock.schedule_once chains.

5. **Individual motor/spindle test buttons** - Operators need to test components separately to diagnose failures (is motor broken? or spindle stuck?). Essential diagnostic capability.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both screens implemented smoothly using shared widget library from 02-01.

## Next Phase Readiness

**Ready to proceed:** Yes

Relay and motor screens complete. Both provide:
- Full configuration of hardware parameters
- Safe hardware testing with hold-to-activate pattern
- Live status monitoring
- Reset-to-defaults capability
- German labels throughout
- Confirmation dialogs for risky changes
- Safety cleanup on screen exit

**Next steps:** LED settings screen (02-03), Sensor settings screen (02-04), Audio settings screen (02-05).

**Blocks nothing.**

**Usage pattern:**

Both screens follow same pattern as widgets from 02-01:

```python
from monitoni.ui.debug_screens.relay_screen import RelaySettingsScreen
from monitoni.ui.debug_screens.motor_screen import MotorSettingsScreen

# Create relay screen
relay_screen = RelaySettingsScreen(
    hardware=hardware_manager,
    config_manager=config_manager,
    navigate_back=lambda: switch_to_menu()
)

# Create motor screen
motor_screen = MotorSettingsScreen(
    hardware=hardware_manager,
    config_manager=config_manager,
    navigate_back=lambda: switch_to_menu()
)
```

Both screens auto-save config changes to local.yaml and provide immediate hardware feedback via live status cards.

## Technical Implementation

### Cascade Test Pattern

Sequential relay activation with hold-to-cancel:

```python
async def _run_cascade_test(self):
    """Run cascade test loop."""
    while self._cascade_running:
        for channel in range(1, 33):
            if not self._cascade_running:
                break
            await self.hardware.relay.set_relay(channel, True)
            await asyncio.sleep(0.1)  # 100ms per relay
            await self.hardware.relay.set_relay(channel, False)
```

User holds button -> test runs. User releases -> test stops, all relays deactivated.

### Motor Sequence Pattern

Async state machine with safety shutdown:

```python
# On button hold:
async def _run_motor_sequence(self):
    # 1. Open spindle lock
    await self.hardware.relay.set_relay(spindle_ch, True)
    # 2. Wait pre-delay
    await asyncio.sleep(pre_delay_ms / 1000.0)
    # 3. Activate motor (runs while held)
    await self.hardware.relay.set_relay(motor_ch, True)

# On button release:
async def _shutdown_motor_sequence(self):
    # 1. Deactivate motor immediately
    await self.hardware.relay.set_relay(motor_ch, False)
    # 2. Wait post-delay
    await asyncio.sleep(post_delay_ms / 1000.0)
    # 3. Close spindle lock
    await self.hardware.relay.set_relay(spindle_ch, False)
```

Critical safety: motor must stop before spindle closes to prevent mechanical damage.

### Door Lock List Editing

Custom mutation logic for config list fields:

```python
def _edit_door_lock_channel(self, level: int, button):
    relay_channels = self.config_manager.config.vending.door_lock.relay_channels
    current_value = relay_channels[level - 1]

    def on_submit(new_value):
        # Rebuild list with new value
        new_channels = list(relay_channels)
        new_channels[level - 1] = int(new_value)

        # Save entire list
        update_dict = {
            "vending": {
                "door_lock": {
                    "relay_channels": new_channels
                }
            }
        }
        show_confirm_dialog(..., on_confirm=lambda: save(update_dict))
```

Preserves list structure from default.yaml while allowing per-level editing.

## Self-Check: PASSED

**Created files:**
- ✅ monitoni/ui/debug_screens/relay_screen.py exists
- ✅ monitoni/ui/debug_screens/motor_screen.py exists

**Commits:**
- ✅ 3aa5edc exists (Task 1: RelaySettingsScreen)
- ✅ 56e87d2 exists (Task 2: MotorSettingsScreen)
