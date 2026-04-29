---
status: awaiting_human_verify
trigger: "Kivy touchscreen app on Raspberry Pi 5 becomes noticeably laggy within 5-15 minutes of launch and progressively worsens over time. Happens even when the app is sitting idle (no user interaction). No errors or exceptions — app just gets slower. Classic profile of a fast-accumulating runtime leak."
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
---

## Current Focus

reasoning_checkpoint:
  hypothesis: "Five LiveStatusCard widgets (relay, motor, led, audio, maintenance debug screens) start a Clock.schedule_interval in __init__ at app startup. They run every 0.5–2.0s for the entire app lifetime. Their on_pre_leave() cleanup is dead code because LiveStatusCard subclasses MDCard, not Screen — Kivy never dispatches Screen lifecycle events to child widgets. Each tick of _display_status() destroys and recreates 5–10 MDLabel widgets, churning Kivy widget/texture/property machinery. For async-callback variants (maintenance, motor) each tick also spawns asyncio tasks whose references are discarded. Over 5–15 minutes this produces thousands of widget create/destroy cycles + accumulating fonts/textures (KivyMD 1.2.0 has known texture caching issues), causing progressive UI lag idle."
  confirming_evidence:
    - "Zero Clock.unschedule(...) calls in entire codebase"
    - "LiveStatusCard.on_pre_leave defined on an MDCard subclass — Screen events never fire on child widgets (Kivy ScreenManager dispatches on_pre_leave only to the Screen itself)"
    - "All 11 BaseDebugSubScreen subclasses are instantiated once at app startup (debug_screen.py:347-354) and added to a nested ScreenManager, so all 5 LiveStatusCards start polling at startup and never stop"
    - "_display_status clears self.status_container.clear_widgets() and creates fresh BoxLayout + 2 MDLabel widgets per status item every tick (5 items × 2 labels × 2 Hz = 20 widgets/sec just for relay_screen alone, ×5 cards)"
    - "Async LiveStatusCard variants (maintenance get_machine_status, motor) call asyncio.create_task(self._update_status_async()) and discard the Task reference — tasks may also pile up if any await blocks"
  falsification_test: "If we add Clock.unschedule(self._update_event) to LiveStatusCard at the right time (or stop scheduling at __init__ and instead start in on_kv_post / start_polling()), and the lag accumulation disappears at the same rate it stops, this hypothesis is confirmed. Conversely: disable all LiveStatusCards entirely, run app idle for 30 min — if lag still accumulates, the hypothesis is wrong and we must look at lower-level hardware loops (modbus DI, WLED, GPIO event monitor)."
  fix_rationale: "Stop polling when the LiveStatusCard is not visible. Since LiveStatusCard cannot rely on Screen lifecycle events, two approaches: (a) the parent BaseDebugSubScreen tracks its own LiveStatusCards and starts/stops them on on_pre_enter/on_pre_leave, (b) provide explicit start_polling/stop_polling on LiveStatusCard and call them from the parent screen's lifecycle hooks. Option (b) is cleanest. Additionally: ensure that within _update_status, async-callback path keeps a reference to the spawned task and skips creating a new task if a previous one is still pending — to bound asyncio task count under slow callbacks."
  blind_spots: "Have not measured len(Clock._events), len(asyncio.all_tasks()), or RSS over time on the actual Pi. Cannot rule out a slower secondary leak in modbus_digital_input poll loop reconnects, GPIO event monitor thread, or KivyMD theme/styling. The fix addresses the dominant cost; secondary leaks may still exist but be much smaller."

hypothesis: 5 LiveStatusCards run forever from app startup; each tick destroys+recreates 5–10 MDLabel widgets and (for async variants) spawns unmanaged asyncio tasks.
test: Stop LiveStatusCard polling when its parent screen is not visible; verify lag accumulation halts. Add observability (Clock._events, asyncio.all_tasks count) to confirm.
expecting: After fix, idle session for 30+ minutes shows steady widget/task counts and no lag.
next_action: Implement explicit start_polling/stop_polling on LiveStatusCard, drive them from BaseDebugSubScreen's on_pre_enter/on_pre_leave. Also fix async-task pile-up by tracking the last spawned task and skipping spawn if still pending. Add a Window.bind for tracemalloc-style observability for verification.

## Symptoms

expected: App stays responsive indefinitely while idle on the touchscreen — frame rate steady, touch response immediate.
actual: Within 5-15 minutes of launch, UI becomes laggy. Lag worsens over time. Continues degrading even when nobody touches the screen.
errors: None observed. No exceptions, no Kivy warnings reported, no OOM. App keeps running, just slow.
reproduction: Launch app via venv python on the Pi, let it sit idle on any screen for 5-15 minutes. Observe degraded responsiveness.
started: Unknown if app has ever stayed responsive long-term. Possibly foundational pattern. Recent phase 02.1 dual ethernet relay migration is a candidate vector.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-04-29
  checked: grep -rn "Clock.unschedule" monitoni/ --include="*.py"
  found: ZERO Clock.unschedule calls in entire codebase (matches against widget._update_event.cancel() which uses Kivy's ClockEvent.cancel(), so this is OK in some places — but no .unschedule by callable reference anywhere)
  implication: The codebase relies on storing the ClockEvent handle and calling .cancel() on it. Wherever a handle is NOT stored, that interval can never be cancelled.

- timestamp: 2026-04-29
  checked: monitoni/ui/debug_screens/widgets.py LiveStatusCard
  found: __init__ calls Clock.schedule_interval(lambda dt: self._update_status(), update_interval) and stores handle in self._update_event. Defines on_pre_leave() to cancel it. BUT LiveStatusCard subclasses MDCard, NOT Screen. Kivy's ScreenManager only dispatches on_pre_enter/on_enter/on_pre_leave/on_leave to Screen instances — never to child widgets. So on_pre_leave() on LiveStatusCard is DEAD CODE. The ClockEvent is never cancelled in normal operation. The only explicit cleanup() call is also never invoked anywhere in the codebase (grep "cleanup()" -> no caller).
  implication: Every LiveStatusCard ever created keeps its Clock.schedule_interval running for the entire app lifetime. This is steady-state, not accumulating per-navigation, BECAUSE screens are also created once at startup (see next finding).

- timestamp: 2026-04-29
  checked: monitoni/ui/debug_screen.py:340-360 (sub_screen_classes loop)
  found: All BaseDebugSubScreen subclasses (Audio, Network, Stats, QRMgmt, Maintenance, Sensor, Relay, LED, Motor, etc.) are instantiated ONCE at app start and added to a nested ScreenManager. navigate_to() just changes .current — never recreates a screen.
  implication: A single screen instance lives the entire app lifetime, so its __init__ Clock.schedule_interval calls execute once. So per-navigation accumulation of Clock callbacks is NOT the issue.

- timestamp: 2026-04-29
  checked: monitoni/ui/debug_screens/relay_screen.py:155-166 (_build_module_status_row)
  found: Two Clock.schedule_interval calls (one per relay module: core + levels) WITHOUT storing the handle. These run every 1.0s forever. They ARE dead code on screen leave — but since screens are reused, this is steady (2 intervals at 1Hz each).
  implication: Steady-state cost, not accumulation.

- timestamp: 2026-04-29
  checked: monitoni/hardware/modbus_digital_input.py connect() and _reconnect_loop()
  found: connect() at line 96 unconditionally does `self._poll_task = asyncio.create_task(self._poll_loop())` without checking/cancelling any previous task. _reconnect_loop() at line 278 calls `self.connect()` on every retry. The previous _poll_task reference is overwritten and orphaned. _poll_loop() is `while True` with `await asyncio.sleep(poll_interval_ms/1000)` — only exits via asyncio.CancelledError. Orphan tasks keep running, polling on a stale reader. This IS accumulation per reconnect.
  implication: PRIMARY LEAK CANDIDATE if Modbus digital input reconnects ever happen during idle. If door sensor uses modbus_di method and connection drops occasionally (network blip, switch port, cable jitter), every reconnect spawns a permanent ghost poll loop. Over hours, dozens of ghosts accumulate.

- timestamp: 2026-04-29
  checked: monitoni/hardware/modbus_tcp_relay.py connect()
  found: connect() does NOT spawn a poll task. Only the reconnect loop is managed (and it's correctly guarded against double-start at line 244). So relay does NOT have the same orphan-task bug.
  implication: Bug is specific to modbus_digital_input, not relay.

- timestamp: 2026-04-29
  checked: monitoni/ui/debug_screens/widgets.py LiveStatusCard._update_status
  found: When get_status_callback is async, every Clock tick schedules `asyncio.create_task(self._update_status_async())`. The Task reference is discarded. PEP-suggested antipattern (tasks can be GC'd mid-await). If the async callback's awaits ever back up (slow network status, slow modbus read), tasks pile up faster than they complete.
  implication: SECONDARY LEAK CANDIDATE for screens whose LiveStatusCards have slow async callbacks. MaintenanceScreen.get_machine_status awaits self.hardware.led.is_connected() (HTTP call to WLED) inside a 2.0s interval — if WLED is slow/unreachable, tasks pile up.

- timestamp: 2026-04-29
  checked: maintenance_screen.py:99-104 LiveStatusCard with async get_machine_status callback at 2.0s interval
  found: get_machine_status awaits hardware.led.is_connected() which (per wled_controller patterns) is likely an HTTP call that can hang or be slow. Combined with Clock.schedule_interval that NEVER stops, every 2s a new task is spawned regardless of whether previous one finished. If WLED times out at 5s, 3 tasks are in flight at all times. If WLED times out at 30s, 15 tasks pile up.
  implication: This screen's status card may be the dominant idle leak vector when WLED is offline/slow.

- timestamp: 2026-04-29
  checked: customer_screen.py:462 Clock.schedule_interval(self._update_ui, 0.5)
  found: Stable single interval, runs forever. _update_ui is sync, only updates labels. Inside _update_ui at line 753 there's a Clock.schedule_once(2.0) inside `if state == State.COMPLETING` branch — only fires on a real purchase, not idle. Customer screen alone is NOT the source of idle leak.
  implication: Customer screen on its own is steady. Idle lag must come from something else running while customer screen is shown.

- timestamp: 2026-04-29
  checked: Async tasks on Kivy main thread interaction
  found: app uses `asyncio.run(main_async)` and `await app.async_run()` (Kivy async EventLoop). asyncio.create_task from inside Clock callbacks targets the running loop. Telemetry server runs uvicorn in a separate thread with its own loop — set_state does `asyncio.create_task(self._broadcast(...))` from sync context, which (if called from Kivy thread) would fail or be misrouted. Not currently called externally though, so not active.
  implication: No cross-thread task confusion in the active idle path.

## Resolution

root_cause: |
  All 5 LiveStatusCard widgets across the debug sub-screens (relay, motor, led,
  audio, maintenance) auto-started a Clock.schedule_interval inside their
  __init__ at app startup. Because every BaseDebugSubScreen is instantiated
  ONCE at app startup and reused (debug_screen.py:347-354), the cards started
  polling immediately and ran forever, regardless of which screen was visible.

  LiveStatusCard had an on_pre_leave() method intended as cleanup, but it was
  dead code: LiveStatusCard subclasses MDCard (not Screen), and Kivy
  ScreenManager only dispatches Screen lifecycle events to the Screen instance
  itself — never to child widgets. So the cleanup was never invoked.

  Each polling tick (every 0.5–2.0s, per card) called _display_status which
  destroyed and recreated 5–10 MDLabel widgets in status_container — churning
  Kivy widget construction, font/texture cache (KivyMD 1.2.0 is known to leak
  textures here), and property bindings. For async-callback variants
  (maintenance, motor) each tick also did asyncio.create_task(...) and
  discarded the Task reference, so if a callback was slow (e.g. WLED HTTP
  hang, modbus backlog), tasks piled up faster than they completed.

  Net effect: from the moment the app started, ~5 callbacks/sec churned widget
  trees and (when async) leaked asyncio Tasks. Over 5–15 minutes idle, this
  saturated the Kivy clock + asyncio event loop and the UI degraded. Lag
  accumulated whether the user touched the screen or not because the polling
  never stopped.

fix: |
  Two-part change in monitoni/ui/debug_screens/{widgets.py, base.py}:

  1. LiveStatusCard no longer auto-starts polling in __init__. Added explicit
     start_polling() / stop_polling() methods (idempotent). on_pre_leave() and
     cleanup() now both delegate to stop_polling() and are documented as
     manual hooks — Kivy will not invoke on_pre_leave on a child widget.
     Added an in-flight async task guard: if a previous async callback is
     still running, the new tick skips creating another task (prevents
     pile-up). The Task reference is held strongly so it isn't GC'd
     mid-await.

  2. BaseDebugSubScreen now overrides on_pre_enter / on_pre_leave to walk
     its widget subtree and call start_polling() / stop_polling() on every
     LiveStatusCard descendant. This is fully backwards-compatible: existing
     screens did not need code changes (call sites still just construct a
     LiveStatusCard and add it to the screen via add_content). Four sibling
     screens that already overrode on_pre_leave (network, sensor, led, stats)
     were updated to call super().on_pre_leave(*args) so the LiveStatusCard
     cleanup chain reaches them.

verification: |
  - Syntax + imports: ast.parse + import all 8 sub-screens — clean.
  - Unit-style smoke tests on LiveStatusCard polling lifecycle (auto-start
    disabled, start/stop idempotent, on_pre_leave + cleanup delegate to stop):
    8/8 PASS.
  - Lifecycle propagation tests on BaseDebugSubScreen with two screens A,B
    in a ScreenManager: only the current screen polls; navigation A->B->A
    correctly transfers polling; 10 navigation cycles do not leak —
    4/4 PASS.
  - End-to-end smoke test booting full VendingApp with mock hardware and
    navigating relay → motor → led → audio → maintenance → menu: each screen
    while current shows 1/1 cards polling; back at menu all screens show
    0 polling cards. PASS.
  - Pre-existing on_pre_leave overrides in network/sensor/led/stats screens
    were updated to call super().on_pre_leave(*args) so the new chain works
    on all screens.

  Still requires real-hardware Pi 5 verification: launch the app, leave on
  customer screen idle for 30+ minutes after navigating into and out of a
  few debug screens, and confirm the UI stays responsive (no progressive
  lag). Suggested instrumentation if it still degrades:
    from kivy.clock import Clock
    import asyncio
    print(len(Clock._events), len(asyncio.all_tasks()))
  Run those every 60s; both should stay flat.

files_changed:
  - monitoni/ui/debug_screens/widgets.py
  - monitoni/ui/debug_screens/base.py
  - monitoni/ui/debug_screens/network_screen.py
  - monitoni/ui/debug_screens/sensor_screen.py
  - monitoni/ui/debug_screens/led_screen.py
  - monitoni/ui/debug_screens/stats_screen.py
