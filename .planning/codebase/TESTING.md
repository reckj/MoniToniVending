# Testing Patterns

**Analysis Date:** 2026-02-05

## Test Framework

**Runner:**
- pytest 7.4.3
- pytest-asyncio 0.21.1 (for async test support)
- Config: No pytest.ini or pyproject.toml testing section found
- Default pytest discovery applies (files named test_*.py or *_test.py)

**Run Commands:**
```bash
pytest                          # Run all tests in scripts/
pytest -v                       # Verbose output
pytest -s                       # Show print statements
pytest --asyncio-mode=auto      # Run async tests
```

**Assertion Library:**
- Standard Python `assert` statements
- No dedicated assertion library (unittest, nose, or hypothesis) detected
- No test output examples in codebase (tests under-developed)

## Test Organization

**Current State:**
- Only integration/hardware test scripts exist in `/monitoni/scripts/`:
  - `test_relay.py` - RS485 Modbus relay board communication
  - `test_relay_debug.py` - Debug variant with detailed output
  - `test_relay_raw.py` - Low-level serial communication test
- No unit test suite
- No test fixtures or factories
- No mocking infrastructure

**Location Pattern:**
- Hardware test scripts co-located in `/scripts/` directory (not ideal for standard testing)
- No parallel test directories (e.g., `tests/` or `test/` folders)
- Scripts are standalone and manually run, not pytest-integrated

**Naming:**
- Hardcoded test file names: `test_relay.py`, `test_relay_debug.py`
- Functions prefixed with `test_`: `async def test_relay()` in scripts
- Clear, descriptive names: test purpose evident from filename

## Hardware Testing Pattern

**Existing Test Scripts:**

**`monitoni/scripts/test_relay.py`:**
```python
async def test_relay():
    """Test relay board communication."""
    ports_to_try = ['/dev/ttyAMA0', '/dev/ttyAMA10', '/dev/ttyUSB0']

    for port in ports_to_try:
        try:
            controller = ModbusRelayController(port=port, ...)
            connected = await controller.connect()

            if connected:
                result = await controller.set_relay(1, True)
                state = await controller.get_relay(1)
                await controller.disconnect()
```

**Pattern Observed:**
- Async/await pattern for hardware operations
- Try/except blocks for robustness
- Clear status output (✓ success, ✗ failure)
- Device port discovery (tries multiple ports)
- Graceful error handling with helpful user messages

## Mock Components

**Strategy:**
- Mock implementations exist for all hardware components but not as formal test doubles
- Example: `monitoni/hardware/` has both real and mock versions structured by capability
- Mock classes inherit from same base: `RelayController`, `LEDController`, `SensorController`
- No unittest.mock or pytest-mock used

**Base Classes as Test Contracts:**
- `HardwareComponent` abstract base defines interface for testing:
  ```python
  class HardwareComponent(ABC):
      @abstractmethod
      async def connect(self) -> bool
      @abstractmethod
      async def health_check(self) -> bool
  ```
- Any mock or real implementation must fulfill contract
- Allows swapping implementations without changing test code

**Hardware Abstraction for Testing:**
```python
# Hardware manager accepts injected components
manager = HardwareManager(
    relay=MockRelayController(),  # Can inject mock
    led=RealLEDController(),       # Or real
    sensors=MockSensorController()
)
```

## Async Testing

**Pattern:**
- pytest-asyncio used for async test support
- Tests marked with `@pytest.mark.asyncio` (not shown in codebase, would be standard)
- async def test_*() for async test functions

**Example Usage:**
```python
async def test_relay():
    controller = ModbusRelayController(port='/dev/ttyUSB0')
    connected = await controller.connect()

    assert connected is True

    result = await controller.set_relay(1, True)
    assert result is True

    state = await controller.get_relay(1)
    assert state is True

    await controller.disconnect()
```

**Async Context Management:**
- Tests properly await async operations
- Connection/disconnection lifecycle tested
- Event loop setup handled by pytest-asyncio

## Error Testing

**Observed Patterns:**
- Exception handling tested in hardware scripts:
  ```python
  try:
      controller = ModbusRelayController(port=port, ...)
      connected = await controller.connect()
  except Exception as e:
      print(f"✗ Error on {port}: {e}")
  ```

- Status checking for error states:
  ```python
  if connected:
      # success path
  else:
      if controller.last_error:
          print(f"Error: {controller.last_error}")
  ```

- Connection failure handling:
  ```python
  if not self._client:
      if self.logger:
          self.logger.error("Purchase client not connected")
      return None
  ```

**Best Practices Not Yet Used:**
- pytest raises context manager: `with pytest.raises(ValueError):`
- Exception matching on message content
- Fixture cleanup for teardown

## Test Coverage

**Requirements:** Not enforced (no coverage config)

**View Coverage:** Not configured
```bash
# Commands would be:
pytest --cov=monitoni --cov-report=html
coverage report
```

**Current Coverage Gaps:**
- No unit tests for core modules:
  - `monitoni/core/logger.py` - Logger initialization, log levels, handlers
  - `monitoni/core/database.py` - CRUD operations, queries, transactions
  - `monitoni/core/config.py` - Configuration loading, merging, validation
  - `monitoni/core/state_machine.py` - State transitions, timeout handling
  - `monitoni/core/purchase_flow.py` - Purchase validation logic

- No UI/KivyMD tests:
  - Screen rendering and transitions
  - Button interactions and callbacks
  - Display state management

- No integration tests:
  - Hardware + telemetry server interaction
  - Purchase flow end-to-end
  - Configuration override behavior

**Risk Areas:**
- Database operations untested - risk of data corruption
- State machine transitions untested - risk of invalid state sequences
- Configuration validation limited to Pydantic - custom validators should have tests
- Error handling paths largely untested - unexpected errors likely

## Test Fixtures and Factories

**Not Currently Used:**
- No pytest fixtures defined
- No test data factories
- No shared test configuration

**Recommendation if tests added:**
```python
# Example fixture pattern (not currently in codebase)
@pytest.fixture
async def database_manager():
    db = DatabaseManager(":memory:")  # In-memory SQLite
    await db.initialize()
    yield db
    await db.close()

@pytest.fixture
async def logger_with_db(database_manager):
    logger = Logger(db_manager=database_manager)
    yield logger
```

## Testing Commands Reference

**Current available:**
```bash
# In project root, run hardware test
python scripts/test_relay.py

# Run all relay tests
for f in scripts/test_relay*.py; do python "$f"; done

# With pytest (if added):
pytest scripts/                    # Run scripts as tests
pytest -k relay                    # Filter by name
pytest --collect-only              # List without running
```

## What Should Be Tested

**Priority 1 (Core Logic):**
- `monitoni/core/state_machine.py`: State transitions, event handling, timeouts
- `monitoni/core/config.py`: Configuration loading, merging, validation
- `monitoni/core/database.py`: Insert, query, update operations

**Priority 2 (Hardware Abstraction):**
- Mock hardware components for unit testing dependent code
- Base class contract enforcement
- Error handling and reconnection logic

**Priority 3 (Business Logic):**
- Purchase validation flow
- State machine timeout triggers
- Purchase client retry logic

**Priority 4 (Integration):**
- Hardware manager initialization sequence
- Telemetry server endpoints
- Configuration persistence

## Notes on Current Test Infrastructure

**Strengths:**
- pytest and pytest-asyncio dependencies already included
- Hardware test scripts demonstrate async testing patterns
- Abstract base classes enable mock implementations

**Weaknesses:**
- No formal test suite structure
- Tests are manual scripts, not integrated into CI
- No test configuration (pytest.ini, conftest.py)
- No fixtures, factories, or shared test utilities
- No assertion patterns established (using print output instead)
- Hardware tests are more "manual verification" than automated tests

**To Improve:**
1. Create `tests/` directory structure parallel to `monitoni/`
2. Add `tests/conftest.py` with common fixtures
3. Migrate hardware scripts to `tests/hardware/`
4. Write unit tests for core modules with mocked dependencies
5. Add pytest.ini or pyproject.toml with test configuration
6. Set coverage threshold (e.g., 70% minimum)
7. Integrate tests into CI/CD pipeline

