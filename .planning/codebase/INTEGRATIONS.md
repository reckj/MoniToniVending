# External Integrations

**Analysis Date:** 2026-02-05

## APIs & External Services

**Purchase Server:**
- External payment/authorization service
  - SDK/Client: `monitoni/core/purchase_client.py` (httpx AsyncClient)
  - Base URL: Configurable at `purchase_server.base_url` (default: `http://localhost:5000`)
  - Endpoints:
    - `POST /api/purchase/check` - Validate product level availability
    - `POST /api/purchase/complete` - Notify server of completed purchase
  - Auth: Machine ID passed in requests
  - Timeout: 5.0 seconds (configurable)
  - Retry: Up to 3 attempts (configurable)
  - Poll interval: 0.5 seconds

**WLED LED Controller (Network):**
- Web-based LED controller for addressable LED strips
  - Protocol: ArtNet (Art-Net DMX over UDP)
  - SDK/Client: `stupidArtnet==1.4.0` library
  - IP address: Configurable at `hardware.wled.ip_address` (default: `192.168.1.100`)
  - Universe: 0 (configurable)
  - Pixel count: 300 total LEDs (configurable)
  - FPS: 30 (configurable)
  - Implementation: `monitoni/hardware/wled_controller.py`
  - Controls:
    - Solid colors (idle, sleep, error states)
    - Animations (rainbow chase, breathing, flashing)
    - Zone-specific highlighting (per product level)

## Data Storage

**Databases:**
- SQLite (local file-based)
  - Path: `data/monitoni.db` (configurable via `database.path`)
  - Client: aiosqlite (async wrapper)
  - Connection: Pooled single async connection
  - Tables:
    - `logs` - Event logging with level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - Purchase tracking
    - System statistics
  - Indexes: timestamp and purchase_id for fast queries
  - Schema creation: Auto-initialized on first run via `DatabaseManager._create_tables()`

**File Storage:**
- Local filesystem only
  - Config files: `config/default.yaml`, `config/local.yaml`
  - Logs: `logs/monitoni.log` (rotating file, 10MB max per file, 5 backups)
  - Audio files: `assets/sounds/` (success.wav, error.wav, alarm.wav)

**Caching:**
- Hardware state caching (relay states, LED colors, audio volume) in memory
- No external caching service used

## Authentication & Identity

**Auth Provider:**
- Custom implementation
  - PIN-based: 4-digit debug PIN for telemetry API control endpoints
  - PIN storage: Configuration value at `telemetry.debug_pin` (default: "1234", should override in `local.yaml`)
  - Verification: String comparison in `TelemetryServer._verify_pin()`
  - Scope: Protects `/api/debug/` endpoints (relay, LED, audio control)
  - Machine ID: Configured at `system.machine_id` for purchase server identification

## Monitoring & Observability

**Error Tracking:**
- None detected (no third-party error tracking service)

**Logs:**
- Built-in async logging to:
  1. Console (real-time output)
  2. Rotating file at `logs/monitoni.log` (10MB max, 5 backups)
  3. SQLite database via `DatabaseManager`
- Logger: `monitoni/core/logger.py`
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL (configurable via `logging.level`)
- Context: Timestamps, log levels, purchase IDs, structured details

## CI/CD & Deployment

**Hosting:**
- Raspberry Pi 5 (8GB RAM) running Raspberry Pi OS 64-bit
- No cloud hosting used

**CI Pipeline:**
- None detected

**Hardware Communication:**
- Serial/RS485: Modbus RTU to relay board via `/dev/ttySC0` (9600 baud, configurable)
- Network: ArtNet UDP to WLED controller on local network
- GPIO: Direct pin control via RPi.GPIO for door sensor (BCM GPIO 5)
- Audio: Direct ALSA/HDMI output via pygame

## Environment Configuration

**Required env vars:**
- None detected as strictly required
- Optional: Can load from `.env` via `python-dotenv`

**Configuration files (required):**
- `config/default.yaml` - Provides all default settings
- `config/local.yaml` - Optional machine-specific overrides (Git-ignored)

**Critical config settings to override in local.yaml:**
- `system.machine_id` - Unique identifier for this vending machine
- `hardware.wled.ip_address` - IP of WLED controller
- `purchase_server.base_url` - URL of payment/authorization server
- `telemetry.debug_pin` - PIN for API access (security-critical)

**Secrets location:**
- Config files with sensitive values (`telemetry.debug_pin`, URLs, ports)
- Git-ignored `config/local.yaml` contains overrides
- `.env` file support via `python-dotenv` (if used)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- Purchase completion callbacks to purchase server
  - Endpoint: `POST {purchase_server.base_url}/api/purchase/complete`
  - Payload: Machine ID, level, success status
  - Retries: Up to 3 attempts with timeout

## Hardware Protocols

**Modbus RTU (Serial):**
- Relay board control (32 channels)
- Protocol: Modbus RTU over RS485
- Serial port: `/dev/ttySC0` (Waveshare SC16IS752 UART expander)
- Baud rate: 9600 (configurable)
- Slave address: 1 (configurable)
- Implementation: `monitoni/hardware/modbus_relay.py`
- CRC calculation: Custom implementation for packet integrity

**ArtNet over UDP:**
- LED controller communication
- DMX512 over Ethernet protocol
- IP: Configurable (192.168.1.100 default)
- UDP port: Standard ArtNet (6454)
- Library: `stupidArtnet`

**GPIO (Direct Pin Control):**
- Door sensor monitoring
- Pin: BCM GPIO 5 (Raspberry Pi physical pin 29)
- Pull mode: Up (configurable)
- Active state: Low (configurable, door open = LOW)

## System Integration Points

**State Machine:**
- File: `monitoni/core/state_machine.py`
- Tracks machine state (IDLE, SLEEPING, PURCHASING, etc.)
- Broadcasts state changes via WebSocket to telemetry clients

**Purchase Flow:**
- File: `monitoni/core/purchase_flow.py`
- Orchestrates hardware calls (motor spin, door lock/unlock)
- Communicates with purchase server for validation
- Logs all transactions to database

**UI Integration:**
- File: `monitoni/ui/app.py` (main Kivy app)
- Files: `monitoni/ui/customer_screen.py`, `monitoni/ui/debug_screen.py`
- Receives hardware events and state updates
- Sends user commands to hardware manager

**Telemetry Broadcasting:**
- WebSocket client connections receive real-time updates
- Events: hardware changes, state transitions, purchase completion
- Broadcast method: `TelemetryServer._broadcast()`

---

*Integration audit: 2026-02-05*
