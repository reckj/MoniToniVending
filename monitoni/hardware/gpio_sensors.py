"""
GPIO sensor controller for door monitoring.

Supports both real hardware (RPi.GPIO) and mock implementation.
"""

import asyncio
from typing import Optional, Callable
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False

from monitoni.hardware.base import SensorController, HardwareStatus


class GPIOSensorController(SensorController):
    """
    Real GPIO sensor controller using RPi.GPIO.
    
    Monitors door sensor with non-blocking event-driven callbacks.
    """
    
    def __init__(
        self,
        door_pin: int,
        pull_mode: str = "up",
        active_state: str = "low"
    ):
        """
        Initialize GPIO sensor controller.
        
        Args:
            door_pin: BCM pin number for door sensor
            pull_mode: "up" or "down" for pull resistor
            active_state: "low" or "high" for active state
        """
        super().__init__("GPIOSensor")
        
        if not GPIO_AVAILABLE:
            raise ImportError("RPi.GPIO not available. Install with: pip install RPi.GPIO")
            
        self.door_pin = door_pin
        self.pull_mode = pull_mode
        self.active_state = active_state
        
        self._door_callback: Optional[Callable] = None
        self._last_door_state: Optional[bool] = None
        self._debounce_time = 0.05  # 50ms debounce
        
    async def connect(self) -> bool:
        """Initialize GPIO."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            # Set GPIO mode to BCM
            GPIO.setmode(GPIO.BCM)
            
            # Configure pull resistor
            pull = GPIO.PUD_UP if self.pull_mode == "up" else GPIO.PUD_DOWN
            
            # Setup pin as input with pull resistor
            GPIO.setup(self.door_pin, GPIO.IN, pull_up_down=pull)
            
            # Add event detection with debouncing
            GPIO.add_event_detect(
                self.door_pin,
                GPIO.BOTH,
                callback=self._gpio_callback,
                bouncetime=int(self._debounce_time * 1000)
            )
            
            # Read initial state
            self._last_door_state = await self.get_door_state()
            
            self.status = HardwareStatus.CONNECTED
            self.last_error = None
            return True
            
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Cleanup GPIO."""
        try:
            GPIO.remove_event_detect(self.door_pin)
            GPIO.cleanup(self.door_pin)
        except Exception:
            pass
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check GPIO health."""
        if not self.is_connected():
            return False
            
        try:
            # Try to read pin state
            GPIO.input(self.door_pin)
            return True
        except Exception:
            return False
            
    async def get_door_state(self) -> Optional[bool]:
        """
        Get door sensor state.
        
        Returns:
            True if door open, False if closed
        """
        if not self.is_connected():
            return None
            
        try:
            pin_state = GPIO.input(self.door_pin)
            
            # Determine if door is open based on active state
            if self.active_state == "low":
                is_open = not pin_state  # LOW = active = open
            else:
                is_open = pin_state  # HIGH = active = open
                
            return is_open
            
        except Exception as e:
            self.last_error = str(e)
            return None
            
    def set_door_callback(self, callback: Callable) -> None:
        """Set callback for door state changes."""
        self._door_callback = callback
        
    def _gpio_callback(self, channel: int) -> None:
        """
        GPIO interrupt callback.
        
        Called by RPi.GPIO when pin state changes.
        """
        # This runs in GPIO's thread, so we need to be careful
        try:
            pin_state = GPIO.input(self.door_pin)
            
            # Determine door state
            if self.active_state == "low":
                is_open = not pin_state
            else:
                is_open = pin_state
                
            # Only call callback if state actually changed
            if is_open != self._last_door_state:
                self._last_door_state = is_open
                
                if self._door_callback:
                    # Schedule callback in event loop
                    asyncio.create_task(self._async_callback(is_open))
                    
        except Exception as e:
            self.last_error = str(e)
            
    async def _async_callback(self, is_open: bool) -> None:
        """Async wrapper for door callback."""
        if self._door_callback:
            if asyncio.iscoroutinefunction(self._door_callback):
                await self._door_callback(is_open)
            else:
                self._door_callback(is_open)


class MockSensorController(SensorController):
    """Mock sensor controller for testing without hardware."""
    
    def __init__(self):
        """Initialize mock sensor controller."""
        super().__init__("MockSensor")
        self._door_open = False
        self._door_callback: Optional[Callable] = None
        
    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(0.1)
        self.status = HardwareStatus.CONNECTED
        return True
        
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_connected()
        
    async def get_door_state(self) -> Optional[bool]:
        """Get mock door state."""
        if not self.is_connected():
            return None
        return self._door_open
        
    def set_door_callback(self, callback: Callable) -> None:
        """Set door callback."""
        self._door_callback = callback
        
    async def simulate_door_open(self) -> None:
        """Simulate door opening (for testing)."""
        if self._door_open:
            return
            
        self._door_open = True
        print("[MOCK] Sensor: Door OPENED")
        
        if self._door_callback:
            if asyncio.iscoroutinefunction(self._door_callback):
                await self._door_callback(True)
            else:
                self._door_callback(True)
                
    async def simulate_door_close(self) -> None:
        """Simulate door closing (for testing)."""
        if not self._door_open:
            return
            
        self._door_open = False
        print("[MOCK] Sensor: Door CLOSED")
        
        if self._door_callback:
            if asyncio.iscoroutinefunction(self._door_callback):
                await self._door_callback(False)
            else:
                self._door_callback(False)
