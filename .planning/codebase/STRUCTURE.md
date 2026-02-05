# Codebase Structure

**Analysis Date:** 2026-02-05

## Directory Layout

```
MoniToniVending/
├── monitoni/                      # Main application package
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── core/                      # Business logic and utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration management (YAML + Pydantic)
│   │   ├── state_machine.py       # Purchase flow state machine
│   │   ├── purchase_flow.py       # Purchase server integration
│   │   ├── purchase_client.py     # HTTP client for purchase validation
│   │   ├── database.py            # SQLite async operations
│   │   └── logger.py              # Logging system with DB backend
│   ├── hardware/                  # Hardware abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract component interfaces
│   │   ├── manager.py             # Hardware manager + global instance
│   │   ├── modbus_relay.py        # Relay controller (real + mock)
│   │   ├── wled_controller.py     # LED controller (ArtNet + mock)
│   │   ├── gpio_sensors.py        # Sensor controller (GPIO + mock)
│   │   └── audio.py               # Audio controller (Pygame + mock)
│   ├── ui/                        # Kivy UI screens and app
│   │   ├── __init__.py
│   │   ├── app.py                 # Main Kivy MDApp
│   │   ├── customer_screen.py     # Customer-facing product UI
│   │   ├── debug_screen.py        # Debug/service technician UI
│   │   └── icons.py               # Icon font utilities
│   └── telemetry/                 # Remote monitoring and control
│       ├── __init__.py
│       ├── server.py              # FastAPI telemetry server
│       └── frontend/              # Web dashboard (HTML/CSS/JS)
├── config/                        # Configuration files
│   ├── default.yaml               # Version-controlled defaults
│   └── local.yaml.example         # Template for machine-specific overrides
├── assets/                        # Static assets
│   ├── fonts/                     # Icon fonts for UI
│   └── qr_codes/                  # Generated QR code images
├── scripts/                       # Testing and utility scripts
│   ├── test_relay.py              # Relay controller tests
│   ├── test_relay_debug.py        # Debug relay tests
│   └── test_relay_raw.py          # Raw Modbus communication tests
├── docs/                          # Documentation
├── .planning/                     # GSD planning documents
│   └── codebase/                  # Architecture/structure analysis
├── requirements.txt               # Python dependencies
├── README.md                      # Project overview
└── main.py                        # (symlink or wrapper for entry point)
```

## Directory Purposes

**monitoni/:**
- Purpose: Main application package containing all source code
- Contains: Core business logic, hardware drivers, UI, telemetry server
- Key entry: `main.py`

**monitoni/core/:**
- Purpose: Shared business logic, configuration, state management, persistence
- Contains: State machine, purchase flow, configuration management, database operations, logging
- Key files: `state_machine.py` (7 classes), `config.py` (15+ config classes), `database.py` (DatabaseManager)
- Pattern: All async operations, centralized access via module-level globals (get_config_manager, get_logger, get_database)

**monitoni/hardware/:**
- Purpose: Hardware abstraction and control
- Contains: Base interface classes, manager, real and mock implementations for relay/LED/sensor/audio
- Key files: `base.py` (5 abstract classes), `manager.py` (HardwareManager + init/shutdown)
- Pattern: Real → ImportError → Mock fallback chain; supports --mock CLI flag for testing

**monitoni/ui/:**
- Purpose: User interface and screen management
- Contains: Kivy MDApp, two screens (customer and debug), icon utilities
- Key files: `app.py` (VendingApp), `customer_screen.py` (product UI), `debug_screen.py` (service UI)
- Pattern: ScreenManager pattern; screens receive app_config, hardware, logger, state_machine on init

**monitoni/telemetry/:**
- Purpose: Remote monitoring and hardware debugging
- Contains: FastAPI server with REST and WebSocket endpoints, static web assets
- Key files: `server.py` (TelemetryServer + route handlers), `frontend/` (HTML/CSS/JS dashboard)
- Pattern: PIN-protected endpoints; runs in daemon thread started by main.py

**config/:**
- Purpose: System configuration management
- Contains: default.yaml (version-controlled), local.yaml.example (template)
- Pattern: Pydantic loads YAML into typed config objects; local.yaml overrides defaults
- Key sections: hardware (relay, LED, GPIO, audio), vending (levels, motor, door lock), timing, UI, audio

**assets/:**
- Purpose: Static resources (fonts, generated images)
- Contains: fonts/ (icon fonts), qr_codes/ (generated during runtime)
- Generated: qr_codes/ is created at runtime; fonts/ are static

**scripts/:**
- Purpose: Development utilities and testing
- Contains: Relay controller test scripts, raw Modbus communication tests
- Not part of production package; used for hardware debugging

## Key File Locations

**Entry Points:**
- `monitoni/main.py`: Main application startup (async main function, CLI arg parsing, component initialization)
- `monitoni/ui/app.py`: Kivy MDApp class (UI bootstrap, screen management)
- `monitoni/telemetry/server.py`: FastAPI telemetry server (creates and configures app instance)

**Configuration:**
- `config/default.yaml`: System defaults (hardware ports, LED count, timeouts, vending levels)
- `monitoni/core/config.py`: Pydantic config classes and ConfigManager singleton

**Core Logic:**
- `monitoni/core/state_machine.py`: PurchaseStateMachine class (state enum, transitions, timeout management)
- `monitoni/core/purchase_flow.py`: PurchaseFlowManager class (server polling, purchase completion)
- `monitoni/core/purchase_client.py`: PurchaseServerClient class (HTTP wrapper for purchase API)

**Testing:**
- `monitoni/core/database.py`: DatabaseManager class (SQLite async interface)
- `monitoni/core/logger.py`: Logger factory, DatabaseHandler (dual output: console + DB)

**Hardware:**
- `monitoni/hardware/base.py`: Abstract component classes (HardwareComponent, RelayController, LEDController, SensorController, AudioController)
- `monitoni/hardware/manager.py`: HardwareManager singleton pattern
- `monitoni/hardware/modbus_relay.py`: Real Modbus RTU relay + MockRelayController
- `monitoni/hardware/wled_controller.py`: WLED ArtNet controller + MockLEDController
- `monitoni/hardware/gpio_sensors.py`: GPIO sensor controller + MockSensorController
- `monitoni/hardware/audio.py`: Pygame audio controller + MockAudioController

## Naming Conventions

**Files:**
- Controllers: `{name}_controller.py` (e.g., `modbus_relay.py`, but note actual file is `wled_controller.py`)
- Managers: `manager.py` (e.g., `hardware/manager.py`)
- Core logic: {noun}.py (e.g., `state_machine.py`, `purchase_flow.py`)
- Screens: `{descriptor}_screen.py` (e.g., `customer_screen.py`, `debug_screen.py`)
- Utilities: `{feature}.py` (e.g., `icons.py`, `config.py`)

**Directories:**
- Functional domains: lowercase nouns (e.g., `core`, `hardware`, `ui`, `telemetry`)
- No feature branches in structure (flat per layer)

**Classes:**
- Controllers: `{Name}Controller` (e.g., `ModbusRelayController`, `WLEDController`)
- Managers: `{Name}Manager` (e.g., `HardwareManager`, `PurchaseFlowManager`)
- Screens: `{Name}Screen` (e.g., `CustomerScreen`, `DebugScreen`)
- Enums: Capitalized (e.g., `State`, `Event`, `LogLevel`, `HardwareStatus`)

**Functions/Methods:**
- Public: snake_case, verb-noun pattern (e.g., `handle_event`, `set_relay`, `get_status`)
- Private: _leading_underscore (e.g., `_get_next_state`, `_schedule_timeout`)
- Async: no special prefix; indicated by `async def` (e.g., `async def connect()`)

## Where to Add New Code

**New Feature (e.g., Payment Processing):**
- Primary code: `monitoni/core/payment.py` (new module in core/)
- UI integration: Add methods to `monitoni/ui/customer_screen.py` or new screen class
- Config: Add section to `monitoni/core/config.py` and `config/default.yaml`
- Tests: `scripts/test_payment.py` (if needed for development)

**New Hardware Component (e.g., Temperature Sensor):**
- Abstract class: Add to `monitoni/hardware/base.py` (e.g., `TemperatureSensorController`)
- Real implementation: `monitoni/hardware/temperature.py` with real + mock classes
- Registration: Add to `HardwareManager` initialization in `monitoni/hardware/manager.py`
- Config: Add hardware config section to `monitoni/core/config.py` and `config/default.yaml`

**New UI Screen:**
- Create file: `monitoni/ui/{descriptor}_screen.py` inheriting from Kivy `Screen`
- Register: Add to ScreenManager in `monitoni/ui/app.py` via `add_widget()`
- Callbacks: Register with state machine in app's `_setup_state_callbacks()` if needed

**Utilities/Helpers:**
- Shared helpers: `monitoni/core/{feature}.py` (e.g., `validators.py`, `formatters.py`)
- Hardware utilities: `monitoni/hardware/{feature}.py` (e.g., `color_utils.py`)
- UI utilities: `monitoni/ui/{feature}.py` (e.g., `layouts.py`)

## Special Directories

**assets/fonts/:**
- Purpose: Icon fonts for UI (Material Design icons, custom glyphs)
- Generated: No; static files committed to repo
- Committed: Yes; used at runtime by `monitoni/ui/icons.py`

**assets/qr_codes/:**
- Purpose: Temporary storage for generated QR code images
- Generated: Yes; created at runtime by `monitoni/ui/customer_screen.py`
- Committed: No; .gitignore excludes qr_codes/

**.planning/codebase/:**
- Purpose: GSD analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes; created by `/gsd:map-codebase` command
- Committed: Yes; reference for future development phases

**config/:**
- Purpose: Configuration files
- default.yaml: Version controlled, immutable defaults
- local.yaml: Machine-specific overrides (template provided as .example, .gitignore excludes local.yaml)

**scripts/:**
- Purpose: Development and debugging utilities
- Not included in package distribution
- Used for interactive hardware testing and diagnostics
