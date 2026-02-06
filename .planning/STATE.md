# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 2 of 5 - Settings Sub-screens
- **Plan:** 1 of 5 - Just completed 02-01-PLAN.md
- **Status:** In progress
- **Last activity:** 2026-02-06 - Completed 02-01-PLAN.md (Shared Widget Library)

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [==        ] 1/5 plans (20%)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [          ] Not Started
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [===.......] ~25%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| touch.grab pattern for HoldButton safe release | 2026-02-06 | 02-01 |
| Support sync and async callbacks in LiveStatusCard | 2026-02-06 | 02-01 |
| RISKY_PATHS hardcoded list for confirmation dialogs | 2026-02-06 | 02-01 |
| NumpadField combines display + NumpadDialog for convenience | 2026-02-06 | 02-01 |
| Config helpers use dot-notation paths | 2026-02-06 | 02-01 |
| German labels, coral accent, contemporary/minimal UI aesthetic | 2026-02-06 | 01 |
| Turn button 600dp, prominent at top of customer screen | 2026-02-06 | 01 |
| Callbacks for navigation instead of hardcoded screen names | 2026-02-06 | 01 |
| Debug screen -> sub-screens for narrow touchscreen | 2026-02-06 | 01 |
| Defer web frontend to v0.3 | 2026-02-06 | 01 |
| Machine must be self-sufficient (no frontend for setup) | 2026-02-06 | 01 |

## Pending Todos

1. **Create design system for centralized UI styling** (ui) — 2026-02-06
2. **Create local chatbot webapp for setup & maintenance help** (tooling) — 2026-02-06

## Blockers/Concerns

None identified.

## Session Continuity

Last session: 2026-02-06 14:46
Stopped at: Completed 02-01-PLAN.md (Shared Widget Library)
Resume file: None
Next: Execute 02-02-PLAN.md (Relay and Motor settings screens)
