# MoniToniVending - Project Definition

## What This Is

A Raspberry Pi-based vending machine system with a Kivy touchscreen interface. Customers select a product level, scan a QR code to pay, and the system unlocks the corresponding door. The machine integrates LED lighting (ArtNet/WLED), Modbus relay control, and GPIO door sensors.

**This Milestone (v0.2):** Make the Kivy touchscreen UI and hardware integration solid and bug-free. The machine must be fully self-sufficient - setup, configuration, and maintenance all possible through the touchscreen without requiring the web frontend.

## Core Value

A vending machine that operators can deploy, configure, and maintain entirely through its touchscreen interface.

## Requirements

### Validated Requirements

1. **Settings Sub-screens** - Debug screen becomes navigation hub with dedicated sub-screens for:
   - LED control (brightness, colors, animations, zone mapping)
   - Relay control (test individual, cascade, channel mapping)
   - Sensors (door status, GPIO pin configuration)
   - Audio (volume, test sounds)
   - Motor (timings, delays, test functions)
   - Network/Server (endpoints, timeouts, connection status)
   - Statistics & Logs

2. **Setup Wizard** - First-time configuration flow covering:
   - Hardware variables (motor delays, server timeouts, standby time)
   - LED setup (strip length, level mapping, brightness, state colors)
   - Relay mapping (motor channel, spindle lock, door locks per level)
   - GPIO configuration (door sensor pin, active state)
   - Server connection (endpoint, machine ID)

3. **Hardware Test Tools** - Each settings sub-screen includes test functions:
   - LED: test zones, test animations, test colors
   - Relay: test individual, test cascade, test door locks
   - Motor: test spin with configurable duration
   - Sensors: live door state display

4. **Maintenance Features**
   - QR code management: generate from links or upload QR images via USB
   - Out of order mode: deactivate machine with status display
   - Pricing updates without web frontend

5. **UI Polish**
   - Button sizes optimized for thin vertical touchscreen
   - Text/instructions clear and readable
   - Navigation intuitive between sub-screens

6. **Hardware Integration Testing**
   - Door sensor: verify detection and transaction flow
   - ArtNet/WLED: verify all state animations work on actual hardware
   - Relay: verify door unlock/lock operations

### Active Requirements (in progress)

None yet - milestone just defined.

### Out of Scope (this milestone)

- Web frontend (management dashboard) - deferred to v0.3
- Multi-unit deployment configuration
- Network credential management for deployment sites

## Constraints

- **Hardware:** Raspberry Pi 5, narrow vertical touchscreen
- **UI Framework:** Kivy (existing codebase)
- **LED Protocol:** ArtNet to WLED controller
- **Relay Protocol:** Modbus RTU over RS485
- **Door Sensor:** GPIO with gpiod (Pi 5 compatible)
- **No external dependencies** for setup - machine must work standalone

## Key Decisions

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Debug screen structure | Sub-screens per component | Better usability on narrow touchscreen | 2026-02-06 |
| Milestone scope | Kivy + hardware only | Frontend deferred to get solid foundation first | 2026-02-06 |
| Setup requirement | No frontend needed | Machine must be deployable with touchscreen only | 2026-02-06 |

## Technical Context

### Existing Architecture

- **Customer Screen**: Level selection → QR display → transaction flow
- **Debug Screen**: PIN-protected, currently 7 sections in single scroll view
- **State Machine**: 7 states (IDLE → CHECKING_PURCHASE → DOOR_UNLOCKED → etc.)
- **Hardware Manager**: Manages LED, relay, sensors, audio with mock fallbacks
- **Config**: YAML-based with local.yaml overrides

### Hardware Integration Status

| Component | Implementation | Tested on Hardware |
|-----------|---------------|-------------------|
| Relay (Modbus) | ✓ Complete | ✓ Yes |
| LED (ArtNet/WLED) | ✓ Complete | Needs testing |
| Door Sensor (GPIO) | ✓ Complete | Needs testing |
| Audio (Pygame) | ✓ Complete | Needs testing |

### Config Parameters Needing UI

Currently hardcoded or config-file-only:
- Motor: `relay_channel`, `spindle_lock_relay`, `spin_delay_ms`, `spindle_pre_delay_ms`, `spindle_post_delay_ms`
- Timeouts: sleep (60s), purchase (120s), door alarm (10s), door unlock (30s)
- Door sensor: GPIO pin (17), pull mode, active state
- Modbus: port, baudrate, slave address
- Server: endpoints, polling interval
