"""
Hardware manager coordinating all hardware components.

Provides centralized hardware access and automatic mock fallback.
"""

import asyncio
from typing import Optional, Dict, Any
from monitoni.core.config import Config
from monitoni.hardware.base import HardwareComponent
from monitoni.hardware.modbus_relay import ModbusRelayController, MockRelayController
from monitoni.hardware.wled_controller import WLEDController, MockLEDController
from monitoni.hardware.gpio_sensors import GPIOSensorController, MockSensorController
from monitoni.hardware.audio import PygameAudioController, MockAudioController


class HardwareManager:
    """
    Manages all hardware components.
    
    Automatically selects real or mock implementations based on:
    - Configuration settings (enabled flags)
    - Hardware availability
    - Mock mode flag
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
        
        self.relay: Optional[ModbusRelayController | MockRelayController] = None
        self.led: Optional[WLEDController | MockLEDController] = None
        self.sensor: Optional[GPIOSensorController | MockSensorController] = None
        self.audio: Optional[PygameAudioController | MockAudioController] = None
        
        self._initialized = False
        
    async def initialize(self) -> Dict[str, bool]:
        """
        Initialize all hardware components.
        
        Returns:
            Dictionary with initialization status for each component
        """
        results = {}
        
        # Initialize relay controller
        if self.config.hardware.modbus.enabled:
            results['relay'] = await self._init_relay()
        else:
            results['relay'] = False
            
        # Initialize LED controller
        if self.config.hardware.wled.enabled:
            results['led'] = await self._init_led()
        else:
            results['led'] = False
            
        # Initialize sensor controller
        if self.config.hardware.gpio.enabled:
            results['sensor'] = await self._init_sensor()
        else:
            results['sensor'] = False
            
        # Initialize audio controller
        if self.config.hardware.audio.enabled:
            results['audio'] = await self._init_audio()
        else:
            results['audio'] = False
            
        self._initialized = True
        return results
        
    async def _init_relay(self) -> bool:
        """Initialize relay controller."""
        try:
            if self.use_mock:
                self.relay = MockRelayController()
            else:
                try:
                    self.relay = ModbusRelayController(
                        port=self.config.hardware.modbus.port,
                        baudrate=self.config.hardware.modbus.baudrate,
                        slave_address=self.config.hardware.modbus.slave_address,
                        timeout=self.config.hardware.modbus.timeout
                    )
                except ImportError:
                    print("Modbus library not available, using mock")
                    self.relay = MockRelayController()
                    
            return await self.relay.connect()
            
        except Exception as e:
            print(f"Failed to initialize relay: {e}")
            # Fallback to mock
            self.relay = MockRelayController()
            return await self.relay.connect()
            
    async def _init_led(self) -> bool:
        """Initialize LED controller."""
        try:
            zones = self.config.led.zones
            animations = self.config.led.animations

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
                        zones=zones,
                        animations=animations
                    )
                except ImportError:
                    print("ArtNet library not available, using mock")
                    self.led = MockLEDController(
                        pixel_count=self.config.hardware.wled.pixel_count,
                        zones=zones
                    )

            return await self.led.connect()

        except Exception as e:
            print(f"Failed to initialize LED: {e}")
            # Fallback to mock
            self.led = MockLEDController(
                pixel_count=self.config.hardware.wled.pixel_count,
                zones=self.config.led.zones
            )
            return await self.led.connect()
            
    async def _init_sensor(self) -> bool:
        """Initialize sensor controller."""
        try:
            if self.use_mock:
                self.sensor = MockSensorController()
            else:
                try:
                    self.sensor = GPIOSensorController(
                        door_pin=self.config.hardware.gpio.door_sensor_pin,
                        pull_mode=self.config.hardware.gpio.door_sensor_pull,
                        active_state=self.config.hardware.gpio.door_sensor_active
                    )
                except ImportError:
                    print("GPIO library not available, using mock")
                    self.sensor = MockSensorController()
                    
            return await self.sensor.connect()
            
        except Exception as e:
            print(f"Failed to initialize sensor: {e}")
            # Fallback to mock
            self.sensor = MockSensorController()
            return await self.sensor.connect()
            
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
                    print("Pygame not available, using mock")
                    self.audio = MockAudioController(
                        volume=self.config.hardware.audio.volume,
                        sounds=sounds
                    )
                    
            return await self.audio.connect()
            
        except Exception as e:
            print(f"Failed to initialize audio: {e}")
            # Fallback to mock
            self.audio = MockAudioController(
                volume=self.config.hardware.audio.volume,
                sounds=self.config.audio.sounds
            )
            return await self.audio.connect()
            
    async def shutdown(self) -> None:
        """Shutdown all hardware components."""
        components = [self.relay, self.led, self.sensor, self.audio]
        
        for component in components:
            if component and component.is_connected():
                try:
                    await component.disconnect()
                except Exception as e:
                    print(f"Error disconnecting {component.name}: {e}")
                    
        self._initialized = False
        
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all components.
        
        Returns:
            Dictionary with health status for each component
        """
        results = {}
        
        if self.relay:
            results['relay'] = await self.relay.health_check()
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
            Dictionary with status information
        """
        status = {
            'initialized': self._initialized,
            'components': {}
        }
        
        if self.relay:
            status['components']['relay'] = self.relay.get_status()
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
        
        Args:
            duration_ms: Duration in milliseconds
            
        Returns:
            True if successful
        """
        if not self.relay:
            return False
            
        motor_channel = self.config.vending.motor.relay_channel
        
        # Turn on motor
        if not await self.relay.set_relay(motor_channel, True):
            return False
            
        # Wait for duration
        await asyncio.sleep(duration_ms / 1000.0)
        
        # Turn off motor
        return await self.relay.set_relay(motor_channel, False)
        
    async def unlock_door(self, level: int) -> bool:
        """
        Unlock door for specific level.
        
        Args:
            level: Product level (1-10)
            
        Returns:
            True if successful
        """
        if not self.relay or level < 1 or level > len(self.config.vending.door_lock.relay_channels):
            return False
            
        channel = self.config.vending.door_lock.relay_channels[level - 1]
        return await self.relay.set_relay(channel, True)
        
    async def lock_door(self, level: int) -> bool:
        """
        Lock door for specific level.
        
        Args:
            level: Product level (1-10)
            
        Returns:
            True if successful
        """
        if not self.relay or level < 1 or level > len(self.config.vending.door_lock.relay_channels):
            return False
            
        channel = self.config.vending.door_lock.relay_channels[level - 1]
        return await self.relay.set_relay(channel, False)


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
