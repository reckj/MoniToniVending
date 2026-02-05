# Codebase Concerns

**Analysis Date:** 2026-02-05

## Tech Debt

**Bare Exception Handling:**
- Issue: Bare `except:` clause in debug screen prevents proper error diagnosis
- Files: `monitoni/ui/debug_screen.py:625`
- Impact: Silent failures when retrieving LED zone configuration, masks root cause
- Fix approach: Replace with specific exception types, log error details for troubleshooting

**Bare `print()` Statements in Hardware Mocks:**
- Issue: Mock implementations use `print()` instead of logging framework
- Files: `monitoni/hardware/modbus_relay.py` (missing), `monitoni/hardware/audio.py:210-214`, `monitoni/core/purchase_client.py:227-268`, `monitoni/hardware/wled_controller.py:356-417`
- Impact: Mock debug output bypasses centralized logging, harder to track mock behavior in telemetry
- Fix approach: Inject logger into mock constructors, use logger.debug() or logger.info() for all output

**Global Singleton Pattern Proliferation:**
- Issue: Multiple global module-level singletons with lazy initialization
- Files: `monitoni/core/database.py:316-332`, `monitoni/core/logger.py:201-254`, `monitoni/hardware/manager.py:318-356`, `monitoni/telemetry/server.py:470+`
- Impact: Difficult to test in isolation, unclear initialization order dependencies
- Fix approach: Consider dependency injection or factory pattern for tests

**Inconsistent Error Handling Strategy:**
- Issue: Some modules catch and return None/False, others raise exceptions
- Files: `monitoni/core/purchase_client.py:84-138`, `monitoni/hardware/manager.py:81-199`, `monitoni/telemetry/server.py:201-217`
- Impact: Callers must handle mixed patterns (None checks vs try/except), error context lost
- Fix approach: Standardize to explicit error types with context propagation

## Security Considerations

**CORS Misconfiguration - Open to All Origins:**
- Risk: Frontend allows requests from any origin, potential CSRF attacks
- Files: `monitoni/telemetry/server.py:138-144`
- Current mitigation: PIN-based access control on debug endpoints
- Recommendations: Restrict CORS to known origins, implement token-based auth, disable CORS for non-dashboard routes

**PIN-Based Security Single Point of Failure:**
- Risk: All administrative access (relay, LED, audio control) protected only by PIN in config
- Files: `monitoni/telemetry/server.py:146-148`, `monitoni/ui/debug_screen.py:1105-1121`, `monitoni/core/config.py:136`
- Current mitigation: PIN stored in config, WebSocket authentication required
- Recommendations: Implement multi-factor authentication, rate limiting on PIN attempts, PIN rotation mechanism, HTTPS/WSS enforcement

**Telemetry Endpoint Publicly Exposed:**
- Risk: Machine status, logs, hardware state visible without authentication to unauthenticated callers
- Files: `monitoni/telemetry/server.py:194-226`, `monitoni/telemetry/server.py:228-257`
- Current mitigation: Status endpoint public, logs endpoint public
- Recommendations: Require authentication tokens for all endpoints, move public status to separate endpoint with rate limiting

**String PIN Comparison Vulnerability:**
- Risk: PIN compared as string, timing attacks possible on long delays
- Files: `monitoni/telemetry/server.py:148`, `monitoni/ui/debug_screen.py:1115`
- Current mitigation: Short 4-digit PIN limits damage
- Recommendations: Use constant-time comparison, add rate limiting with lockout

**Debug Screen Accessible via Tap Pattern:**
- Risk: Debug access protected only by PIN on physical screen, customer can attempt brute force
- Files: `monitoni/ui/customer_screen.py:460+`, `monitoni/ui/debug_screen.py:1105-1121`
- Current mitigation: PIN required, no rate limiting visible
- Recommendations: Implement lockout after failed attempts, add delay between attempts, log all access attempts

## Performance Bottlenecks

**Database Commit After Every Log Entry:**
- Problem: Each log write triggers immediate database commit in add_log
- Files: `monitoni/core/database.py:124-132`
- Cause: Synchronous commit blocks async operations, potential I/O bottleneck under high log volume
- Improvement path: Batch writes into transaction, commit periodically or on threshold, use write-ahead logging

**Poll-Based Purchase Checking:**
- Problem: Continuous polling loop even when not in CHECKING_PURCHASE state
- Files: `monitoni/core/purchase_flow.py:65-78`
- Cause: Sleep per iteration (0.5s) wastes CPU checking status machine repeatedly
- Improvement path: Event-driven instead of polling, trigger check only on state change

**Synchronous File I/O in Main Thread:**
- Problem: Frontend index.html read synchronously on first request
- Files: `monitoni/telemetry/server.py:160-162`
- Cause: Blocks event loop if frontend file is large or on slow storage
- Improvement path: Load frontend on startup, cache in memory or use StaticFiles for production

**Relay State Cache Not Persisted:**
- Problem: `_relay_states` dict only in memory, lost on restart
- Files: `monitoni/hardware/modbus_relay.py:60, 81-83`
- Cause: No state persistence means relays default to cached "off" on startup regardless of actual state
- Improvement path: Query all relay states on connect, persist state to database

## Fragile Areas

**State Machine Event Dispatch Without Validation:**
- Files: `monitoni/core/state_machine.py:123-145`
- Why fragile: No validation that event is valid for current state, silent returns on invalid transitions
- Safe modification: Add explicit state machine diagrams, log all attempted transitions, consider stricter typing
- Test coverage: No tests visible for invalid state transitions

**Hardware Component Initialization Race Condition:**
- Files: `monitoni/hardware/manager.py:45-79`
- Why fragile: Multiple independent initialization calls that can race, no locking on individual component init
- Safe modification: Ensure all component inits complete before returning manager
- Test coverage: Mock implementations always succeed, no real hardware failure scenarios tested

**Database Connection Not Validated On Use:**
- Files: `monitoni/core/database.py:124-132, 179-196`
- Why fragile: Assumes `_connection` is always valid after initialize, no reconnection logic
- Safe modification: Check connection state before each operation, implement auto-reconnect with exponential backoff
- Test coverage: Single-threaded use assumed, no concurrent access tests

**Purchase Flow Timeouts Not Enforced:**
- Files: `monitoni/core/state_machine.py:200-260`
- Why fragile: State machine has timeout logic but no background task driving timeout events
- Safe modification: Verify timeout task is running, test timeout edge cases
- Test coverage: Timeout callbacks defined but unclear if properly triggered

**Large Monolithic Debug Screen (1126 lines):**
- Files: `monitoni/ui/debug_screen.py:1-1126`
- Why fragile: Single module handles status display, configuration, hardware testing, and zone editing
- Safe modification: Split into separate sections/classes, test configuration updates independently
- Test coverage: UI testing not visible in codebase

## Scaling Limits

**Database Query Limit (999999):**
- Current capacity: Hardcoded 999999 as "unlimited" for export
- Limit: Will load entire database into memory on export
- Scaling path: Implement streaming export, pagination for large result sets, partition logs by date

**In-Memory WebSocket Connection List:**
- Current capacity: All clients stored in list, broadcasts to all connections
- Limit: O(n) broadcast time, no connection pooling or batching
- Scaling path: Use message queue (Redis), pub/sub pattern, connection filtering by client type

**Relay State Cache Array (32 slots):**
- Current capacity: Fixed 32-relay array, one machine only
- Limit: Cannot scale to multi-machine installations
- Scaling path: Make relay count dynamic, support multiple relay boards

## Dependencies at Risk

**Serial Communication Dependency:**
- Risk: Modbus relay controller requires `serial` library, no fallback if import fails
- Files: `monitoni/hardware/modbus_relay.py:1-13`
- Impact: Device cannot run without pySerial, even in mock mode
- Migration plan: Make serial import lazy, defer to first real hardware use, not required for mocks

**Pygame Audio Dependency:**
- Risk: Audio controller imports pygame at module level
- Files: `monitoni/hardware/audio.py:1-15`
- Impact: Device fails to start if pygame not installed, even if audio disabled in config
- Migration plan: Lazy import pygame only in PygameAudioController constructor

**ArtNet/pyArtNet for WLED:**
- Risk: WLED controller requires artnet library
- Files: `monitoni/hardware/wled_controller.py:1-20`
- Impact: LED control fails silently if library missing, falls back to mock
- Migration plan: Explicit error message when library missing and hardware enabled

## Test Coverage Gaps

**No Purchase Server Integration Tests:**
- What's not tested: Error scenarios from server (500, 429, timeout behavior), retry logic edge cases
- Files: `monitoni/core/purchase_client.py:73-203`
- Risk: Purchase timeouts and network errors could deadlock state machine unnoticed
- Priority: High

**No Database Error Recovery Tests:**
- What's not tested: Database connection failure during logging, corrupted database scenario, concurrent write conflicts
- Files: `monitoni/core/database.py:47-286`
- Risk: Silent failure of logs during peak operations
- Priority: High

**No State Machine Timeout Tests:**
- What's not tested: Timeout event delivery, multiple timeout events in sequence, timeout during transitions
- Files: `monitoni/core/state_machine.py:200-260`
- Risk: Purchase can hang indefinitely if timeout mechanism fails
- Priority: High

**No Hardware Failure Simulation:**
- What's not tested: Individual hardware component failures (relay unreachable, LED network down, GPIO error)
- Files: `monitoni/hardware/manager.py:45-199`
- Risk: Single failed component blocks entire startup, no graceful degradation
- Priority: Medium

**No UI Event Integration Tests:**
- What's not tested: Button press sequences, state transitions from UI, purchase flow end-to-end
- Files: `monitoni/ui/customer_screen.py`, `monitoni/ui/app.py:114-180`
- Risk: Customer flows broken without detection until field deployment
- Priority: Medium

**No Concurrency Tests:**
- What's not tested: Multiple simultaneous requests to telemetry API, concurrent hardware access, async task cleanup
- Files: `monitoni/telemetry/server.py`, `monitoni/hardware/manager.py`
- Risk: Race conditions, resource leaks under concurrent load
- Priority: Medium

## Missing Critical Features

**No Purchase Timeout Mechanism Visible:**
- Problem: State machine has purchase_timeout but no background task enforcing it
- Blocks: Purchases can hang indefinitely if server never responds
- Files: `monitoni/core/state_machine.py:69`, `monitoni/core/purchase_flow.py`
- Impact: Customer stuck on payment screen, machine unresponsive

**No Network Connectivity Check:**
- Problem: No health check for purchase server availability before accepting purchases
- Blocks: Cannot detect network down until purchase attempt
- Files: `monitoni/core/purchase_client.py`
- Impact: Accepts payment then fails, confusing customer

**No Log Rotation Policy:**
- Problem: Logs accumulate indefinitely in database with no automatic cleanup
- Blocks: Database grows unbounded, impacts query performance
- Files: `monitoni/core/database.py:262-286` (cleanup_old_logs exists but never called)
- Impact: Slow telemetry dashboard, eventual disk full

**No Configuration Hot Reload:**
- Problem: Config changes require application restart
- Blocks: Cannot update pricing or timings without downtime
- Files: `monitoni/core/config.py`
- Impact: Inflexible for operations

**No Graceful Shutdown on Errors:**
- Problem: Fatal errors in async tasks can leave hardware in unknown state
- Blocks: Relay might be left on, door unlocked, LEDs stuck
- Files: `monitoni/core/purchase_flow.py:77-78`, `monitoni/main.py:25-134`
- Impact: Safety hazard, require manual reset

---

*Concerns audit: 2026-02-05*
