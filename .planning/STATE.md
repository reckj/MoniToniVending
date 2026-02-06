# MoniToniVending - Project State

## Project Reference

**Building:** Kivy touchscreen vending machine UI - self-sufficient setup and maintenance
**Core Value:** Operators can deploy and manage machines entirely through touchscreen

## Current Position

- **Phase:** 4 of 5 - Maintenance Features
- **Plan:** 1 of 3 - Just completed 04-01-PLAN.md
- **Status:** In progress
- **Last activity:** 2026-02-06 - Completed 04-01-PLAN.md (QR Code Management)

## Progress

```
Phase 1: Debug Screen Architecture  [==========] Complete ✓
Phase 2: Settings Sub-screens       [========  ] 4/5 plans (80%)
Phase 3: Setup Wizard               [          ] Not Started
Phase 4: Maintenance Features       [===       ] 1/3 plans (33%)
Phase 5: UI Polish & Hardware Test  [          ] Not Started

Overall: [======....] ~52%
```

## Recent Decisions

| Decision | Date | Phase-Plan |
|----------|------|------------|
| NumpadDialog over NumpadField for transient level selection | 2026-02-06 | 04-01 |
| ERROR_CORRECT_M (15%) for QR code generation | 2026-02-06 | 04-01 |
| Image reload via source clearing and Clock.schedule_once | 2026-02-06 | 04-01 |
| Custom QR precedence pattern (custom_level_N.png > level_N.png) | 2026-02-06 | 04-01 |
| Clock.schedule_interval for 200ms sensor polling (need sync callback) | 2026-02-06 | 02-03 |
| LED brightness stored in led.animations.idle.brightness path | 2026-02-06 | 02-03 |
| Zone mapping uses direct pixel range (start/end) editable per-level | 2026-02-06 | 02-03 |
| Sensor door status prominently displayed with H3 font and color-coded background | 2026-02-06 | 02-03 |
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

Last session: 2026-02-06 19:00
Stopped at: Completed 04-01-PLAN.md (QR Code Management)
Resume file: None
Next: Continue with Phase 04 maintenance features
