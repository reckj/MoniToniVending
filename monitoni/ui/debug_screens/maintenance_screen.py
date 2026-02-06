"""
Maintenance mode and machine status screen.

Provides:
- Maintenance mode toggle (blocks customer purchases)
- Real-time machine status display (hardware health, mode)
"""

import asyncio
from typing import List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDSwitch

from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    LiveStatusCard,
    update_config_value,
    CORAL_ACCENT,
    NEAR_BLACK,
    ERROR_RED
)


class MaintenanceScreen(BaseDebugSubScreen):
    """
    Maintenance mode control and machine status display.

    Allows operators to:
    - Toggle maintenance mode on/off (blocks customer purchases)
    - View real-time machine health status
    """

    def __init__(self, hardware: HardwareManager, config_manager: ConfigManager,
                 navigate_back=None, **kwargs):
        """
        Initialize maintenance screen.

        Args:
            hardware: Hardware manager for status checks
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager

        # Set screen name and title before calling super().__init__
        kwargs.setdefault('name', 'maintenance')

        super().__init__(navigate_back=navigate_back, **kwargs)

        # Set title after initialization
        self.title = "Wartung & Status"

        # Build UI
        self._build_maintenance_ui()

    def _build_maintenance_ui(self):
        """Build the maintenance screen UI."""
        # Operating Mode Card
        mode_card = SettingsCard(title="Betriebsmodus")

        # Maintenance mode toggle row
        toggle_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        toggle_label = MDLabel(
            text="Wartungsmodus:",
            size_hint_x=0.7,
            font_style='Body1'
        )
        toggle_row.add_widget(toggle_label)

        # MDSwitch - MUST use Clock.schedule_once for KivyMD 1.2.0 quirk
        self.maintenance_toggle = MDSwitch(
            size_hint_x=0.3
        )
        self.maintenance_toggle.bind(on_active=self.on_maintenance_toggle)
        toggle_row.add_widget(self.maintenance_toggle)

        mode_card.add_content(toggle_row)

        # Info text
        info_label = MDLabel(
            text="Im Wartungsmodus ist der Verkauf gesperrt.",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height="30dp"
        )
        mode_card.add_content(info_label)

        self.add_content(mode_card)

        # Machine Status Card (LiveStatusCard with async callback)
        status_card = LiveStatusCard(
            title="Maschinenstatus",
            get_status_callback=self.get_machine_status,
            update_interval=2.0
        )
        self.add_content(status_card)

        # Set initial toggle state via Clock.schedule_once (KivyMD quirk)
        current_state = self._get_maintenance_mode()
        Clock.schedule_once(
            lambda dt: setattr(self.maintenance_toggle, 'active', current_state),
            0
        )

    def _get_maintenance_mode(self) -> bool:
        """Get current maintenance mode state from config."""
        try:
            if hasattr(self.config_manager.config, 'system'):
                if hasattr(self.config_manager.config.system, 'maintenance_mode'):
                    return self.config_manager.config.system.maintenance_mode
        except Exception as e:
            print(f"Failed to get maintenance mode: {e}")
        return False

    def on_maintenance_toggle(self, instance, value):
        """Handle maintenance mode toggle."""
        # Update config
        success, needs_confirm = update_config_value(
            self.config_manager,
            "system.maintenance_mode",
            value
        )

        if not success:
            # Revert toggle on failure
            Clock.schedule_once(
                lambda dt: setattr(self.maintenance_toggle, 'active', not value),
                0
            )
            print("Failed to update maintenance mode")

    async def get_machine_status(self) -> List[Tuple[str, str, Tuple]]:
        """
        Get real-time machine status.

        Returns:
            List of (label, value, color) tuples for status display
        """
        status_items = []

        # Color definitions
        green = (0, 0.8, 0, 1)
        yellow = (1, 1, 0, 1)
        grey = (0.5, 0.5, 0.5, 1)

        # 1. Operating Mode
        maintenance_active = self._get_maintenance_mode()
        if maintenance_active:
            status_items.append(("Modus:", "WARTUNG", ERROR_RED))
        else:
            status_items.append(("Modus:", "Betrieb", green))

        # 2. Relay Status
        try:
            if self.hardware.relay and self.hardware.relay.is_connected():
                status_items.append(("Relais:", "OK", green))
            else:
                status_items.append(("Relais:", "FEHLER", ERROR_RED))
        except Exception as e:
            status_items.append(("Relais:", "FEHLER", ERROR_RED))

        # 3. LED Status
        try:
            if self.hardware.led and hasattr(self.hardware.led, 'is_connected'):
                if await self.hardware.led.is_connected():
                    status_items.append(("LEDs:", "OK", green))
                else:
                    status_items.append(("LEDs:", "OFFLINE", yellow))
            else:
                # LED controller doesn't support connection check
                status_items.append(("LEDs:", "OK", green))
        except Exception as e:
            status_items.append(("LEDs:", "OFFLINE", yellow))

        # 4. Door Sensor Status
        try:
            if self.hardware.sensor:
                door_open = self.hardware.sensor.is_door_open()
                if door_open:
                    status_items.append(("Tür:", "OFFEN", yellow))
                else:
                    status_items.append(("Tür:", "Geschlossen", grey))
            else:
                status_items.append(("Tür:", "N/A", grey))
        except Exception as e:
            status_items.append(("Tür:", "N/A", grey))

        # 5. Audio Status
        try:
            if hasattr(self.config_manager.config, 'hardware'):
                if hasattr(self.config_manager.config.hardware, 'audio'):
                    audio_enabled = self.config_manager.config.hardware.audio.enabled
                    if audio_enabled:
                        status_items.append(("Audio:", "Aktiv", green))
                    else:
                        status_items.append(("Audio:", "Deaktiviert", grey))
                else:
                    status_items.append(("Audio:", "N/A", grey))
            else:
                status_items.append(("Audio:", "N/A", grey))
        except Exception as e:
            status_items.append(("Audio:", "N/A", grey))

        return status_items
