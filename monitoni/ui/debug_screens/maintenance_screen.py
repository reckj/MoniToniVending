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
        self.hardware = hardware
        self.config_manager = config_manager

        kwargs.setdefault('name', 'maintenance')
        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "Maintenance & Status"
        self._build_maintenance_ui()

    def _build_maintenance_ui(self):
        """Build the maintenance screen UI."""
        # Operating Mode Card
        self.mode_card = SettingsCard(title="Operating Mode")

        # Maintenance mode toggle row
        toggle_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="56dp",
            spacing="10dp",
            padding=["10dp", "4dp", "10dp", "4dp"]
        )

        toggle_label = MDLabel(
            text="Maintenance Mode:",
            size_hint_x=0.7,
            font_style='Body1'
        )
        toggle_row.add_widget(toggle_label)

        # MDSwitch - MUST use Clock.schedule_once for KivyMD 1.2.0 quirk
        self.maintenance_toggle = MDSwitch(
            size_hint=(None, None),
            size=("48dp", "28dp"),
            pos_hint={"center_y": 0.5},
        )
        self.maintenance_toggle.bind(on_active=self.on_maintenance_toggle)
        toggle_row.add_widget(self.maintenance_toggle)

        self.mode_card.add_content(toggle_row)

        # Info text
        self.info_label = MDLabel(
            text="Sales are blocked while maintenance mode is active.",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height="30dp",
            padding=["10dp", 0]
        )
        self.mode_card.add_content(self.info_label)

        self.add_content(self.mode_card)

        # Machine Status Card (LiveStatusCard with async callback)
        status_card = LiveStatusCard(
            title="Machine Status",
            get_status_callback=self.get_machine_status,
            update_interval=2.0
        )
        self.add_content(status_card)

        # Set initial toggle state via Clock.schedule_once (KivyMD quirk)
        current_state = self._get_maintenance_mode()
        Clock.schedule_once(
            lambda dt: self._set_toggle_state(current_state),
            0
        )

    def _get_maintenance_mode(self) -> bool:
        """Get current maintenance mode state from config."""
        try:
            return self.config_manager.config.system.maintenance_mode
        except Exception:
            return False

    def _set_toggle_state(self, active: bool):
        """Set toggle state and update visual feedback."""
        self.maintenance_toggle.active = active
        self._update_mode_visual(active)

    def _update_mode_visual(self, active: bool):
        """Update card visual to reflect maintenance state."""
        if active:
            self.info_label.text = "MAINTENANCE MODE ACTIVE — Sales blocked"
            self.info_label.theme_text_color = 'Custom'
            self.info_label.text_color = ERROR_RED
        else:
            self.info_label.text = "Sales are blocked while maintenance mode is active."
            self.info_label.theme_text_color = 'Secondary'

    def on_maintenance_toggle(self, instance, value):
        """Handle maintenance mode toggle."""
        success, needs_confirm = update_config_value(
            self.config_manager,
            "system.maintenance_mode",
            value
        )

        if not success:
            # Revert toggle on failure
            Clock.schedule_once(
                lambda dt: self._set_toggle_state(not value),
                0
            )
        else:
            self._update_mode_visual(value)

    async def get_machine_status(self) -> List[Tuple[str, str, Tuple]]:
        """Get real-time machine status."""
        status_items = []

        green = (0, 0.8, 0, 1)
        yellow = (1, 1, 0, 1)
        grey = (0.5, 0.5, 0.5, 1)

        # 1. Operating Mode
        maintenance_active = self._get_maintenance_mode()
        if maintenance_active:
            status_items.append(("Mode:", "MAINTENANCE", ERROR_RED))
        else:
            status_items.append(("Mode:", "Operating", green))

        # 2. Relay Status
        try:
            if self.hardware.relay and self.hardware.relay.is_connected():
                status_items.append(("Relay:", "OK", green))
            else:
                status_items.append(("Relay:", "ERROR", ERROR_RED))
        except Exception:
            status_items.append(("Relay:", "ERROR", ERROR_RED))

        # 3. LED Status
        try:
            if self.hardware.led and hasattr(self.hardware.led, 'is_connected'):
                if await self.hardware.led.is_connected():
                    status_items.append(("LEDs:", "OK", green))
                else:
                    status_items.append(("LEDs:", "OFFLINE", yellow))
            else:
                status_items.append(("LEDs:", "OK", green))
        except Exception:
            status_items.append(("LEDs:", "OFFLINE", yellow))

        # 4. Door Sensor Status
        try:
            if self.hardware.sensor:
                door_open = self.hardware.sensor.is_door_open()
                if door_open:
                    status_items.append(("Door:", "OPEN", yellow))
                else:
                    status_items.append(("Door:", "Closed", grey))
            else:
                status_items.append(("Door:", "N/A", grey))
        except Exception:
            status_items.append(("Door:", "N/A", grey))

        # 5. Audio Status
        try:
            audio_enabled = self.config_manager.config.hardware.audio.enabled
            if audio_enabled:
                status_items.append(("Audio:", "Active", green))
            else:
                status_items.append(("Audio:", "Disabled", grey))
        except Exception:
            status_items.append(("Audio:", "N/A", grey))

        return status_items
