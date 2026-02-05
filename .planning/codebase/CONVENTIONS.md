# Coding Conventions

**Analysis Date:** 2026-02-05

## Naming Patterns

**Files:**
- Snake case for module names: `modbus_relay.py`, `gpio_sensors.py`, `state_machine.py`
- Domain-organized: hardware modules in `monitoni/hardware/`, core logic in `monitoni/core/`
- Descriptive names indicating purpose: `purchase_client.py` (external server client), `logger.py` (logging system)

**Classes:**
- PascalCase (CapWords): `DatabaseManager`, `PurchaseStateMachine`, `VendingApp`
- Base/abstract classes use semantic suffixes: `HardwareComponent`, `RelayController`, `LEDController`
- Implementation-specific prefixes: `ModbusRelayController`, `PygameAudioController`, `GPIOSensorController`
- Pydantic models/responses use semantic names: `LogEntry`, `StatusResponse`, `ConfigUpdateRequest`

**Functions:**
- Snake case: `get_database()`, `check_purchase()`, `set_event_loop()`
- Async functions clearly marked: `async def initialize(self)`, `async def connect(self)`
- Method prefixes for type clarity:
  - `get_*`: Retrieve data without side effects (`get_logs()`, `get_status()`)
  - `set_*`: Modify state (`set_relay()`, `set_color()`)
  - `_*`: Private/internal methods (`_create_tables()`, `_deep_merge()`)

**Variables:**
- Snake case: `purchase_id`, `relay_states`, `sleep_timeout`
- Boolean prefixes for clarity: `is_connected()`, `GPIOD_AVAILABLE`, `_stop_monitoring`
- Descriptive iteration variables: `for log_data in self._pending_logs`
- State tracking with clear naming: `_last_activity`, `_timeout_task`, `previous_state`

**Enums & Constants:**
- UPPER_CASE for Enum values: `State.IDLE`, `Event.PURCHASE_VALID`, `LogLevel.INFO`
- Inherit from `str` for JSON/API serialization: `class LogLevel(str, Enum)`
- Domain-specific enum files alongside usage: Enums defined in same module as consumer

## Code Style

**Formatting:**
- Black formatter is a dependency (`black==23.11.0` in requirements.txt)
- 4-space indentation (Python standard)
- Import statements organized by groups

**Linting:**
- No formal linting config detected (no .flake8, .pylintrc)
- Code follows PEP 8 conventions naturally
- Type hints used throughout for clarity

**Docstring Format:**
- Google-style docstrings with sections:
  ```python
  def __init__(self, name: str, level: str = "INFO"):
      """
      Initialize logger.

      Args:
          name: Logger name
          level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
      """
  ```
- Module-level docstrings describe purpose: `"""Logging system for MoniToni vending machine."""`
- Class docstrings explain role and state management
- Method docstrings include Args, Returns, Raises when applicable

## Import Organization

**Order:**
1. Standard library: `import asyncio`, `import json`, `from pathlib import Path`
2. Third-party packages: `from pydantic import BaseModel`, `import httpx`, `from kivy.app import App`
3. Internal modules: `from monitoni.core.config import get_config`

**Path Aliases:**
- Absolute imports used throughout: `from monitoni.core.database import DatabaseManager`
- No relative imports (no `from . import x` patterns)
- Project root added to path when needed: `sys.path.insert(0, str(Path(__file__).parent.parent))`

**Module Organization:**
- Barrel files used selectively: `monitoni/core/__init__.py` remains empty
- Direct imports preferred: `from monitoni.core.logger import get_logger()`

## Error Handling

**Patterns:**
- Explicit exception handling with context preservation:
  ```python
  try:
      self._connection = await aiosqlite.connect(str(self.db_path))
  except Exception as e:
      self.last_error = str(e)
      self.status = HardwareStatus.ERROR
  ```
- Graceful degradation in critical paths:
  - Logging errors don't crash app: `except Exception as e: print(f"Error writing log: {e}", file=sys.stderr)`
  - Hardware failures set status but allow continuation: `if not self._client: return None`
- Custom exceptions not used; standard exceptions preferred
- Exception details logged with context: `logger.error(f"Failed to connect: {e}")`

**Return Convention for Error Reporting:**
- Boolean returns for success/failure: `async def connect(self) -> bool:`
- `None` return for recoverable errors: `async def check_purchase(...) -> Optional[Dict]:`
- Last error stored on component: `self.last_error = None` (cleared on success)

## Validation

**Pydantic Models:**
- Used extensively for configuration and API schemas:
  ```python
  class ModbusConfig(BaseModel):
      enabled: bool = True
      port: str = "/dev/ttyUSB0"
      baudrate: int = 9600
  ```
- Custom validators for complex rules:
  ```python
  @validator('zones')
  def validate_zones(cls, v):
      for zone in v:
          if len(zone) != 2 or zone[0] >= zone[1]:
              raise ValueError(f"Invalid zone: {zone}")
      return v
  ```
- Field constraints via Field descriptors:
  ```python
  volume: float = Field(default=0.7, ge=0.0, le=1.0)
  ```

## Logging

**Framework:** Python's standard `logging` module

**Custom Handler:**
- `DatabaseHandler` in `monitoni/core/logger.py` extends `logging.Handler`
- Async operations queued until event loop ready
- Integration with database via `DatabaseManager`

**Patterns:**
- Use Logger wrapper methods: `logger.info()`, `logger.error()`, `logger.exception()`
- Include context when available:
  ```python
  logger.info("Purchase completed", purchase_id=purchase_id)
  logger.error("Connection failed", details={'port': port, 'error': str(e)})
  ```
- Exception logging includes traceback: `logger.exception(message)` captures full stack
- Level-specific methods encourage proper classification (INFO vs WARNING vs ERROR)

**Outputs:**
1. Console (stderr for handlers, stdout for app)
2. File (rotating, max 10MB, keep 5 backups)
3. Database (via DatabaseHandler, for telemetry queries)

## Comments

**When to Comment:**
- Complex algorithms explained: Modbus CRC calculation commented
- Non-obvious business logic: "Door left open too long triggers alarm"
- Workarounds documented: "Note: debounce handled in software with edge event filtering"
- Hardware-specific details: "Pi 5 uses gpiochip4 for the main GPIO header"
- External protocol references: Modbus RTU implementation notes

**Docstrings vs Comments:**
- Methods: Always include docstrings (Args, Returns, Raises)
- Complex blocks: Inline comments for business logic
- State transitions: Comments explain why state changes occur

## Function Design

**Size:** Functions are focused, typically 10-50 lines
- Connection logic isolated: `async def connect()`
- Specific operations single-purpose: `async def set_relay(channel, state)`
- Business logic extracted: Purchase validation separate from state management

**Parameters:**
- Explicit over implicit: Pass logger/config as arguments, don't rely on globals
- Type hints on all parameters: `async def add_log(self, level: LogLevel, message: str, ...)`
- Optional parameters have defaults: `purchase_id: Optional[str] = None`
- Avoid long parameter lists (max 4-5 explicit params, use config objects for many settings)

**Return Values:**
- Consistent return types: Boolean for success/failure, None for errors
- Clear semantic: `-> Dict[str, Any]` for data returns, `-> bool` for operations
- Use Optional for nullable returns: `-> Optional[Dict]`

## Module Design

**Exports:**
- Classes and module-level functions exported at module level
- Global instances managed via factory functions: `get_config()`, `get_database()`, `get_logger()`
- No `__all__` lists (all public symbols accessible)

**Hardware Abstraction:**
- Base classes define interface: `HardwareComponent`, `RelayController`, `LEDController`
- Mock implementations for testing: Each component has real and mock versions
- Consistent connection lifecycle: `connect()`, `disconnect()`, `health_check()`

**Configuration Pattern:**
- Pydantic nested models match hierarchy: `Config.hardware.modbus`, `Config.vending.motor`
- Factory function pattern: `get_config_manager()` returns singleton
- Override support: default.yaml + local.yaml merge

**Async Patterns:**
- Async used for I/O-bound operations: database, hardware, HTTP
- Sync functions where appropriate: configuration loading
- Event loop injection: `set_event_loop()` methods pass loop to handlers

