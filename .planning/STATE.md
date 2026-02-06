# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 2 of 5 - Settings Sub-screens
- **Plan:** 4 of 5 - Just completed 02-04-PLAN.md
- **Status:** In progress
- **Last activity:** 2026-02-06 - Completed 02-04-PLAN.md (Audio and Network Settings)

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [========  ] 4/5 plans (80%)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [          ] Not Started
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [======....] ~50%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| Network status auto-refreshes every 5s with Clock.schedule_interval | 2026-02-06 | 02-04 |
| Telemetry PIN masked by default with reveal/hide toggle button | 2026-02-06 | 02-04 |
| IP address detection tries socket connection test first, hostname fallback | 2026-02-06 | 02-04 |
| WiFi detection uses iwgetid command with graceful fallback | 2026-02-06 | 02-04 |
| Network connection test runs in executor to avoid blocking UI | 2026-02-06 | 02-04 |
| Volume stored as 0.0-1.0 in config but displayed as 0-100% | 2026-02-06 | 02-04 |
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

Last session: 2026-02-06 15:54
Stopped at: Completed 02-04-PLAN.md (Audio and Network Settings)
Resume file: None
Next: Execute 02-05-PLAN.md (Debug Menu Screen integration)
