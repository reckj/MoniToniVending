"""
WLED LED controller via ArtNet protocol.

Supports both real hardware (WLED via ArtNet) and mock implementation.
"""

import asyncio
import math
from typing import Optional, List, Tuple, Dict, Any
try:
    from stupidArtnet import StupidArtnet
    ARTNET_AVAILABLE = True
except ImportError:
    ARTNET_AVAILABLE = False

from monitoni.hardware.base import LEDController, HardwareStatus


class WLEDController(LEDController):
    """
    Real WLED LED controller via ArtNet.
    
    Controls addressable LED strips through WLED controller.
    """
    
    def __init__(
        self,
        ip_address: str,
        universe: int = 0,
        pixel_count: int = 300,
        fps: int = 30,
        zones: List[List[int]] = None
    ):
        """
        Initialize WLED controller.
        
        Args:
            ip_address: WLED controller IP address
            universe: ArtNet universe
            pixel_count: Total number of LEDs
            fps: Frames per second for animations
            zones: LED zones as [[start, end], ...] pairs
        """
        super().__init__("WLED")
        
        if not ARTNET_AVAILABLE:
            raise ImportError("stupidArtnet not available. Install with: pip install stupidArtnet")
            
        self.ip_address = ip_address
        self.universe = universe
        self.pixel_count = pixel_count
        self.fps = fps
        self.zones = zones or []
        
        self.artnet: Optional[StupidArtnet] = None
        self._current_brightness = 1.0
        self._animation_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> bool:
        """Connect to WLED controller."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            # Initialize ArtNet
            # Each pixel needs 3 bytes (RGB)
            packet_size = self.pixel_count * 3
            
            self.artnet = StupidArtnet(
                targetIP=self.ip_address,
                universe=self.universe,
                packet_size=packet_size,
                fps=self.fps
            )
            
            self.artnet.start()
            
            # Test connection by setting all LEDs to black
            await self.turn_off()
            
            self.status = HardwareStatus.CONNECTED
            self.last_error = None
            return True
            
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from WLED."""
        # Stop any running animation
        if self._animation_task and not self._animation_task.done():
            self._animation_task.cancel()
            
        # Turn off LEDs
        await self.turn_off()
        
        if self.artnet:
            self.artnet.stop()
            self.artnet = None
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check WLED connection health."""
        return self.is_connected() and self.artnet is not None
        
    async def set_color(self, r: int, g: int, b: int, brightness: float = 1.0) -> bool:
        """Set solid color for all LEDs."""
        if not self.is_connected():
            return False
            
        try:
            # Apply brightness
            r = int(r * brightness)
            g = int(g * brightness)
            b = int(b * brightness)
            
            # Create pixel array
            pixels = [r, g, b] * self.pixel_count
            
            self.artnet.set(pixels)
            self.artnet.show()
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def set_zone_color(
        self,
        zone: int,
        r: int,
        g: int,
        b: int,
        brightness: float = 1.0
    ) -> bool:
        """Set color for specific zone."""
        if not self.is_connected():
            return False
            
        if zone < 0 or zone >= len(self.zones):
            self.last_error = f"Invalid zone: {zone}"
            return False
            
        try:
            # Apply brightness
            r = int(r * brightness)
            g = int(g * brightness)
            b = int(b * brightness)
            
            # Get zone range
            start, end = self.zones[zone]
            
            # Get current pixel data
            current_pixels = self.artnet.get()
            
            # Update zone pixels
            for i in range(start, end + 1):
                idx = i * 3
                current_pixels[idx] = r
                current_pixels[idx + 1] = g
                current_pixels[idx + 2] = b
                
            self.artnet.set(current_pixels)
            self.artnet.show()
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def set_zone_pixels(
        self,
        start: int,
        end: int,
        r: int,
        g: int,
        b: int,
        brightness: float = 1.0
    ) -> bool:
        """Set color for specific pixel range (direct control)."""
        if not self.is_connected():
            return False
            
        try:
            # Apply brightness
            r = int(r * brightness)
            g = int(g * brightness)
            b = int(b * brightness)
            
            # Clamp to valid range
            start = max(0, min(start, self.pixel_count - 1))
            end = max(0, min(end, self.pixel_count - 1))
            
            # Get current pixel data
            current_pixels = list(self.artnet.get())
            
            # Update zone pixels
            for i in range(start, end + 1):
                idx = i * 3
                current_pixels[idx] = r
                current_pixels[idx + 1] = g
                current_pixels[idx + 2] = b
                
            self.artnet.set(current_pixels)
            self.artnet.show()
            
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def play_animation(self, animation_name: str) -> bool:
        """Play predefined animation."""
        # Stop any running animation
        if self._animation_task and not self._animation_task.done():
            self._animation_task.cancel()
            
        # Start new animation
        self._animation_task = asyncio.create_task(
            self._run_animation(animation_name)
        )
        
        return True
        
    async def _run_animation(self, animation_name: str) -> None:
        """Run animation loop."""
        # This is a simplified version - in production, load from config
        try:
            if animation_name == "rainbow_chase":
                await self._rainbow_chase()
            elif animation_name == "breathing":
                await self._breathing(0, 50, 100)
            elif animation_name == "flash":
                await self._flash(255, 0, 0, flashes=3)
            else:
                # Default to solid color
                await self.set_color(0, 150, 255)
        except asyncio.CancelledError:
            pass
            
    async def _rainbow_chase(self, duration: float = 3.0) -> None:
        """Rainbow chase animation."""
        steps = int(duration * self.fps)
        
        for step in range(steps):
            pixels = []
            for i in range(self.pixel_count):
                hue = (i + step * 5) % 360
                r, g, b = self._hsv_to_rgb(hue, 1.0, 1.0)
                pixels.extend([r, g, b])
                
            self.artnet.set(pixels)
            self.artnet.show()
            await asyncio.sleep(1.0 / self.fps)
            
    async def _breathing(self, r: int, g: int, b: int, speed: float = 2.0) -> None:
        """Breathing animation (loops until cancelled)."""
        while True:
            # Fade in
            for i in range(100):
                brightness = i / 100.0
                await self.set_color(r, g, b, brightness)
                await asyncio.sleep(speed / 100.0)
                
            # Fade out
            for i in range(100, 0, -1):
                brightness = i / 100.0
                await self.set_color(r, g, b, brightness)
                await asyncio.sleep(speed / 100.0)
                
    async def _flash(self, r: int, g: int, b: int, flashes: int = 3) -> None:
        """Flash animation."""
        for _ in range(flashes):
            await self.set_color(r, g, b, 1.0)
            await asyncio.sleep(0.2)
            await self.turn_off()
            await asyncio.sleep(0.2)
            
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """Convert HSV to RGB."""
        h = h / 360.0
        c = v * s
        x = c * (1 - abs((h * 6) % 2 - 1))
        m = v - c
        
        if h < 1/6:
            r, g, b = c, x, 0
        elif h < 2/6:
            r, g, b = x, c, 0
        elif h < 3/6:
            r, g, b = 0, c, x
        elif h < 4/6:
            r, g, b = 0, x, c
        elif h < 5/6:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
            
        return (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255)
        )
        
    async def set_brightness(self, brightness: float) -> bool:
        """Set global brightness."""
        self._current_brightness = max(0.0, min(1.0, brightness))
        return True
        
    async def turn_off(self) -> bool:
        """Turn off all LEDs."""
        return await self.set_color(0, 0, 0, 1.0)


class MockLEDController(LEDController):
    """Mock LED controller for testing without hardware."""
    
    def __init__(self, pixel_count: int = 300, zones: List[List[int]] = None):
        """Initialize mock LED controller."""
        super().__init__("MockLED")
        self.pixel_count = pixel_count
        self.zones = zones or []
        self._pixels = [(0, 0, 0)] * pixel_count
        self._brightness = 1.0
        
    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(0.1)
        self.status = HardwareStatus.CONNECTED
        return True
        
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._pixels = [(0, 0, 0)] * self.pixel_count
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_connected()
        
    async def set_color(self, r: int, g: int, b: int, brightness: float = 1.0) -> bool:
        """Set mock color."""
        if not self.is_connected():
            return False
            
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        self._pixels = [(r, g, b)] * self.pixel_count
        print(f"[MOCK] LED: All pixels set to RGB({r}, {g}, {b})")
        return True
        
    async def set_zone_color(
        self,
        zone: int,
        r: int,
        g: int,
        b: int,
        brightness: float = 1.0
    ) -> bool:
        """Set mock zone color."""
        if not self.is_connected() or zone >= len(self.zones):
            return False
            
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        start, end = self.zones[zone]
        for i in range(start, end + 1):
            self._pixels[i] = (r, g, b)
            
        print(f"[MOCK] LED: Zone {zone} set to RGB({r}, {g}, {b})")
        return True
        
    async def set_zone_pixels(
        self,
        start: int,
        end: int,
        r: int,
        g: int,
        b: int,
        brightness: float = 1.0
    ) -> bool:
        """Set color for specific pixel range (direct control)."""
        if not self.is_connected():
            return False
            
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        # Clamp to valid range
        start = max(0, min(start, self.pixel_count - 1))
        end = max(0, min(end, self.pixel_count - 1))
        
        for i in range(start, end + 1):
            self._pixels[i] = (r, g, b)
            
        print(f"[MOCK] LED: Pixels {start}-{end} set to RGB({r}, {g}, {b})")
        return True
        
    async def play_animation(self, animation_name: str) -> bool:
        """Play mock animation."""
        print(f"[MOCK] LED: Playing animation '{animation_name}'")
        return True
        
    async def set_brightness(self, brightness: float) -> bool:
        """Set mock brightness."""
        self._brightness = brightness
        print(f"[MOCK] LED: Brightness set to {brightness:.2f}")
        return True
        
    async def turn_off(self) -> bool:
        """Turn off mock LEDs."""
        return await self.set_color(0, 0, 0)
