# Phase 2: Settings Sub-screens - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Build 7 dedicated settings screens accessible from the debug menu, each providing full configurability and hardware test functions for its component. Screens replace the current placeholder sub-screens from Phase 1. All hardcoded parameters become configurable through the touchscreen UI, with changes persisting to config/local.yaml.

</domain>

<decisions>
## Implementation Decisions

### Screen layout & controls
- Number input via on-screen numpad (tap field to open numpad, type exact value). No sliders, no steppers.
- Related settings grouped in cards with section headers. Cards provide visual separation between parameter groups.
- Same contemporary/minimal aesthetic as customer screen: coral accent, near-black background, flat design.
- Fixed title bar at top of each screen showing screen name + back arrow. Content scrolls below.

### Test tool interaction
- Motor/relay tests: hold-to-activate pattern. Hardware runs only while button is held, releases immediately on finger lift. Safest approach.
- Live status area on each screen showing real-time hardware state (e.g., "Door: CLOSED", "Relay 3: ON").
- LED tests: color controls, zone selection, animation previews, and brightness adjustment. Full test coverage.
- Sensor testing: continuous live readout. Door state updates in real-time as operator opens/closes door.

### Config persistence
- Auto-save on change: each value writes to local.yaml immediately. No save button.
- Changes apply to hardware immediately/live as values change. Instant feedback.
- Reset-to-defaults button per screen, restoring factory values for that section only.
- Confirmation dialog for hardware pin changes (GPIO, relay channels, Modbus settings) that could affect communication. All other changes apply without confirmation.

### Screen priority & scope
- **Build order (highest priority first):** Relay > Motor > LED > Sensor > Audio > Network > Stats
- Relay: channel mapping, test individual relays (hold-to-activate), door lock config, cascade test
- Motor: timing parameters (spin_delay_ms, spindle_pre/post_delay_ms), relay channel, test spin (hold)
- LED: brightness, colors, zone mapping, animation previews (idle, purchase, alarm states)
- Sensor: GPIO pin config, pull mode, active state, live continuous door state readout
- Audio: volume control, test sound playback
- Network: server URL, machine ID, timeout values, WiFi status display, IP address display, test connection button
- Stats & Logs: full log viewer with scrollable output, filter by level, export to USB, basic counters (transactions, uptime, last error)

### Claude's Discretion
- Exact card grouping within each screen
- Numpad implementation details
- Loading/transition animations
- Error state presentation in live status area
- How reset-to-defaults confirmation works

</decisions>

<specifics>
## Specific Ideas

- Contemporary/minimal aesthetic established in Phase 1: coral accent (#F24033), near-black buttons (#1F1F1F), flat design, German labels
- Hold-to-activate is critical for safety — operator must physically hold the button for motor/relay to stay active
- Live status area should feel like a diagnostic dashboard — always visible, always updating
- Full log viewer for Stats means scrollable log output, not just summary stats

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-settings-sub-screens*
*Context gathered: 2026-02-06*
