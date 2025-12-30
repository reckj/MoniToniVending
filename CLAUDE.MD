# CLAUDE.MD - MoniToni Vending Machine System

This file provides context for Claude Code when working on the MoniToni vending machine system.

## Project Overview

MoniToni is a production-ready vending machine control system for Raspberry Pi 5, featuring:
- Hardware control (Modbus RTU relays, WLED LED strips, GPIO sensors, audio)
- KivyMD-based touchscreen UI (customer and debug interfaces)
- FastAPI telemetry server with WebSocket monitoring
- Complete state machine for purchase flow management
- Hardware abstraction layer with mock implementations for development

**Target Platform**: Raspberry Pi 5 (8GB), Raspberry Pi OS (64-bit), Python 3.11+

## Architecture

### Component Layers (Ordered by Dependency)

1. **Hardware Layer** (`monitoni/hardware/`)
   - Base abstraction: `base.py` (HardwareComponent interface)
   - Drivers: `modbus_relay.py`, `wled_controller.py`, `gpio_sensors.py`, `audio.py`
   - Manager: `manager.py` (centralized hardware access)
   - All components have mock implementations for testing without hardware

2. **Core Infrastructure** (`monitoni/core/`)
   - `config.py`: YAML-based configuration with Pydantic validation
   - `database.py`: SQLite with async operations (logs + statistics tables)
   - `logger.py`: Dual console/database logging with async writes
   - `state_machine.py`: Purchase flow state management
   - `purchase_flow.py`: Purchase server integration
   - `purchase_client.py`: HTTP client for external purchase API

3. **User Interface** (`monitoni/ui/`)
   - `app.py`: Main KivyMD application
   - `customer_screen.py`: Customer-facing product selection
   - `debug_screen.py`: PIN-protected hardware testing
   - `icons.py`: Custom icons and visual elements

4. **Telemetry Server** (`monitoni/telemetry/`)
   - `server.py`: FastAPI REST API + WebSocket server
   - Endpoints for monitoring, log downloads, remote control
   - Web dashboard frontend in `monitoni/telemetry/static/`

5. **Entry Point**
   - `monitoni/main.py`: Application startup with --mock flag support

## Key Design Patterns

### Hardware Abstraction
All hardware components implement the `HardwareComponent` abstract base class:
```python
async def connect() -> bool
async def disconnect() -> None
async def health_check() -> bool
def is_connected() -> bool
def get_status() -> Dict
```

**Important**: Always use mock implementations during development (`--mock` flag). Real hardware requires specific Raspberry Pi peripherals.

### State Machine Flow
The purchase flow is managed by a state machine with these states:
- `IDLE` → `SLEEP` (timeout) or `CHECKING_PURCHASE` (product selected)
- `CHECKING_PURCHASE` → `DOOR_UNLOCKED` (valid) or `IDLE` (invalid/timeout)
- `DOOR_UNLOCKED` → `DOOR_OPENED` (sensor) or `IDLE` (timeout)
- `DOOR_OPENED` → `COMPLETING` (door closed) or `DOOR_ALARM` (timeout)
- `DOOR_ALARM` → `COMPLETING` (door closed)
- `COMPLETING` → `IDLE` (completion sent)

**Events trigger state transitions**: user input, purchase validation, door sensors, timeouts

### Async Operations
- Database writes are async to avoid blocking the UI
- All hardware operations are async
- Network requests (purchase server, telemetry) use async HTTP/WebSocket
- Use `asyncio.create_task()` for background operations

### Configuration System
- **Default config**: `config/default.yaml` (version controlled, never modify directly)
- **Local overrides**: `config/local.yaml` (machine-specific, gitignored)
- Deep merge allows partial overrides
- Pydantic models validate all configuration

## File Structure Reference

```
monitoni/
├── monitoni/
│   ├── core/              # Core infrastructure
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # SQLite database with async operations
│   │   ├── logger.py      # Logging system (console + DB)
│   │   ├── state_machine.py  # Purchase flow state machine
│   │   ├── purchase_flow.py  # Purchase flow coordinator
│   │   └── purchase_client.py # External purchase API client
│   ├── hardware/          # Hardware abstraction + drivers
│   │   ├── base.py        # HardwareComponent base class
│   │   ├── manager.py     # Centralized hardware manager
│   │   ├── modbus_relay.py   # 32-channel relay control
│   │   ├── wled_controller.py # LED strip via ArtNet
│   │   ├── gpio_sensors.py   # Door sensor monitoring
│   │   └── audio.py       # HDMI audio output
│   ├── ui/                # KivyMD user interface
│   │   ├── app.py         # Main application
│   │   ├── customer_screen.py  # Customer UI
│   │   ├── debug_screen.py     # Debug/setup UI (PIN protected)
│   │   └── icons.py       # Custom icons
│   ├── telemetry/         # Monitoring and control
│   │   ├── server.py      # FastAPI server
│   │   └── static/        # Web dashboard frontend
│   └── main.py            # Application entry point
├── config/
│   ├── default.yaml       # Default configuration (DO NOT EDIT)
│   └── local.yaml         # Local overrides (gitignored)
├── docs/                  # Documentation
│   ├── SYSTEM.md          # Architecture details
│   ├── SETUP.md           # Installation guide
│   └── ...
├── scripts/               # Utility scripts
└── tests/                 # Test suite
```

## Development Guidelines

### Running the Application

**Development mode (with mocks)**:
```bash
python -m monitoni.main --mock
```

**Production mode (requires hardware)**:
```bash
python -m monitoni.main
```

### Testing Philosophy
- Use `--mock` flag for all development work
- Mock implementations mirror real hardware behavior
- Test state transitions without hardware dependencies
- Debug screen provides manual hardware testing on actual device

### Code Style
- Async/await for all I/O operations
- Type hints for all functions (Pydantic models for config)
- Comprehensive logging with purchase ID tracking
- Error handling with graceful degradation

### Common Tasks

**Adding a new hardware component**:
1. Create driver in `monitoni/hardware/` implementing `HardwareComponent`
2. Add mock implementation (suffix with `Mock` class)
3. Register in `HardwareManager.__init__()`
4. Add configuration section to `config/default.yaml`
5. Update Pydantic config model in `core/config.py`

**Adding a new state**:
1. Add to `State` enum in `state_machine.py`
2. Add associated events to `Event` enum
3. Update `_get_next_state()` transition logic
4. Add timeout handling if needed

**Adding a new telemetry endpoint**:
1. Add route in `telemetry/server.py`
2. Implement handler function
3. Update frontend in `telemetry/static/` if needed

### Important Notes

**Hardware Protocols**:
- Modbus RTU: RS485 serial, 9600 baud, slave address 1
- WLED: ArtNet over UDP port 6454, universe 0, 300 RGB pixels
- GPIO: BCM mode, door sensor with configurable pull resistor

**Database**:
- SQLite at path specified in config
- Two tables: `logs` (event tracking), `statistics` (metrics)
- Async writes via custom log handler
- Export functionality available via telemetry API

**Security**:
- Debug UI requires PIN (configured in `config/local.yaml`)
- Telemetry control endpoints require PIN authentication
- Local network only (no internet exposure by default)

**Purchase Flow**:
- External purchase server validates transactions
- System polls for valid purchase during CHECKING_PURCHASE state
- Purchase ID (UUID) tracks all logs for a transaction
- Completion confirmation sent after door closed

### Common Gotchas

1. **Async Context**: KivyMD runs its own event loop. Use `asyncio.create_task()` for background operations, not `asyncio.run()`.

2. **Configuration**: Never modify `config/default.yaml` directly. Always use `config/local.yaml` for machine-specific settings.

3. **Hardware Manager**: Access all hardware through `HardwareManager` instance, not directly importing drivers.

4. **State Machine**: Don't bypass state machine for purchase flow. Always emit events and let state transitions handle logic.

5. **Database Logging**: Don't write directly to database. Use Python logging module with purchase_id context.

6. **LED Zones**: LED strip has 10 zones (30 pixels each). Zone 0 = level 1, zone 9 = level 10.

7. **Relay Channels**: Motor spindles use one channel per level (channels 0-9). Door locks use separate channels (10-19).

8. **Watchdog Timer**: System will auto-reboot if main loop hangs. Ensure async operations don't block indefinitely.

## Debugging Tips

**Check state machine transitions**:
- Logs include state transitions with purchase ID
- Telemetry WebSocket streams real-time state changes

**Hardware issues**:
- Use debug screen on actual device for manual testing
- Check hardware health via telemetry API endpoint
- Review logs for connection/health check failures

**Purchase flow problems**:
- Grep logs for purchase_id to trace entire transaction
- Check state machine timeout values in config
- Verify purchase server connectivity and response format

**UI not responding**:
- Check for blocking operations (should be async)
- Review logs for exceptions in event handlers
- Verify KivyMD event loop isn't blocked

## Related Documentation

- `README.md`: Quick start guide
- `docs/SYSTEM.md`: Detailed architecture and design
- `docs/SETUP.md`: Installation and deployment
- `docs/API.md`: Telemetry server API reference
- `docs/HARDWARE.md`: Hardware setup and wiring

## Current Development

This is an active project running in production. When making changes:
- Prioritize reliability and fault tolerance
- Maintain backward compatibility with existing config files
- Add comprehensive logging for new features
- Update documentation for significant changes
- Test with mock hardware before deploying to device
