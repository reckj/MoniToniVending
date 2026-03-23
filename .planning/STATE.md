# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 4 of 5 - Maintenance Features (COMPLETE)
- **Plan:** 2 of 2 - Complete
- **Status:** Phase 4 complete, Phase 5 not yet planned
- **Last activity:** 2026-03-23 - Closed out Phase 4 (commit + summary)

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [========  ] 4/5 plans (80%)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [==========] Complete ✓
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [=======...] ~60%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| Full-screen MaintenanceDisplayScreen replaces customer screen entirely | 2026-03-23 | 04-02 |
| App routing consolidated through _go_to_customer_or_maintenance() | 2026-03-23 | 04-02 |
| bind(active=callback) is the reliable MDSwitch pattern in KivyMD 1.2.0 | 2026-03-23 | 04-02 |
| MDSwitch alignment deferred to design system overhaul | 2026-03-23 | 04-02 |
| NumpadDialog over NumpadField for transient level selection | 2026-02-06 | 04-01 |
| ERROR_CORRECT_M (15%) for QR code generation | 2026-02-06 | 04-01 |
| Image reload via source clearing and Clock.schedule_once | 2026-02-06 | 04-01 |
| Custom QR precedence pattern (custom_level_N.png > level_N.png) | 2026-02-06 | 04-01 |

## Pending Todos

1. **Create design system for centralized UI styling** (ui) — 2026-02-06
2. **Create local chatbot webapp for setup & maintenance help** (tooling) — 2026-02-06
3. **Fix motor asyncio lock bound to different event loop** (hardware) — 2026-02-06
4. **Add feedback QR code button to customer screen** (ui) — 2026-02-06

## Blockers/Concerns

- MDSwitch thumb slightly overflows card border (cosmetic, deferred to Phase 5 / design overhaul)

## Session Continuity

Last session: 2026-03-23
Stopped at: Phase 4 closed out — committed, summary created, ROADMAP/STATE updated
Resume file: None
Next: Phase 2 remaining plans (02-02 through 02-05), Phase 3, or Phase 5
