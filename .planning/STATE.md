---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: milestone
status: completed
stopped_at: Completed 02.1-03-PLAN.md — UI screens dual-module update
last_updated: "2026-03-24T11:32:38.962Z"
last_activity: "2026-03-24 - Executed 02.1-04: Remaining caller migration, dual-relay complete"
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 16
  completed_plans: 11
---

# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 02.1 - Dual Ethernet Relay Migration (COMPLETE)
- **Plan:** All 4 plans complete (01-04)
- **Status:** Phase 02.1 complete — resume Phase 02 (Settings Sub-screens) from plan 02-02
- **Last activity:** 2026-03-24 - Executed 02.1-04: Remaining caller migration, dual-relay complete

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [========  ] 1/5 plans (20%)
Phase 02.1: Dual Ethernet Relay     [==========] Complete ✓ (4/4 plans)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [==========] Complete ✓
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [███████░░░] 69%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| Waveshare transparent mode = raw Modbus RTU with CRC over TCP (no MBAP, no pymodbus) | 2026-03-23 | 02.1-01 |
| No command retry on failure — safety: avoids double-firing relay coils | 2026-03-23 | 02.1-01 |
| Per-controller asyncio.Lock; background reconnect only reconnects transport, never replays | 2026-03-23 | 02.1-01 |
| readexactly() for deterministic TCP reads (not read()) | 2026-03-23 | 02.1-01 |
| Optional pydantic config fields with defaults for backward compat | 2026-03-23 | 02.1-01 |
| Insert Phase 02.1 for dual Ethernet relay hardware migration | 2026-03-23 | 02.1 |
| Keep RS485 serial as fallback transport option | 2026-03-23 | 02.1 |
| 30-CH module for levels, 8-CH Module C for core + digital inputs | 2026-03-23 | 02.1 |
| Door sensor moves from GPIO to 8-CH digital input (Modbus func 0x02) | 2026-03-23 | 02.1 |
| Full-screen MaintenanceDisplayScreen replaces customer screen entirely | 2026-03-23 | 04-02 |
| App routing consolidated through _go_to_customer_or_maintenance() | 2026-03-23 | 04-02 |
| bind(active=callback) is the reliable MDSwitch pattern in KivyMD 1.2.0 | 2026-03-23 | 04-02 |
| Motor/spindle routes to relay_core (8-CH), door locks route to relay_levels (30-CH) | 2026-03-23 | 02.1-02 |
| DI sensor host/port taken from relay_core config (same physical device) | 2026-03-23 | 02.1-02 |
| relay_levels absent config creates MockRelayController (not an error — module may not be wired yet) | 2026-03-23 | 02.1-02 |
| self.relay backward-compat property returns relay_core to avoid breaking callers | 2026-03-23 | 02.1-02 |
| Telemetry relay API defaults to module=core for backward compat with existing API clients | 2026-03-24 | 02.1-04 |
| app.py door unlock guard uses relay_levels since unlock_door() routes through relay_levels internally | 2026-03-24 | 02.1-04 |

## Pending Todos

1. **Create design system for centralized UI styling** (ui) — 2026-02-06
2. **Create local chatbot webapp for setup & maintenance help** (tooling) — 2026-02-06
3. **Fix motor asyncio lock bound to different event loop** (hardware) — 2026-02-06
4. **Add feedback QR code button to customer screen** (ui) — 2026-02-06

## Blockers/Concerns

- MDSwitch thumb slightly overflows card border (cosmetic, deferred to Phase 5 / design overhaul)

## Roadmap Evolution

- Phase 02.1 inserted after Phase 2: Dual Ethernet Relay Migration (URGENT) — hardware changed from single RS485 relay + GPIO to dual Waveshare Ethernet PoE relay modules (30-CH levels + 8-CH core with digital inputs)

## Session Continuity

Last session: 2026-03-24T11:32:38.951Z
Stopped at: Completed 02.1-03-PLAN.md — UI screens dual-module update
Resume file: None
Next: /gsd:execute-phase 02.1
