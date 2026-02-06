# Phase 3: Setup Wizard - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

A guided first-time configuration flow for new vending machine deployment. Walks operators through essential hardware and server setup via the touchscreen. Reuses widget components from Phase 2 but has custom wizard-specific screens. No hardware testing in the wizard itself — that's handled by existing debug sub-screens.

</domain>

<decisions>
## Implementation Decisions

### Wizard flow & steps
- Step order matches roadmap: Hardware (motor/relay) -> LED -> Relay mapping -> Sensors -> Server
- Every step is skippable — "Skip" button available on all steps
- Back button on every step for free back-and-forth navigation
- Skipped steps use defaults from default.yaml — machine works with sensible defaults out of the box

### First-run detection
- Detection method: check if `config/local.yaml` exists — if missing, it's a first run
- On first-run detection: show prompt dialog "First time setup detected" with two options: "Run Wizard" / "Skip"
- Skip goes straight to customer screen with defaults
- Wizard re-runnable from debug/settings menu ("Run Setup Wizard" button)
- Individual sub-screens also remain accessible separately (both options available)

### Step presentation
- Custom wizard screens (not direct reuse of Phase 2 sub-screens, but can pull widgets from Phase 2)
- Step dots progress indicator at top (e.g., filled/unfilled dots)
- Header: step dots + step title + 1-line description + skip and back buttons
- Essential fields shown by default, "Show advanced" toggle to expand additional options per step
- Designed for 400px wide portrait screen

### Completion & testing
- Simple "Setup complete!" message, then navigate to customer screen
- No hardware testing in wizard — operator uses debug sub-screens for that
- All config held in memory during wizard, written to local.yaml only when "Finish Setup" is pressed
- If wizard is abandoned (crash, navigate away), nothing is saved — next launch re-detects first-run and re-prompts

### Claude's Discretion
- Exact essential vs advanced field classification per step
- Widget layout within each wizard step
- Step dot styling and positioning
- "Setup complete" screen design
- How wizard re-run from debug menu handles existing config (pre-fill current values)

</decisions>

<specifics>
## Specific Ideas

- Wizard should feel lightweight — not overwhelming for a first-time operator
- "Show advanced" toggle keeps the default view clean while letting power users access everything
- Step descriptions should be brief (1 line) explaining what this step configures
- The existing Phase 2 widgets (NumpadField, SettingsCard, etc.) can be reused in custom wizard layouts

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-setup-wizard*
*Context gathered: 2026-02-06*
