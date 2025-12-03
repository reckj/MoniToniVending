"""
Hardware abstraction layer base classes.

Defines interfaces for all hardware components with both real and mock implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum


class HardwareStatus(str, Enum):
    """Hardware component status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class HardwareComponent(ABC):
    """
    Base class for all hardware components.
    
    Provides common interface for connection, health checking, and status.
    """
    
    def __init__(self, name: str):
        """
        Initialize hardware component.
        
        Args:
            name: Component name for logging
        """
        self.name = name
        self.status = HardwareStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to hardware.
        
        Returns:
            True if connection successful
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from hardware."""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check hardware health.
        
        Returns:
            True if hardware is healthy
        """
        pass
        
    def is_connected(self) -> bool:
        """Check if hardware is connected."""
        return self.status == HardwareStatus.CONNECTED
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get component status.
        
        Returns:
            Status dictionary
        """
        return {
            'name': self.name,
            'status': self.status.value,
            'last_error': self.last_error
        }


class RelayController(HardwareComponent):
    """Abstract relay controller interface."""
    
    @abstractmethod
    async def set_relay(self, channel: int, state: bool) -> bool:
        """
        Set relay state.
        
        Args:
            channel: Relay channel number (1-32)
            state: True for ON, False for OFF
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def get_relay(self, channel: int) -> Optional[bool]:
        """
        Get relay state.
        
        Args:
            channel: Relay channel number
            
        Returns:
            Relay state or None if error
        """
        pass
        
    @abstractmethod
    async def set_all_relays(self, state: bool) -> bool:
        """
        Set all relays to same state.
        
        Args:
            state: True for ON, False for OFF
            
        Returns:
            True if successful
        """
        pass


class LEDController(HardwareComponent):
    """Abstract LED controller interface."""
    
    @abstractmethod
    async def set_color(self, r: int, g: int, b: int, brightness: float = 1.0) -> bool:
        """
        Set solid color for all LEDs.
        
        Args:
            r: Red (0-255)
            g: Green (0-255)
            b: Blue (0-255)
            brightness: Brightness (0.0-1.0)
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def set_zone_color(
        self,
        zone: int,
        r: int,
        g: int,
        b: int,
        brightness: float = 1.0
    ) -> bool:
        """
        Set color for specific zone.
        
        Args:
            zone: Zone number (0-9 for 10 levels)
            r: Red (0-255)
            g: Green (0-255)
            b: Blue (0-255)
            brightness: Brightness (0.0-1.0)
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def play_animation(self, animation_name: str) -> bool:
        """
        Play predefined animation.
        
        Args:
            animation_name: Animation name from config
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def set_brightness(self, brightness: float) -> bool:
        """
        Set global brightness.
        
        Args:
            brightness: Brightness (0.0-1.0)
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def turn_off(self) -> bool:
        """
        Turn off all LEDs.
        
        Returns:
            True if successful
        """
        pass


class SensorController(HardwareComponent):
    """Abstract sensor controller interface."""
    
    @abstractmethod
    async def get_door_state(self) -> Optional[bool]:
        """
        Get door sensor state.
        
        Returns:
            True if door open, False if closed, None if error
        """
        pass
        
    @abstractmethod
    def set_door_callback(self, callback) -> None:
        """
        Set callback for door state changes.
        
        Args:
            callback: Callback function(is_open: bool)
        """
        pass


class AudioController(HardwareComponent):
    """Abstract audio controller interface."""
    
    @abstractmethod
    async def play_sound(self, sound_name: str) -> bool:
        """
        Play sound effect.
        
        Args:
            sound_name: Sound name from config
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def set_volume(self, volume: float) -> bool:
        """
        Set audio volume.
        
        Args:
            volume: Volume (0.0-1.0)
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def stop_all(self) -> bool:
        """
        Stop all playing sounds.
        
        Returns:
            True if successful
        """
        pass
