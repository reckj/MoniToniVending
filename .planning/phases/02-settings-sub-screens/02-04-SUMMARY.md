---
phase: 02-settings-sub-screens
plan: 04
subsystem: ui
tags: [kivy, kivymd, audio, networking, pygame, settings-screens]

# Dependency graph
requires:
  - phase: 02-01
    provides: Shared widget library (NumpadDialog, SettingsCard, LiveStatusCard, NumpadField, config helpers)
provides:
  - AudioSettingsScreen with volume control and sound testing
  - NetworkSettingsScreen with server configuration and connectivity testing
  - TextInputDialog widget for string input fields
affects: [02-05-audio-network-integration, setup-wizard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TextInputDialog for string config fields (URLs, IPs, machine IDs)"
    - "Async HTTP connection testing with urllib in executor"
    - "System command integration for WiFi SSID (iwgetid) and IP detection"
    - "Volume stored as 0.0-1.0 but displayed as 0-100% for user convenience"
    - "Auto-refresh network status every 5s with Clock.schedule_interval"

key-files:
  created:
    - monitoni/ui/debug_screens/audio_screen.py
    - monitoni/ui/debug_screens/network_screen.py
  modified:
    - monitoni/ui/debug_screens/widgets.py

key-decisions:
  - "Volume stored as 0.0-1.0 in config but displayed/edited as 0-100% for operator convenience"
  - "Network connection test runs in executor to avoid blocking UI thread"
  - "WiFi detection uses iwgetid command with graceful fallback if unavailable"
  - "IP address detection tries socket connection test first, falls back to hostname resolution"
  - "Telemetry PIN masked by default with reveal/hide toggle button"
  - "Network status auto-refreshes every 5s, cancelled on screen leave"

patterns-established:
  - "TextInputDialog: Reusable dialog for string config fields, consistent with NumpadDialog pattern"
  - "Sound test buttons: Direct play on press (no hold-to-activate) since sounds are safe and stop naturally"
  - "System command integration: subprocess.run with timeout and exception handling for graceful degradation"
  - "Async HTTP requests: urllib in executor for non-blocking connection tests"

# Metrics
duration: 3min
completed: 2026-02-06
---

# Phase 2 Plan 4: Audio and Network Settings Summary

**Audio screen with volume control and sound testing; Network screen with server config, WiFi status, and connection testing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-06T15:51:30Z
- **Completed:** 2026-02-06T15:54:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Audio settings screen with 0-100% volume control, sound test buttons, file verification, and live status
- Network settings screen with server URL/ID configuration, connection testing, and WiFi/IP status display
- TextInputDialog widget for string input fields (URLs, machine IDs, IP addresses)
- All settings auto-save to local.yaml immediately via ConfigManager

## Task Commits

Each task was committed atomically:

1. **Task 1: Build AudioSettingsScreen** - `a0490a4` (feat)
2. **Task 2: Build NetworkSettingsScreen** - `6bc47b3` (feat)

## Files Created/Modified
- `monitoni/ui/debug_screens/audio_screen.py` - Audio configuration screen with volume control, sound testing, file status display, live status monitoring, and reset-to-defaults
- `monitoni/ui/debug_screens/network_screen.py` - Network configuration screen with server settings, connection test, WiFi/IP status, telemetry info, and reset-to-defaults
- `monitoni/ui/debug_screens/widgets.py` - Added TextInputDialog class for string input fields

## Decisions Made

**Volume display conversion:**
- Stored as 0.0-1.0 in config (hardware.audio.volume) for hardware compatibility
- Displayed and edited as 0-100% for operator convenience
- Conversion happens in AudioSettingsScreen._on_volume_changed()

**Network connection test implementation:**
- Uses urllib.request.urlopen() for HTTP GET requests
- Runs in asyncio executor to avoid blocking UI thread
- Displays response time on success, error message on failure
- Test button disabled during test to prevent concurrent requests

**WiFi and IP detection:**
- WiFi SSID: subprocess call to `iwgetid -r` with 2s timeout
- IP address: socket connection test to external host (8.8.8.8) first, hostname resolution fallback
- Both methods have graceful exception handling showing "Nicht verfügbar" on failure
- Status auto-refreshes every 5s via Clock.schedule_interval

**Telemetry PIN security:**
- PIN masked as "****" by default
- Reveal/hide toggle button to show actual PIN when needed
- Prevents shoulder-surfing while maintaining operator access

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all features implemented smoothly with existing patterns from plan 02-01.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next phase:**
- Audio screen allows operators to adjust volume and verify all sound effects work
- Network screen allows operators to configure purchase server connection for deployment
- Connection test provides clear feedback on server reachability
- WiFi/IP status helps operators verify network connectivity without SSH access

**Integration points:**
- Audio screen needs to be added to DebugMenuScreen navigation
- Network screen needs to be added to DebugMenuScreen navigation
- Future: Setup wizard can use these screens as embedded sub-flows
- Future: Audio test could be enhanced with sound effect upload capability

---
*Phase: 02-settings-sub-screens*
*Completed: 2026-02-06*

## Self-Check: PASSED

All files created:
- ✓ monitoni/ui/debug_screens/audio_screen.py
- ✓ monitoni/ui/debug_screens/network_screen.py

All commits verified:
- ✓ a0490a4 (Task 1)
- ✓ 6bc47b3 (Task 2)
