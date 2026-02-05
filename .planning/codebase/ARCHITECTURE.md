# Architecture

**Analysis Date:** 2026-02-05

## Pattern Overview

**Overall:** Layered event-driven architecture with state machine orchestration

**Key Characteristics:**
- Async-first design using Python's asyncio for non-blocking operations
- Hardware abstraction layer with mock implementations for testing and development
- Central state machine managing purchase flow lifecycle
- Separation of concerns: UI, hardware, business logic, telemetry, and persistence
- Event-driven communication between components via callbacks and state transitions

## Layers

**Presentation Layer (UI):**
- Purpose: Render customer interface and debug screens, handle user interactions
- Location: `monitoni/ui/`
- Contains: Screen implementations (customer_screen.py, debug_screen.py), main app (app.py), icon utilities (icons.py)
- Depends on: Core (state machine, logger, config), Hardware (HardwareManager)
- Used by: End users and service technicians

**Business Logic Layer (Core):**
- Purpose: Orchestrate purchase flow, manage state transitions, database operations, logging
- Location: `monitoni/core/`
- Contains: State machine (`state_machine.py`), purchase flow (`purchase_flow.py`), purchase client (`purchase_client.py`), database (`database.py`), configuration (`config.py`), logging (`logger.py`)
- Depends on: Hardware (HardwareManager for callbacks), Database (for persistence)
- Used by: UI layer, Telemetry layer, Hardware layer

**Hardware Abstraction Layer:**
- Purpose: Provide unified interface for all hardware components with real/mock fallback
- Location: `monitoni/hardware/`
- Contains: Base interfaces (`base.py`), hardware manager (`manager.py`), specific controllers (relay, LED, sensors, audio)
- Depends on: None (standalone)
- Used by: Business logic, Telemetry server

**Telemetry & Monitoring Layer:**
- Purpose: Remote monitoring, log retrieval, hardware debugging, configuration management via REST API
- Location: `monitoni/telemetry/`
- Contains: FastAPI server (`server.py`), frontend assets (`frontend/`)
- Depends on: Core (config, database, logger), Hardware (HardwareManager)
- Used by: Remote administrators and monitoring systems

**Persistence Layer:**
- Purpose: Store logs, statistics, and event records in SQLite database
- Location: `monitoni/core/database.py`
- Contains: Database schema, async query operations, table management
- Depends on: None
- Used by: Logger (via DatabaseHandler), Business logic (statistics), Telemetry (log retrieval)

## Data Flow

**Purchase Flow (Main Workflow):**

1. User taps product level on CustomerScreen
2. CustomerScreen triggers `state_machine.handle_event(Event.PURCHASE_SELECTED)`
3. State machine transitions to CHECKING_PURCHASE state
4. PurchaseFlowManager polls purchase server via `purchase_client.check_purchase()`
5. Upon valid response, state machine transitions to DOOR_UNLOCKED
6. HardwareManager receives state callback and calls `unlock_door(level)`
7. Relay controller activates specified relay channel
8. GPIO sensor detects door opening → Event.DOOR_OPENED
9. Sensor callback triggers state transition to DOOR_OPENED
10. Upon door close → Event.DOOR_CLOSED → COMPLETING
11. PurchaseFlowManager calls `complete_purchase()` to notify server
12. State machine returns to IDLE

**Hardware Status → UI Update:**
1. Hardware component state changes (e.g., door sensor)
2. Hardware callback (set via app.py) fires with state data
3. Callback triggers state machine event
4. State machine executes registered transition callbacks
5. UI screen updates via state notifications

**Logging & Telemetry:**
1. Any component calls `logger.info()`, `logger.error()`, etc.
2. Logger routes to console and DatabaseHandler
3. DatabaseHandler queues logs if event loop not ready, else async writes to database
4. Telemetry server polls database for logs via REST API `/api/logs`
5. Web frontend displays logs in real-time

**State Management:**

The PurchaseStateMachine in `monitoni/core/state_machine.py` is the single source of truth for purchase lifecycle state. State transitions are guarded:
- Only valid transitions allowed (e.g., IDLE → SLEEP only on timeout)
- Each state has associated timeout management (automatically cancels previous timeout)
- State entry and transition callbacks allow components to react to state changes
- Current state, previous state, and purchase context (ID, level, data) stored in machine

## Key Abstractions

**Hardware Component Interface:**
- Purpose: Define contract all hardware must implement
- Examples: `monitoni/hardware/base.py` (HardwareComponent, RelayController, LEDController, SensorController, AudioController)
- Pattern: Abstract base classes with `connect()`, `disconnect()`, `health_check()`, `is_connected()`, `get_status()` methods. Concrete implementations in `modbus_relay.py`, `wled_controller.py`, `gpio_sensors.py`, `audio.py`

**PurchaseStateMMachine:**
- Purpose: Encapsulate all purchase flow states and valid transitions
- Examples: `monitoni/core/state_machine.py`
- Pattern: State enum-based machine with event-driven transitions. Callbacks registered via `on_state_enter()` and `on_transition()`. Async timeout scheduling for state-specific delays.

**HardwareManager:**
- Purpose: Centralized hardware access with automatic real/mock fallback
- Examples: `monitoni/core/hardware/manager.py` plus module-level functions `initialize_hardware()`, `shutdown_hardware()`
- Pattern: Manager pattern holding refs to all component controllers. Tries real implementation first, falls back to mock on ImportError or connection failure. Used as singleton via module globals.

**DatabaseManager:**
- Purpose: SQLite async interface for logs and statistics
- Examples: `monitoni/core/database.py`
- Pattern: Manages connection lifecycle, table creation, async insert/query operations. Custom DatabaseHandler bridges Python logging to async database.

**Config Hierarchy:**
- Purpose: Load defaults from version control, override with local machine settings
- Examples: `monitoni/core/config.py` loads `config/default.yaml` then `config/local.yaml`
- Pattern: Pydantic models validating structure, env var overrides for sensitive values

## Entry Points

**Application Bootstrap:**
- Location: `monitoni/main.py`
- Triggers: `python -m monitoni.main` or direct script execution
- Responsibilities:
  - Parse CLI args (--mock, --debug, --test)
  - Load config via ConfigManager
  - Initialize database
  - Initialize hardware manager
  - Start telemetry server in background thread (uvicorn)
  - Create and run VendingApp (Kivy MDApp)
  - Handle graceful shutdown

**VendingApp (Kivy Application):**
- Location: `monitoni/ui/app.py`
- Triggers: Instantiated by main.py, runs until window closed or app.stop()
- Responsibilities:
  - Build screen hierarchy (ScreenManager with CustomerScreen and DebugScreen)
  - Create PurchaseStateMachine instance
  - Set up state and hardware callbacks
  - Bridge hardware events to UI updates
  - Manage app lifecycle (on_start, on_stop)

**Telemetry Server:**
- Location: `monitoni/telemetry/server.py`
- Triggers: Started as daemon thread in main.py (uvicorn.run)
- Responsibilities:
  - REST API for status, logs, config updates
  - WebSocket for real-time log streaming
  - Hardware debug endpoints (relay, LED, audio, sensor control)
  - PIN-protected endpoints for sensitive operations

## Error Handling

**Strategy:** Try-except with fallback to mock implementations, log all errors, surface critical failures

**Patterns:**

1. **Hardware Initialization Fallback** (`hardware/manager.py`):
   - Try real controller (e.g., ModbusRelayController)
   - Catch ImportError (library not available) → use mock
   - Catch connection Exception → log and use mock
   - Never fail startup; always return a functional component

2. **Async Operation Cancellation** (`core/state_machine.py`):
   - All timeout tasks stored and cancelled on state transition
   - `asyncio.CancelledError` caught in `_schedule_timeout()` to prevent unhandled errors
   - Graceful cleanup via finally blocks

3. **Database Error Recovery** (`core/logger.py`):
   - DatabaseHandler queues logs if event loop not ready
   - Failed async database writes caught; logs don't block main thread
   - Fallback to console-only logging if database unavailable

4. **Purchase Server Resilience** (`core/purchase_flow.py`):
   - Timeout-based invalid purchase detection (state machine timeout, not server error)
   - Server errors don't crash flow; timeouts handle stalled purchases
   - Completion notifications best-effort (no blocking on failure)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard logging (StreamHandler + DatabaseHandler)
- Approach: Centralized logger acquired via `get_sync_logger()` (early startup) or `get_logger()` (async context)
- Context: Purchase ID included via `logger.info(..., purchase_id=...)` extra field
- Targets: Console (development), Database (telemetry), File rotation (if configured)

**Validation:**
- Configuration validation via Pydantic models (`core/config.py`) with field validators
- Hardware level validation in HardwareManager (relay channel bounds checking)
- Purchase level bounds checking in `hardware/manager.py` convenience methods

**Authentication:**
- Telemetry endpoints protected by PIN verification (request body includes `pin` field)
- PIN checked against config value; hardcoded for now (migrate to env var)
- No user authentication on UI (kiosk use case)

**Async Concurrency:**
- All I/O operations (hardware, database, network) are async
- Event loop managed by Kivy app via `app.async_run()` and `logger.set_event_loop()`
- Daemon thread for telemetry server (HTTP doesn't block UI loop)
- Task cancellation and exception handling for timeouts and background operations
