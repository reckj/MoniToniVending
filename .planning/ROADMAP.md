# MoniToniVending v0.2 Roadmap

## Milestone Goal

Make the Kivy touchscreen UI and hardware integration solid and bug-free. Machine fully self-sufficient for setup, configuration, and maintenance.

## Phases

### Phase 1: Debug Screen Architecture
**Goal:** Convert debug screen from single scroll view to navigation hub with sub-screens

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md - Create debug_screens package with BaseDebugSubScreen and DebugMenuScreen
- [x] 01-02-PLAN.md - Refactor DebugScreen to use nested ScreenManager

**Delivers:**
- Navigation menu replacing current single-scroll debug screen
- Screen management infrastructure for settings sub-screens
- Back navigation pattern
- PIN protection preserved

**Success Criteria:**
- Debug screen shows menu of component categories
- Tapping category navigates to dedicated sub-screen
- Back button returns to menu
- No functionality lost from current implementation

---

### Phase 2: Settings Sub-screens
**Goal:** Build dedicated settings screens for each hardware component with full configurability

**Plans:** 5 plans

Plans:
- [x] 02-01-PLAN.md - Shared widgets (NumpadDialog, HoldButton, LiveStatusCard, SettingsCard, config helpers)
- [ ] 02-02-PLAN.md - Relay and Motor settings screens
- [ ] 02-03-PLAN.md - LED and Sensor settings screens
- [ ] 02-04-PLAN.md - Audio and Network settings screens
- [ ] 02-05-PLAN.md - Stats & Logs screen + integration into DebugScreen

**Delivers:**
- LED sub-screen: brightness, colors, animations, zone mapping with test tools
- Relay sub-screen: channel mapping, test individual/cascade, door lock config
- Motor sub-screen: timing parameters, test spin function
- Sensors sub-screen: GPIO config, live door state, test functions
- Audio sub-screen: volume, sound selection, test buttons
- Network sub-screen: server endpoints, timeouts, connection status
- Stats & Logs sub-screen: statistics display, log viewer, export

**Success Criteria:**
- All hardcoded parameters now configurable through UI
- Changes persist to config/local.yaml
- Each component has working test functions
- Settings survive app restart

---

### Phase 02.1: Dual Ethernet Relay Migration (INSERTED)
**Goal:** Migrate from single RS485 relay + GPIO sensor to dual Ethernet PoE relay modules (Waveshare 30-CH for levels, 8-CH Module C for core) with digital input door sensing

**Depends on:** Phase 2 (shared widgets)

**Plans:** 2/4 plans executed

Plans:
- [x] 02.1-01-PLAN.md — Modbus utils, TCP relay controller, digital input controller, config models
- [x] 02.1-02-PLAN.md — HardwareManager dual relay routing and sensor method dispatch
- [ ] 02.1-03-PLAN.md — UI screens: relay (dual-section), motor (relay_core), sensor (method indicator)
- [ ] 02.1-04-PLAN.md — Caller migration: customer screen, app, telemetry, maintenance, main

**Delivers:**
- TCP socket transport for Modbus RTU alongside existing RS485 serial (configurable)
- Two relay controller instances: `relay_core` (8-CH) for motor/spindle/machine, `relay_levels` (30-CH) for per-level door locks
- Digital input reading (function code 0x02) on 8-CH module for door sensor (replaces GPIO)
- HardwareManager routing: motor/spindle → core module, door locks → levels module
- Config restructure: IP/port per module, channel mappings per module, digital input config
- Updated UI screens (relay, motor, sensor) for dual-module setup

**Hardware:**
- Waveshare Modbus POE ETH Relay 30CH — levels (door locks), Modbus RTU over TCP, default 192.168.1.254:502
- Waveshare Modbus POE ETH Relay (C) — core (motor, spindle, machine functions) + 8 digital inputs, Modbus RTU over TCP
- RS485 serial kept as fallback transport option

**Success Criteria:**
- Both relay modules controllable independently via Ethernet
- Door sensor reads from 8-CH digital input instead of GPIO
- Motor/spindle operations route to core module
- Door lock operations route to levels module
- RS485 serial still works as alternative transport
- All existing relay/motor/sensor settings screens updated
- Mock controllers still work for development without hardware

---

### Phase 3: Setup Wizard
**Goal:** First-time configuration flow for new machine deployment

**Plans:** 3 plans

Plans:
- [ ] 03-01-PLAN.md — Wizard infrastructure (coordinator, header, base step, dialog, utilities)
- [ ] 03-02-PLAN.md — Wizard steps (Hardware, LED, Relay Map, Sensor, Server, Completion)
- [ ] 03-03-PLAN.md — App integration (first-run detection, ScreenManager wiring, debug menu re-run)

**Delivers:**
- Wizard entry point (detect first run or manual trigger)
- Step-by-step flow: Hardware -> LED -> Relay -> Sensors -> Server
- Each step uses components from Phase 2 sub-screens
- Skip/back navigation
- Completion confirmation with atomic config save

**Success Criteria:**
- New machine can be fully configured without editing config files
- Wizard detects unconfigured state and prompts automatically
- All critical settings covered before machine goes operational
- Can re-run wizard from settings menu

---

### Phase 4: Maintenance Features
**Goal:** Enable operators to manage machine without web frontend

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — QR Management Screen (generate, upload, preview, delete QR codes)
- [x] 04-02-PLAN.md — Maintenance Mode + Integration (toggle, status display, customer screen check, debug menu wiring)

**Delivers:**
- QR code management screen:
  - Generate QR from payment link URL
  - Upload QR images from USB drive
  - Preview and assign to levels
- Out of order mode:
  - Toggle from settings
  - Customer screen shows maintenance message
  - Disables purchase flow
- Machine status display for operators

**Success Criteria:**
- Pricing/QR updates possible entirely through touchscreen
- Machine can be put in/out of maintenance mode
- Clear operator feedback for all maintenance actions

---

### Phase 5: UI Polish & Hardware Testing
**Goal:** Optimize UI for actual hardware and verify all integrations work

**Delivers:**
- Button size optimization for narrow touchscreen
- Text/instruction clarity improvements
- Navigation flow refinements
- Hardware integration verification on actual Pi + peripherals

**Success Criteria:**
- All buttons easily tappable on physical touchscreen
- Instructions clear and readable at viewing distance
- Door sensor triggers transaction flow correctly
- LED animations display on actual WLED strip
- Audio plays through actual speakers
- Full purchase flow works end-to-end on hardware

---

## Phase Dependencies

```
Phase 1 (Architecture)
    └── Phase 2 (Sub-screens)
            └── Phase 02.1 (Dual Ethernet Relay Migration) ← INSERTED
                    ├── Phase 2 remaining (02-02..02-05)
                    ├── Phase 3 (Wizard)
                    └── Phase 4 (Maintenance) ✓
                             │
                             v
                    Phase 5 (Polish & Testing)
```

## Progress Tracking

| Phase | Status | Plans | Notes |
|-------|--------|-------|-------|
| 1. Debug Screen Architecture | Complete ✓ | 2/2 | Verified 2026-02-06 |
| 2. Settings Sub-screens | In Progress | 1/5 | Shared widget library complete |
| 02.1 Dual Ethernet Relay Migration | 2/4 | In Progress|  |
| 3. Setup Wizard | Planned | 0/3 | 3 plans in 3 waves |
| 4. Maintenance Features | Complete ✓ | 2/2 | Verified 2026-03-23 |
| 5. UI Polish & Hardware Testing | Not Started | 0/0 | |
