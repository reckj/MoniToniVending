"""
Debug sub-screens package.

Provides modular sub-screens for the debug interface, each handling
a specific category of functionality (LED, Audio, Relay, etc.).
"""

from monitoni.ui.debug_screens.base import BaseDebugSubScreen

__all__ = [
    "BaseDebugSubScreen",
]
