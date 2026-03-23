# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 02.1 - Dual Ethernet Relay Migration (INSERTED)
- **Plan:** Not yet planned
- **Status:** Phase inserted, needs planning
- **Last activity:** 2026-03-23 - Inserted Phase 02.1 for hardware migration

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [========  ] 1/5 plans (20%)
Phase 02.1: Dual Ethernet Relay     [          ] Not Started (INSERTED)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [==========] Complete ✓
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [=====.....] ~50%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| Insert Phase 02.1 for dual Ethernet relay hardware migration | 2026-03-23 | 02.1 |
| Keep RS485 serial as fallback transport option | 2026-03-23 | 02.1 |
| 30-CH module for levels, 8-CH Module C for core + digital inputs | 2026-03-23 | 02.1 |
| Door sensor moves from GPIO to 8-CH digital input (Modbus func 0x02) | 2026-03-23 | 02.1 |
| Full-screen MaintenanceDisplayScreen replaces customer screen entirely | 2026-03-23 | 04-02 |
| App routing consolidated through _go_to_customer_or_maintenance() | 2026-03-23 | 04-02 |
| bind(active=callback) is the reliable MDSwitch pattern in KivyMD 1.2.0 | 2026-03-23 | 04-02 |

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

Last session: 2026-03-23
Stopped at: Phase 02.1 inserted into roadmap, needs planning
Resume file: None
Next: /gsd:plan-phase 02.1 to break down the hardware migration
