"""
GPIO sensor controller for door monitoring.

Supports both real hardware (gpiod for Pi 5) and mock implementation.
Uses gpiod (libgpiod) for Raspberry Pi 5 compatibility.
"""

import asyncio
import threading
from typing import Optional, Callable

try:
    import gpiod
    from gpiod.line import Direction, Bias, Value, Edge
    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False

from monitoni.hardware.base import SensorController, HardwareStatus


class GPIOSensorController(SensorController):
    """
    Real GPIO sensor controller using gpiod (libgpiod).
    
    Monitors door sensor with event-driven callbacks.
    Compatible with Raspberry Pi 5.
    """
    
    # Pi 5 uses gpiochip4 for the main GPIO header
    GPIO_CHIP = "/dev/gpiochip4"
    
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
        
        if not GPIOD_AVAILABLE:
            raise ImportError("gpiod not available. Install with: pip install gpiod")
            
        self.door_pin = door_pin
        self.pull_mode = pull_mode
        self.active_state = active_state
        
        self._chip: Optional[gpiod.Chip] = None
        self._line_request = None
        self._door_callback: Optional[Callable] = None
        self._last_door_state: Optional[bool] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
    async def connect(self) -> bool:
        """Initialize GPIO."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            # Open GPIO chip
            self._chip = gpiod.Chip(self.GPIO_CHIP)
            
            # Configure pull resistor
            if self.pull_mode == "up":
                bias = Bias.PULL_UP
            elif self.pull_mode == "down":
                bias = Bias.PULL_DOWN
            else:
                bias = Bias.DISABLED
            
            # Configure line settings with edge detection
            config = gpiod.LineSettings(
                direction=Direction.INPUT,
                bias=bias,
                edge_detection=Edge.BOTH  # Detect both rising and falling edges
                # Note: debounce handled in software with edge event filtering
            )
            
            # Request the line
            self._line_request = self._chip.request_lines(
                consumer="monitoni-door-sensor",
                config={self.door_pin: config}
            )
            
            # Read initial state
            self._last_door_state = await self.get_door_state()
            
            # Start monitoring thread for events
            self._stop_monitoring.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_events,
                daemon=True
            )
            self._monitor_thread.start()
            
            self.status = HardwareStatus.CONNECTED
            self.last_error = None
            return True
            
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Cleanup GPIO."""
        # Stop monitoring thread
        self._stop_monitoring.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
            
        # Release line request
        if self._line_request:
            self._line_request.release()
            self._line_request = None
            
        # Close chip
        if self._chip:
            self._chip.close()
            self._chip = None
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check GPIO health."""
        if not self.is_connected():
            return False
            
        try:
            # Try to read pin state
            if self._line_request:
                self._line_request.get_value(self.door_pin)
                return True
            return False
        except Exception:
            return False
            
    async def get_door_state(self) -> Optional[bool]:
        """
        Get door sensor state.
        
        Returns:
            True if door open, False if closed
        """
        if not self.is_connected() or not self._line_request:
            return None
            
        try:
            value = self._line_request.get_value(self.door_pin)
            
            # Determine if door is open based on active state
            # Value.ACTIVE = 1, Value.INACTIVE = 0
            pin_high = (value == Value.ACTIVE)
            
            if self.active_state == "low":
                is_open = not pin_high  # LOW = active = open
            else:
                is_open = pin_high  # HIGH = active = open
                
            return is_open
            
        except Exception as e:
            self.last_error = str(e)
            return None
            
    def set_door_callback(self, callback: Callable) -> None:
        """Set callback for door state changes."""
        self._door_callback = callback
        
    def _monitor_events(self) -> None:
        """
        Monitor GPIO events in a background thread.
        
        This handles edge detection and calls the door callback.
        """
        while not self._stop_monitoring.is_set():
            try:
                if not self._line_request:
                    break
                    
                # Wait for events with timeout
                if self._line_request.wait_edge_events(timeout=0.5):
                    # Read events
                    events = self._line_request.read_edge_events()
                    
                    for event in events:
                        # Get current door state
                        value = self._line_request.get_value(self.door_pin)
                        pin_high = (value == Value.ACTIVE)
                        
                        if self.active_state == "low":
                            is_open = not pin_high
                        else:
                            is_open = pin_high
                        
                        # Only call callback if state changed
                        if is_open != self._last_door_state:
                            self._last_door_state = is_open
                            
                            if self._door_callback:
                                # Schedule callback
                                self._schedule_callback(is_open)
                                
            except Exception as e:
                if not self._stop_monitoring.is_set():
                    self.last_error = str(e)
                break
                
    def _schedule_callback(self, is_open: bool) -> None:
        """Schedule the door callback to run."""
        if self._door_callback:
            # Run callback in thread (it may or may not be async)
            try:
                if asyncio.iscoroutinefunction(self._door_callback):
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(self._door_callback(is_open))
                    finally:
                        loop.close()
                else:
                    self._door_callback(is_open)
            except Exception as e:
                self.last_error = str(e)


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
