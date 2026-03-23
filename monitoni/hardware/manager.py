"""
Hardware manager coordinating all hardware components.

Provides centralized hardware access with dual relay module support,
transport-aware initialization, and automatic mock fallback.

Phase 02.1: Dual Ethernet relay migration
- relay_core  (8-CH Module C): motor, spindle, digital inputs
- relay_levels (30-CH module): door locks per level
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from monitoni.core.config import Config
from monitoni.hardware.base import HardwareComponent, RelayController, DigitalInputController
from monitoni.hardware.modbus_relay import ModbusRelayController, MockRelayController
from monitoni.hardware.modbus_tcp_relay import EthernetRelayController
from monitoni.hardware.modbus_digital_input import ModbusDigitalInputController, MockDigitalInputController
from monitoni.hardware.wled_controller import WLEDController, MockLEDController
from monitoni.hardware.gpio_sensors import GPIOSensorController, MockSensorController
from monitoni.hardware.audio import PygameAudioController, MockAudioController

logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Manages all hardware components.

    Automatically selects real or mock implementations based on:
    - Configuration settings (enabled flags, transport, method)
    - Hardware availability
    - Mock mode flag

    Dual relay modules (Phase 02.1):
    - relay_core  — 8-CH Waveshare module for motor/spindle/machine control
    - relay_levels — 30-CH Waveshare module for door lock control per level

    Partial operation: if one module fails to connect, the other still initializes.
    App can run with one module down (degraded mode).
    """

    def __init__(self, config: Config, use_mock: bool = False):
        """
        Initialize hardware manager.

        Args:
            config: System configuration
            use_mock: Force mock implementations
        """
        self.config = config
        self.use_mock = use_mock

        self.relay_core: Optional[RelayController] = None    # 8-CH: motor/spindle
        self.relay_levels: Optional[RelayController] = None  # 30-CH: door locks
        self.led: Optional[WLEDController | MockLEDController] = None
        self.sensor: Optional[Any] = None  # SensorController or DigitalInputController
        self.audio: Optional[PygameAudioController | MockAudioController] = None

        self._initialized = False

    @property
    def relay(self) -> Optional[RelayController]:
        """DEPRECATED: use relay_core. Backward-compat alias for relay_core."""
        return self.relay_core

    async def initialize(self) -> Dict[str, bool]:
        """
        Initialize all hardware components.

        Returns:
            Dictionary with initialization status for each component.
            Keys: relay_core, relay_levels, sensor, led, audio.
        """
        results: Dict[str, bool] = {}

        # Initialize relay_core (8-CH module — motor, spindle, DI)
        results['relay_core'] = await self._init_relay_core()

        # Initialize relay_levels (30-CH module — door locks)
        results['relay_levels'] = await self._init_relay_levels()

        # Initialize sensor (GPIO or Modbus DI, based on config)
        results['sensor'] = await self._init_sensor()

        # Initialize LED controller
        if self.config.hardware.wled.enabled:
            results['led'] = await self._init_led()
        else:
            results['led'] = False

        # Initialize audio controller
        if self.config.hardware.audio.enabled:
            results['audio'] = await self._init_audio()
        else:
            results['audio'] = False

        self._initialized = True
        return results

    async def _init_relay_core(self) -> bool:
        """
        Initialize relay_core controller (8-CH module for motor/spindle).

        Falls back to legacy modbus serial config if relay_core section is absent.
        Falls back to MockRelayController on connection failure (partial operation).
        """
        try:
            if self.use_mock:
                self.relay_core = MockRelayController()
                return await self.relay_core.connect()

            relay_core_cfg = self.config.hardware.relay_core

            if relay_core_cfg is None:
                # Legacy fallback: use old serial modbus config
                logger.info("No relay_core config found — falling back to legacy ModbusRelayController")
                try:
                    self.relay_core = ModbusRelayController(
                        port=self.config.hardware.modbus.port,
                        baudrate=self.config.hardware.modbus.baudrate,
                        slave_address=self.config.hardware.modbus.slave_address,
                        timeout=self.config.hardware.modbus.timeout,
                    )
                except ImportError:
                    logger.warning("Modbus serial library not available, using mock for relay_core")
                    self.relay_core = MockRelayController()
                    return await self.relay_core.connect()
            elif relay_core_cfg.transport == "tcp":
                self.relay_core = EthernetRelayController(
                    host=relay_core_cfg.host,
                    port=relay_core_cfg.port,
                    slave_address=relay_core_cfg.slave_address,
                    timeout=relay_core_cfg.timeout,
                    max_channels=relay_core_cfg.max_channels,
                )
            elif relay_core_cfg.transport == "serial":
                try:
                    self.relay_core = ModbusRelayController(
                        port=relay_core_cfg.serial_port,
                        baudrate=relay_core_cfg.baudrate,
                        slave_address=relay_core_cfg.slave_address,
                        timeout=relay_core_cfg.timeout,
                    )
                except ImportError:
                    logger.warning("Modbus serial library not available, using mock for relay_core")
                    self.relay_core = MockRelayController()
                    return await self.relay_core.connect()
            else:
                logger.warning(f"Unknown relay_core transport '{relay_core_cfg.transport}', using mock")
                self.relay_core = MockRelayController()
                return await self.relay_core.connect()

            connected = await self.relay_core.connect()
            if not connected:
                logger.error(
                    f"relay_core failed to connect (last_error={self.relay_core.last_error}). "
                    "Falling back to mock — partial operation."
                )
                self.relay_core = MockRelayController()
                return await self.relay_core.connect()

            # Start reconnect loop for TCP controllers
            if isinstance(self.relay_core, EthernetRelayController):
                await self.relay_core.start_reconnect_loop()

            return True

        except Exception as e:
            logger.error(f"Unexpected error initializing relay_core: {e}. Using mock.")
            self.relay_core = MockRelayController()
            return await self.relay_core.connect()

    async def _init_relay_levels(self) -> bool:
        """
        Initialize relay_levels controller (30-CH module for door locks).

        If relay_levels config section is absent, creates a MockRelayController
        (levels module is new and may not yet be configured on all machines).
        Falls back to MockRelayController on connection failure (partial operation).
        """
        try:
            if self.use_mock:
                self.relay_levels = MockRelayController()
                return await self.relay_levels.connect()

            relay_levels_cfg = self.config.hardware.relay_levels

            if relay_levels_cfg is None:
                # Levels module not yet configured — use mock
                logger.info(
                    "No relay_levels config found — using mock (module not yet configured)"
                )
                self.relay_levels = MockRelayController()
                return await self.relay_levels.connect()
            elif relay_levels_cfg.transport == "tcp":
                self.relay_levels = EthernetRelayController(
                    host=relay_levels_cfg.host,
                    port=relay_levels_cfg.port,
                    slave_address=relay_levels_cfg.slave_address,
                    timeout=relay_levels_cfg.timeout,
                    max_channels=relay_levels_cfg.max_channels,
                )
            elif relay_levels_cfg.transport == "serial":
                try:
                    self.relay_levels = ModbusRelayController(
                        port=relay_levels_cfg.serial_port,
                        baudrate=relay_levels_cfg.baudrate,
                        slave_address=relay_levels_cfg.slave_address,
                        timeout=relay_levels_cfg.timeout,
                    )
                except ImportError:
                    logger.warning("Modbus serial library not available, using mock for relay_levels")
                    self.relay_levels = MockRelayController()
                    return await self.relay_levels.connect()
            else:
                logger.warning(f"Unknown relay_levels transport '{relay_levels_cfg.transport}', using mock")
                self.relay_levels = MockRelayController()
                return await self.relay_levels.connect()

            connected = await self.relay_levels.connect()
            if not connected:
                logger.error(
                    f"relay_levels failed to connect (last_error={self.relay_levels.last_error}). "
                    "Falling back to mock — partial operation."
                )
                self.relay_levels = MockRelayController()
                return await self.relay_levels.connect()

            # Start reconnect loop for TCP controllers
            if isinstance(self.relay_levels, EthernetRelayController):
                await self.relay_levels.start_reconnect_loop()

            return True

        except Exception as e:
            logger.error(f"Unexpected error initializing relay_levels: {e}. Using mock.")
            self.relay_levels = MockRelayController()
            return await self.relay_levels.connect()

    async def _init_sensor(self) -> bool:
        """
        Initialize sensor controller.

        Dispatches on door_sensor.method:
        - "modbus_di": ModbusDigitalInputController (DI on relay_core module)
        - "gpio" (default): GPIOSensorController

        Falls back to appropriate mock on failure.
        """
        try:
            door_sensor_cfg = self.config.hardware.door_sensor
            method = door_sensor_cfg.method if door_sensor_cfg is not None else "gpio"

            if self.use_mock:
                if method == "modbus_di":
                    di_index = door_sensor_cfg.di_index if door_sensor_cfg else 0
                    self.sensor = MockDigitalInputController(door_di_index=di_index)
                else:
                    self.sensor = MockSensorController()
                return await self.sensor.connect()

            if method == "modbus_di":
                # DI is physically on the relay_core (8-CH) module
                relay_core_cfg = self.config.hardware.relay_core
                if relay_core_cfg is None:
                    logger.warning(
                        "door_sensor.method=modbus_di but no relay_core config — using mock DI"
                    )
                    di_index = door_sensor_cfg.di_index if door_sensor_cfg else 0
                    self.sensor = MockDigitalInputController(door_di_index=di_index)
                    return await self.sensor.connect()

                di_index = door_sensor_cfg.di_index if door_sensor_cfg else 0
                poll_interval_ms = door_sensor_cfg.poll_interval_ms if door_sensor_cfg else 150

                try:
                    self.sensor = ModbusDigitalInputController(
                        host=relay_core_cfg.host,
                        port=relay_core_cfg.port,
                        slave_address=relay_core_cfg.slave_address,
                        timeout=relay_core_cfg.timeout,
                        door_di_index=di_index,
                        poll_interval_ms=poll_interval_ms,
                    )
                except ImportError:
                    logger.warning("Modbus library not available for DI sensor, using mock")
                    self.sensor = MockDigitalInputController(door_di_index=di_index)
                    return await self.sensor.connect()

                connected = await self.sensor.connect()
                if not connected:
                    logger.error(
                        f"ModbusDigitalInputController failed to connect: "
                        f"{self.sensor.last_error}. Using mock DI."
                    )
                    self.sensor = MockDigitalInputController(door_di_index=di_index)
                    return await self.sensor.connect()

                return True

            else:
                # GPIO method (default / legacy)
                gpio_cfg = self.config.hardware.gpio
                if not gpio_cfg.enabled:
                    logger.info("GPIO sensor disabled in config — using mock sensor")
                    self.sensor = MockSensorController()
                    return await self.sensor.connect()

                try:
                    self.sensor = GPIOSensorController(
                        door_pin=gpio_cfg.door_sensor_pin,
                        pull_mode=gpio_cfg.door_sensor_pull,
                        active_state=gpio_cfg.door_sensor_active,
                    )
                except ImportError:
                    logger.warning("GPIO library not available, using mock sensor")
                    self.sensor = MockSensorController()
                    return await self.sensor.connect()

                connected = await self.sensor.connect()
                if not connected:
                    logger.error(
                        f"GPIOSensorController failed to connect: {self.sensor.last_error}. "
                        "Using mock sensor."
                    )
                    self.sensor = MockSensorController()
                    return await self.sensor.connect()

                return True

        except Exception as e:
            logger.error(f"Unexpected error initializing sensor: {e}. Using mock.")
            self.sensor = MockSensorController()
            return await self.sensor.connect()

    async def _init_led(self) -> bool:
        """Initialize LED controller."""
        try:
            zones = self.config.led.zones

            if self.use_mock:
                self.led = MockLEDController(
                    pixel_count=self.config.hardware.wled.pixel_count,
                    zones=zones
                )
            else:
                try:
                    self.led = WLEDController(
                        ip_address=self.config.hardware.wled.ip_address,
                        universe=self.config.hardware.wled.universe,
                        pixel_count=self.config.hardware.wled.pixel_count,
                        fps=self.config.hardware.wled.fps,
                        zones=zones
                    )
                except ImportError:
                    logger.warning("ArtNet library not available, using mock LED")
                    self.led = MockLEDController(
                        pixel_count=self.config.hardware.wled.pixel_count,
                        zones=zones
                    )

            return await self.led.connect()

        except Exception as e:
            logger.error(f"Failed to initialize LED: {e}")
            self.led = MockLEDController(
                pixel_count=self.config.hardware.wled.pixel_count,
                zones=self.config.led.zones
            )
            return await self.led.connect()

    async def _init_audio(self) -> bool:
        """Initialize audio controller."""
        try:
            sounds = self.config.audio.sounds

            if self.use_mock:
                self.audio = MockAudioController(
                    volume=self.config.hardware.audio.volume,
                    sounds=sounds
                )
            else:
                try:
                    self.audio = PygameAudioController(
                        volume=self.config.hardware.audio.volume,
                        sounds=sounds
                    )
                except ImportError:
                    logger.warning("Pygame not available, using mock audio")
                    self.audio = MockAudioController(
                        volume=self.config.hardware.audio.volume,
                        sounds=sounds
                    )

            return await self.audio.connect()

        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self.audio = MockAudioController(
                volume=self.config.hardware.audio.volume,
                sounds=self.config.audio.sounds
            )
            return await self.audio.connect()

    async def shutdown(self) -> None:
        """
        Shutdown all hardware components.

        For TCP relay controllers: stops reconnect loop before disconnect.
        """
        # Stop reconnect loops on TCP relay controllers first
        for ctrl in (self.relay_core, self.relay_levels):
            if isinstance(ctrl, EthernetRelayController):
                try:
                    await ctrl.stop_reconnect_loop()
                except Exception as e:
                    logger.error(f"Error stopping reconnect loop for {ctrl.name}: {e}")

        components = [self.relay_core, self.relay_levels, self.led, self.sensor, self.audio]

        for component in components:
            if component and component.is_connected():
                try:
                    await component.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting {component.name}: {e}")

        self._initialized = False

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all components.

        Returns:
            Dictionary with health status for each component.
            Keys: relay_core, relay_levels, led, sensor, audio.
        """
        results: Dict[str, bool] = {}

        if self.relay_core:
            results['relay_core'] = await self.relay_core.health_check()
        if self.relay_levels:
            results['relay_levels'] = await self.relay_levels.health_check()
        if self.led:
            results['led'] = await self.led.health_check()
        if self.sensor:
            results['sensor'] = await self.sensor.health_check()
        if self.audio:
            results['audio'] = await self.audio.health_check()

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all hardware components.

        Returns:
            Dictionary with status information for each component.
        """
        status: Dict[str, Any] = {
            'initialized': self._initialized,
            'components': {}
        }

        if self.relay_core:
            core_status = self.relay_core.get_status()
            if isinstance(self.relay_core, EthernetRelayController):
                core_status['connection_info'] = self.relay_core.connection_info
            status['components']['relay_core'] = core_status

        if self.relay_levels:
            levels_status = self.relay_levels.get_status()
            if isinstance(self.relay_levels, EthernetRelayController):
                levels_status['connection_info'] = self.relay_levels.connection_info
            status['components']['relay_levels'] = levels_status

        if self.led:
            status['components']['led'] = self.led.get_status()
        if self.sensor:
            status['components']['sensor'] = self.sensor.get_status()
        if self.audio:
            status['components']['audio'] = self.audio.get_status()

        return status

    # Convenience methods for motor and door lock control

    async def spin_motor(self, duration_ms: int) -> bool:
        """
        Spin motor for specified duration.

        Routes to relay_core (8-CH module).

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            True if successful
        """
        if not self.relay_core:
            return False

        motor_channel = self.config.vending.motor.relay_channel

        # Turn on motor
        if not await self.relay_core.set_relay(motor_channel, True):
            return False

        # Wait for duration
        await asyncio.sleep(duration_ms / 1000.0)

        # Turn off motor
        return await self.relay_core.set_relay(motor_channel, False)

    async def unlock_door(self, level: int) -> bool:
        """
        Unlock door for specific level.

        Routes to relay_levels (30-CH module).

        Args:
            level: Product level (1-N)

        Returns:
            True if successful
        """
        if not self.relay_levels:
            return False

        if level < 1 or level > len(self.config.vending.door_lock.relay_channels):
            return False

        channel = self.config.vending.door_lock.relay_channels[level - 1]
        return await self.relay_levels.set_relay(channel, True)

    async def lock_door(self, level: int) -> bool:
        """
        Lock door for specific level.

        Routes to relay_levels (30-CH module).

        Args:
            level: Product level (1-N)

        Returns:
            True if successful
        """
        if not self.relay_levels:
            return False

        if level < 1 or level > len(self.config.vending.door_lock.relay_channels):
            return False

        channel = self.config.vending.door_lock.relay_channels[level - 1]
        return await self.relay_levels.set_relay(channel, False)


# Global hardware manager instance
_hardware_manager: Optional[HardwareManager] = None


def get_hardware_manager() -> Optional[HardwareManager]:
    """
    Get global hardware manager instance.

    Returns:
        HardwareManager instance or None if not initialized
    """
    return _hardware_manager


async def initialize_hardware(config: Config, use_mock: bool = False) -> HardwareManager:
    """
    Initialize global hardware manager.

    Args:
        config: System configuration
        use_mock: Force mock implementations

    Returns:
        Initialized HardwareManager
    """
    global _hardware_manager

    _hardware_manager = HardwareManager(config, use_mock)
    await _hardware_manager.initialize()

    return _hardware_manager


async def shutdown_hardware() -> None:
    """Shutdown global hardware manager."""
    global _hardware_manager

    if _hardware_manager:
        await _hardware_manager.shutdown()
        _hardware_manager = None
