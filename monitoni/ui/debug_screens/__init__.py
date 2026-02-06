"""
Debug sub-screens package.

Provides modular sub-screens for the debug interface, each handling
a specific category of functionality (LED, Audio, Relay, etc.).
"""

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.menu_screen import DebugMenuScreen
from monitoni.ui.debug_screens.relay_screen import RelaySettingsScreen
from monitoni.ui.debug_screens.motor_screen import MotorSettingsScreen
from monitoni.ui.debug_screens.led_screen import LEDSettingsScreen
from monitoni.ui.debug_screens.sensor_screen import SensorSettingsScreen
from monitoni.ui.debug_screens.audio_screen import AudioSettingsScreen
from monitoni.ui.debug_screens.network_screen import NetworkSettingsScreen
from monitoni.ui.debug_screens.stats_screen import StatsSettingsScreen

__all__ = [
    "BaseDebugSubScreen",
    "DebugMenuScreen",
    "RelaySettingsScreen",
    "MotorSettingsScreen",
    "LEDSettingsScreen",
    "SensorSettingsScreen",
    "AudioSettingsScreen",
    "NetworkSettingsScreen",
    "StatsSettingsScreen",
]
