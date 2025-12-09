"""
Configuration management for MoniToni vending machine system.

Loads configuration from YAML files with override support:
1. config/default.yaml (version controlled defaults)
2. config/local.yaml (machine-specific overrides, gitignored)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, validator


class ModbusConfig(BaseModel):
    """Modbus RTU configuration."""
    enabled: bool = True
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    slave_address: int = 1
    timeout: float = 1.0


class WLEDConfig(BaseModel):
    """WLED LED controller configuration."""
    enabled: bool = True
    ip_address: str
    universe: int = 0
    fps: int = 30
    pixel_count: int = 300


class GPIOConfig(BaseModel):
    """GPIO sensor configuration."""
    enabled: bool = True
    door_sensor_pin: int = 17
    door_sensor_pull: str = "up"
    door_sensor_active: str = "low"


class AudioHardwareConfig(BaseModel):
    """Audio hardware configuration."""
    enabled: bool = True
    volume: float = Field(default=0.7, ge=0.0, le=1.0)


class HardwareConfig(BaseModel):
    """Hardware configuration."""
    modbus: ModbusConfig
    wled: WLEDConfig
    gpio: GPIOConfig
    audio: AudioHardwareConfig


class MotorConfig(BaseModel):
    """Motor control configuration."""
    relay_channel: int = 1
    spin_delay_ms: int = 500
    spindle_lock_relay: int = 12
    spindle_pre_delay_ms: int = 200
    spindle_post_delay_ms: int = 100


class DoorLockConfig(BaseModel):
    """Door lock configuration."""
    relay_channels: List[int]
    unlock_duration_s: int = 30


class TimingsConfig(BaseModel):
    """System timing configuration."""
    sleep_timeout_s: int = 60
    door_alarm_delay_s: int = 10
    purchase_timeout_s: int = 120


class VendingConfig(BaseModel):
    """Vending machine configuration."""
    levels: int = 10
    motor: MotorConfig
    door_lock: DoorLockConfig
    timings: TimingsConfig


class LEDZone(BaseModel):
    """LED zone definition (start, end pixel indices)."""
    start: int
    end: int


class AnimationConfig(BaseModel):
    """LED animation configuration."""
    type: str
    color: Optional[List[int]] = None
    brightness: float = Field(ge=0.0, le=1.0)
    speed: Optional[float] = None
    duration_s: Optional[float] = None
    flashes: Optional[int] = None


class LEDConfig(BaseModel):
    """LED configuration."""
    zones: List[List[int]]  # List of [start, end] pairs
    animations: Dict[str, Dict[str, Any]]
    
    @validator('zones')
    def validate_zones(cls, v):
        """Ensure zones are valid [start, end] pairs."""
        for zone in v:
            if len(zone) != 2 or zone[0] >= zone[1]:
                raise ValueError(f"Invalid zone: {zone}")
        return v


class AudioConfig(BaseModel):
    """Audio configuration."""
    sounds: Dict[str, str]


class PurchaseServerConfig(BaseModel):
    """Purchase server configuration."""
    enabled: bool = True
    base_url: str
    endpoints: Dict[str, str]
    poll_interval_s: float = 0.5
    timeout_s: float = 5.0
    retry_attempts: int = 3


class TelemetryConfig(BaseModel):
    """Telemetry server configuration."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    debug_pin: str


class DatabaseConfig(BaseModel):
    """Database configuration."""
    path: str = "data/monitoni.db"


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    console: bool = True
    file: bool = True
    file_path: str = "logs/monitoni.log"
    max_file_size_mb: int = 10
    backup_count: int = 5


class UIConfig(BaseModel):
    """UI configuration."""
    screen_width: int = 400
    screen_height: int = 1280
    fullscreen: bool = True
    theme: str = "Dark"
    primary_palette: str = "Blue"


class WatchdogConfig(BaseModel):
    """Watchdog configuration."""
    enabled: bool = True
    timeout_s: int = 60


class SystemConfig(BaseModel):
    """System information."""
    name: str = "MoniToni Vending Machine"
    version: str = "1.0.0"
    machine_id: str = "VM001"


class Config(BaseModel):
    """Main configuration model."""
    system: SystemConfig
    hardware: HardwareConfig
    vending: VendingConfig
    led: LEDConfig
    audio: AudioConfig
    purchase_server: PurchaseServerConfig
    telemetry: TelemetryConfig
    database: DatabaseConfig
    logging: LoggingConfig
    ui: UIConfig
    watchdog: WatchdogConfig


class ConfigManager:
    """
    Configuration manager for loading and accessing configuration.
    
    Loads configuration from:
    1. config/default.yaml (required)
    2. config/local.yaml (optional, overrides defaults)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to configuration directory. Defaults to ./config
        """
        if config_dir is None:
            # Assume we're running from project root
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
            
        self.default_config_path = self.config_dir / "default.yaml"
        self.local_config_path = self.config_dir / "local.yaml"
        
        self._config: Optional[Config] = None
        
    def load(self) -> Config:
        """
        Load configuration from YAML files.
        
        Returns:
            Loaded and validated configuration
            
        Raises:
            FileNotFoundError: If default.yaml is missing
            ValueError: If configuration is invalid
        """
        # Load default configuration
        if not self.default_config_path.exists():
            raise FileNotFoundError(
                f"Default configuration not found: {self.default_config_path}"
            )
            
        with open(self.default_config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
            
        # Override with local configuration if it exists
        if self.local_config_path.exists():
            with open(self.local_config_path, 'r') as f:
                local_config = yaml.safe_load(f)
                if local_config:
                    config_dict = self._deep_merge(config_dict, local_config)
                    
        # Validate and create config object
        self._config = Config(**config_dict)
        return self._config
        
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Dictionary with override values
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    @property
    def config(self) -> Config:
        """
        Get loaded configuration.
        
        Returns:
            Configuration object
            
        Raises:
            RuntimeError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config
        
    def save_local(self, updates: Dict[str, Any]) -> None:
        """
        Save updates to local configuration file.
        
        Args:
            updates: Dictionary of configuration updates
        """
        # Load existing local config if it exists
        local_config = {}
        if self.local_config_path.exists():
            with open(self.local_config_path, 'r') as f:
                local_config = yaml.safe_load(f) or {}
                
        # Merge updates
        local_config = self._deep_merge(local_config, updates)
        
        # Save to file
        self.local_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_config_path, 'w') as f:
            yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)
            
        # Reload configuration
        self.load()


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance.
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    return _config_manager


def get_config() -> Config:
    """
    Get loaded configuration.
    
    Returns:
        Configuration object
    """
    return get_config_manager().config
