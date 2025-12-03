"""
Audio controller for sound effects.

Supports both real hardware (pygame) and mock implementation.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict
try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from monitoni.hardware.base import AudioController, HardwareStatus


class PygameAudioController(AudioController):
    """
    Real audio controller using pygame mixer.
    
    Plays sound effects via HDMI audio output.
    """
    
    def __init__(self, volume: float = 0.7, sounds: Dict[str, str] = None):
        """
        Initialize audio controller.
        
        Args:
            volume: Initial volume (0.0-1.0)
            sounds: Dictionary mapping sound names to file paths
        """
        super().__init__("PygameAudio")
        
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame not available. Install with: pip install pygame")
            
        self.volume = max(0.0, min(1.0, volume))
        self.sounds = sounds or {}
        self._loaded_sounds: Dict[str, pygame.mixer.Sound] = {}
        
    async def connect(self) -> bool:
        """Initialize pygame mixer."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            # Initialize mixer
            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=512
            )
            
            # Set volume
            pygame.mixer.music.set_volume(self.volume)
            
            # Preload sounds
            for name, path in self.sounds.items():
                await self._load_sound(name, path)
                
            self.status = HardwareStatus.CONNECTED
            self.last_error = None
            return True
            
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Cleanup pygame mixer."""
        try:
            await self.stop_all()
            pygame.mixer.quit()
            self._loaded_sounds.clear()
        except Exception:
            pass
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check audio health."""
        if not self.is_connected():
            return False
            
        try:
            # Check if mixer is initialized
            return pygame.mixer.get_init() is not None
        except Exception:
            return False
            
    async def _load_sound(self, name: str, path: str) -> bool:
        """
        Load a sound file.
        
        Args:
            name: Sound name
            path: Path to sound file
            
        Returns:
            True if loaded successfully
        """
        try:
            sound_path = Path(path)
            
            if not sound_path.exists():
                self.last_error = f"Sound file not found: {path}"
                return False
                
            sound = pygame.mixer.Sound(str(sound_path))
            sound.set_volume(self.volume)
            self._loaded_sounds[name] = sound
            
            return True
            
        except Exception as e:
            self.last_error = f"Failed to load sound {name}: {e}"
            return False
            
    async def play_sound(self, sound_name: str) -> bool:
        """Play sound effect."""
        if not self.is_connected():
            return False
            
        try:
            # Load sound if not already loaded
            if sound_name not in self._loaded_sounds:
                if sound_name in self.sounds:
                    await self._load_sound(sound_name, self.sounds[sound_name])
                else:
                    self.last_error = f"Unknown sound: {sound_name}"
                    return False
                    
            # Play sound
            if sound_name in self._loaded_sounds:
                self._loaded_sounds[sound_name].play()
                return True
            else:
                return False
                
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def set_volume(self, volume: float) -> bool:
        """Set audio volume."""
        self.volume = max(0.0, min(1.0, volume))
        
        if not self.is_connected():
            return True  # Just store the value
            
        try:
            # Update volume for all loaded sounds
            for sound in self._loaded_sounds.values():
                sound.set_volume(self.volume)
                
            pygame.mixer.music.set_volume(self.volume)
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def stop_all(self) -> bool:
        """Stop all playing sounds."""
        if not self.is_connected():
            return False
            
        try:
            pygame.mixer.stop()
            return True
        except Exception as e:
            self.last_error = str(e)
            return False


class MockAudioController(AudioController):
    """Mock audio controller for testing without hardware."""
    
    def __init__(self, volume: float = 0.7, sounds: Dict[str, str] = None):
        """Initialize mock audio controller."""
        super().__init__("MockAudio")
        self.volume = volume
        self.sounds = sounds or {}
        self._playing_sounds: list = []
        
    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(0.1)
        self.status = HardwareStatus.CONNECTED
        return True
        
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._playing_sounds.clear()
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_connected()
        
    async def play_sound(self, sound_name: str) -> bool:
        """Play mock sound."""
        if not self.is_connected():
            return False
            
        if sound_name not in self.sounds:
            print(f"[MOCK] Audio: Unknown sound '{sound_name}'")
            return False
            
        self._playing_sounds.append(sound_name)
        print(f"[MOCK] Audio: Playing '{sound_name}' at volume {self.volume:.2f}")
        
        # Simulate sound duration
        asyncio.create_task(self._remove_after_delay(sound_name, 1.0))
        
        return True
        
    async def _remove_after_delay(self, sound_name: str, delay: float) -> None:
        """Remove sound from playing list after delay."""
        await asyncio.sleep(delay)
        if sound_name in self._playing_sounds:
            self._playing_sounds.remove(sound_name)
            
    async def set_volume(self, volume: float) -> bool:
        """Set mock volume."""
        self.volume = max(0.0, min(1.0, volume))
        print(f"[MOCK] Audio: Volume set to {self.volume:.2f}")
        return True
        
    async def stop_all(self) -> bool:
        """Stop all mock sounds."""
        if self._playing_sounds:
            print(f"[MOCK] Audio: Stopping {len(self._playing_sounds)} sounds")
        self._playing_sounds.clear()
        return True
