# Technology Stack

**Analysis Date:** 2026-02-05

## Languages

**Primary:**
- Python 3.11+ - Full application codebase (hardware control, UI, telemetry server)

## Runtime

**Environment:**
- Raspberry Pi 5 (8GB recommended)
- Raspberry Pi OS 64-bit
- Linux kernel 6.12.47+ (armv7l/aarch64)

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` (present)

## Frameworks

**Core:**
- FastAPI 0.104.1 - RESTful telemetry server with WebSocket support
- Uvicorn 0.24.0 - ASGI server for FastAPI
- KivyMD 1.1.1 - Material Design UI framework for touchscreen interface
- Kivy 2.2.1 - Underlying GUI framework

**Hardware Communication:**
- pymodbus 3.5.4 - Modbus RTU protocol for relay control
- stupidArtnet 1.4.1 - ArtNet protocol for WLED LED strip control
- RPi.GPIO 0.7.1 - GPIO sensor control (Raspberry Pi only)

**Audio:**
- pygame 2.5.2 - Audio playback for user feedback

**Configuration & Validation:**
- pydantic 2.5.0 - Data validation and settings management
- pydantic-settings 2.1.0 - Environment-based configuration
- PyYAML 6.0.1 - YAML configuration file parsing

**Database:**
- aiosqlite 0.19.0 - Async SQLite database operations (event logging, statistics)

**Testing & Development:**
- pytest 7.4.3 - Test framework
- pytest-asyncio 0.21.1 - Async test support
- black 23.11.0 - Code formatter

**HTTP Client:**
- httpx 0.25.2 - Async HTTP client for purchase server integration
- websockets 12.0 - WebSocket protocol support

**Environment:**
- python-dotenv 1.0.0 - Environment variable loading from .env files

## Key Dependencies

**Critical:**
- FastAPI/Uvicorn - Core telemetry server infrastructure enabling remote monitoring and control
- pymodbus - Enables communication with 32-channel Modbus RTU relay board for spindle motors and door locks
- stupidArtnet - Enables communication with WLED LED controller via ArtNet for visual feedback
- aiosqlite - Event logging database critical for troubleshooting and compliance

**Infrastructure:**
- KivyMD/Kivy - Complete touchscreen user interface
- RPi.GPIO - Door sensor input on Raspberry Pi GPIO
- pygame - Audio feedback system

## Configuration

**Environment:**
- Config path resolution: `config/default.yaml` (version controlled) + `config/local.yaml` (machine-specific overrides, gitignored)
- Environment-based overrides via `python-dotenv` and pydantic-settings
- Configuration manager: `monitoni.core.config.ConfigManager`

**Build:**
- No build tool required (pure Python application)
- Entry point: `python -m monitoni.main`
- CLI arguments: `--mock` (use mock hardware), `--debug` (debug logging), `--test` (hardware test mode)

## Platform Requirements

**Development:**
- Python 3.11+
- pip package manager
- Linux/Unix environment recommended for serial port access

**Production:**
- Raspberry Pi 5 (8GB RAM recommended)
- Raspberry Pi OS 64-bit
- Waveshare 7.9" HDMI Capacitive Touch display (400x1280 resolution)
- Ethernet connection recommended for telemetry server access
- Modbus RTU relay board accessible via `/dev/ttySC0` (RS485 via Waveshare SC16IS752 UART board)
- WLED LED controller on network (default IP: 192.168.1.100)
- Watchdog timer enabled for automatic recovery (60s timeout default)

## Startup & Entry Points

**Main Application:**
- Location: `monitoni/main.py`
- Starts three concurrent systems:
  1. Hardware manager (relay, LED, GPIO, audio controllers)
  2. Telemetry server (FastAPI on port 8000 by default)
  3. KivyMD UI application (blocking, runs main event loop)
- Lifecycle: Config → Database init → Hardware init → Telemetry server (background thread) → UI startup

**Hardware Abstraction:**
- Base classes: `monitoni/hardware/base.py`
- Implementations:
  - Modbus relay: `monitoni/hardware/modbus_relay.py`
  - WLED LED: `monitoni/hardware/wled_controller.py`
  - GPIO sensors: `monitoni/hardware/gpio_sensors.py`
  - Audio (Pygame): `monitoni/hardware/audio.py`
- Manager: `monitoni/hardware/manager.py` (auto-selects real/mock implementations)

**Telemetry Server:**
- Location: `monitoni/telemetry/server.py`
- Runs in background thread via Uvicorn
- FastAPI instance: `TelemetryServer.app`
- Endpoints: REST API + WebSocket at `/ws`

**Database:**
- Location: `monitoni/core/database.py`
- Async SQLite manager using aiosqlite
- Auto-initialized at startup
- Stores logs, statistics, purchase records

---

*Stack analysis: 2026-02-05*
