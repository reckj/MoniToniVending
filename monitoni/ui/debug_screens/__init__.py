"""
Debug sub-screens package.

Provides modular sub-screens for the debug interface, each handling
a specific category of functionality (LED, Audio, Relay, etc.).
"""

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.menu_screen import DebugMenuScreen

__all__ = [
    "BaseDebugSubScreen",
    "DebugMenuScreen",
]
