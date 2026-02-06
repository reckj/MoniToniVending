"""
Relay settings and testing screen.

Provides Modbus configuration, relay testing, door lock mapping, and live status.
"""

import asyncio
from typing import Optional, List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard, HoldButton, NumpadField, LiveStatusCard,
    show_confirm_dialog, reset_section_to_defaults, CORAL_ACCENT
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class RelaySettingsScreen(BaseDebugSubScreen):
    """
    Relay configuration and testing screen.

    Provides:
    - Modbus connection settings
    - Individual relay testing (hold-to-activate)
    - Cascade test for all relays
    - Door lock relay mapping
    - Live relay status
    - Reset to defaults
    """

    def __init__(
        self,
        hardware: HardwareManager,
        config_manager: ConfigManager,
        navigate_back=None,
        **kwargs
    ):
        """
        Initialize relay settings screen.

        Args:
            hardware: HardwareManager instance
            config_manager: ConfigManager instance
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager
        self.title = "Relay-Steuerung"

        # Cascade test state
        self._cascade_task = None
        self._cascade_running = False

        super().__init__(navigate_back=navigate_back, **kwargs)
        self._build_content()

    def _build_content(self):
        """Build the relay settings screen content."""
        # Card 1: Modbus Connection
        self._build_modbus_card()

        # Card 2: Relay Testing
        self._build_relay_test_card()

        # Card 3: Door Lock Mapping
        self._build_door_lock_card()

        # Card 4: Live Status
        self._build_status_card()

        # Reset button
        self._build_reset_button()

    def _build_modbus_card(self):
        """Build Modbus connection settings card."""
        card = SettingsCard("Modbus-Verbindung")

        # Port (string field - tappable label showing current value)
        port_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )
        port_label = MDLabel(
            text="Port",
            size_hint_x=0.6,
            font_style='Body1'
        )
        port_row.add_widget(port_label)

        current_port = self.config_manager.config.hardware.modbus.port
        self.port_button = MDRaisedButton(
            text=current_port,
            size_hint_x=0.4,
            md_bg_color=(0.12, 0.12, 0.12, 1),
            on_release=lambda x: self._edit_port()
        )
        port_row.add_widget(self.port_button)
        card.add_content(port_row)

        # Baudrate
        baudrate_field = NumpadField(
            label="Baudrate",
            config_path="hardware.modbus.baudrate",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1200,
            max_value=115200
        )
        card.add_content(baudrate_field)

        # Slave Address
        slave_field = NumpadField(
            label="Slave-Adresse",
            config_path="hardware.modbus.slave_address",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=247
        )
        card.add_content(slave_field)

        # Timeout
        timeout_field = NumpadField(
            label="Timeout (s)",
            config_path="hardware.modbus.timeout",
            config_manager=self.config_manager,
            allow_decimal=True,
            min_value=0.1,
            max_value=10.0
        )
        card.add_content(timeout_field)

        self.add_content(card)

    def _edit_port(self):
        """Show dialog to edit Modbus port."""
        # Simple confirmation dialog showing current port
        # For production, could add text input dialog
        current_port = self.config_manager.config.hardware.modbus.port
        show_confirm_dialog(
            title="Modbus Port",
            text=f"Aktueller Port: {current_port}\n\nPort-Änderung erfordert Neustart.",
            on_confirm=None
        )

    def _build_relay_test_card(self):
        """Build relay testing card with cascade and individual buttons."""
        card = SettingsCard("Relay-Test")

        # Cascade test button (full width, prominent)
        cascade_btn = HoldButton(
            text="Alle testen (Kaskade)",
            on_hold=self._start_cascade_test,
            on_release_hold=self._stop_cascade_test
        )
        cascade_btn.height = "70dp"
        card.add_content(cascade_btn)

        # Grid of 32 relay buttons (4 columns x 8 rows)
        relay_grid = GridLayout(
            cols=4,
            spacing="5dp",
            size_hint_y=None
        )
        relay_grid.bind(minimum_height=relay_grid.setter('height'))

        for channel in range(1, 33):
            btn = HoldButton(
                text=f"R{channel}",
                on_hold=lambda ch=channel: self._activate_relay(ch),
                on_release_hold=lambda ch=channel: self._deactivate_relay(ch)
            )
            btn.height = "50dp"
            relay_grid.add_widget(btn)

        card.add_content(relay_grid)
        self.add_content(card)

    def _build_door_lock_card(self):
        """Build door lock mapping card."""
        card = SettingsCard("Tür-Schloss Zuordnung")

        # Get current relay channels list
        levels = self.config_manager.config.vending.levels
        relay_channels = self.config_manager.config.vending.door_lock.relay_channels

        # Create numpad field for each level
        for level in range(1, levels + 1):
            # Get current channel for this level (with bounds checking)
            current_channel = relay_channels[level - 1] if level - 1 < len(relay_channels) else 0

            # Create a custom row with label and button
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height="50dp",
                spacing="10dp"
            )

            label = MDLabel(
                text=f"Fach {level}:",
                size_hint_x=0.6,
                font_style='Body1'
            )
            row.add_widget(label)

            # Button to open numpad for this level
            btn = MDRaisedButton(
                text=str(current_channel),
                size_hint_x=0.4,
                md_bg_color=(0.12, 0.12, 0.12, 1),
                on_release=lambda x, lv=level, btn_ref=None: self._edit_door_lock_channel(lv, btn_ref or x)
            )
            # Store button reference for updating after edit
            btn.level = level
            row.add_widget(btn)

            card.add_content(row)

        # Unlock duration field
        unlock_duration_field = NumpadField(
            label="Entsperr-Dauer (s)",
            config_path="vending.door_lock.unlock_duration_s",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=5,
            max_value=120
        )
        card.add_content(unlock_duration_field)

        self.add_content(card)

    def _edit_door_lock_channel(self, level: int, button: MDRaisedButton):
        """Edit relay channel for a door lock level."""
        from monitoni.ui.debug_screens.widgets import NumpadDialog

        # Get current value
        relay_channels = self.config_manager.config.vending.door_lock.relay_channels
        current_value = relay_channels[level - 1] if level - 1 < len(relay_channels) else 0

        def on_submit(new_value: float):
            # Update the relay_channels list
            new_channels = list(relay_channels)
            # Ensure list is long enough
            while len(new_channels) < level:
                new_channels.append(0)
            new_channels[level - 1] = int(new_value)

            # Save to config
            update_dict = {
                "vending": {
                    "door_lock": {
                        "relay_channels": new_channels
                    }
                }
            }

            # Show confirmation (risky change)
            show_confirm_dialog(
                title="Bestätigung erforderlich",
                text=f"Möchten Sie Fach {level} wirklich auf Relay {int(new_value)} setzen?\n\nDies ist eine hardwarerelevante Einstellung.",
                on_confirm=lambda: self._apply_door_lock_change(update_dict, button, int(new_value))
            )

        # Open numpad
        dialog = NumpadDialog(
            title=f"Fach {level} Relay-Kanal",
            initial_value=float(current_value),
            min_value=1,
            max_value=32,
            allow_decimal=False,
            on_submit=on_submit
        )
        dialog.open()

    def _apply_door_lock_change(self, update_dict: dict, button: MDRaisedButton, new_value: int):
        """Apply door lock channel change."""
        try:
            self.config_manager.save_local(update_dict)
            button.text = str(new_value)
        except Exception as e:
            print(f"Failed to update door lock channel: {e}")

    def _build_status_card(self):
        """Build live relay status card."""
        def get_relay_status() -> List[Tuple[str, str, Tuple[float, float, float, float]]]:
            """Get status of important relays."""
            if not self.hardware.relay:
                return [("Relay", "Nicht verbunden", (1, 0, 0, 1))]

            status_items = []

            # Motor relay
            motor_ch = self.config_manager.config.vending.motor.relay_channel
            try:
                motor_state = asyncio.run(self.hardware.relay.get_relay(motor_ch))
                state_text = "AN" if motor_state else "AUS"
                color = (0, 1, 0, 1) if motor_state else (0.5, 0.5, 0.5, 1)
                status_items.append((f"Motor (R{motor_ch})", state_text, color))
            except Exception:
                status_items.append((f"Motor (R{motor_ch})", "ERROR", (1, 0, 0, 1)))

            # Spindle lock relay
            spindle_ch = self.config_manager.config.vending.motor.spindle_lock_relay
            try:
                spindle_state = asyncio.run(self.hardware.relay.get_relay(spindle_ch))
                state_text = "AN" if spindle_state else "AUS"
                color = (0, 1, 0, 1) if spindle_state else (0.5, 0.5, 0.5, 1)
                status_items.append((f"Spindel (R{spindle_ch})", state_text, color))
            except Exception:
                status_items.append((f"Spindel (R{spindle_ch})", "ERROR", (1, 0, 0, 1)))

            # First 3 door lock relays (sample)
            door_channels = self.config_manager.config.vending.door_lock.relay_channels[:3]
            for i, ch in enumerate(door_channels):
                try:
                    door_state = asyncio.run(self.hardware.relay.get_relay(ch))
                    state_text = "AN" if door_state else "AUS"
                    color = (0, 1, 0, 1) if door_state else (0.5, 0.5, 0.5, 1)
                    status_items.append((f"Tür {i+1} (R{ch})", state_text, color))
                except Exception:
                    status_items.append((f"Tür {i+1} (R{ch})", "ERROR", (1, 0, 0, 1)))

            return status_items

        status_card = LiveStatusCard(
            title="Relay-Status",
            get_status_callback=get_relay_status,
            update_interval=1.0
        )
        self.add_content(status_card)

    def _build_reset_button(self):
        """Build reset to defaults button."""
        reset_btn = MDRaisedButton(
            text="Werkseinstellungen",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._reset_to_defaults()
        )
        self.add_content(reset_btn)

    def _reset_to_defaults(self):
        """Reset relay settings to defaults."""
        def do_reset():
            # Reset Modbus section
            reset_section_to_defaults(self.config_manager, "hardware.modbus")
            # Reset door lock section
            reset_section_to_defaults(self.config_manager, "vending.door_lock")

        show_confirm_dialog(
            title="Werkseinstellungen",
            text="Relay-Einstellungen zurücksetzen?\n\nDies setzt Modbus und Tür-Schloss Konfiguration zurück.",
            on_confirm=do_reset
        )

    def _activate_relay(self, channel: int):
        """Activate a relay channel."""
        if self.hardware.relay:
            asyncio.create_task(self.hardware.relay.set_relay(channel, True))

    def _deactivate_relay(self, channel: int):
        """Deactivate a relay channel."""
        if self.hardware.relay:
            asyncio.create_task(self.hardware.relay.set_relay(channel, False))

    def _start_cascade_test(self):
        """Start cascade test (sequential relay activation)."""
        if not self._cascade_running:
            self._cascade_running = True
            self._cascade_task = asyncio.create_task(self._run_cascade_test())

    def _stop_cascade_test(self):
        """Stop cascade test and deactivate all relays."""
        self._cascade_running = False
        if self._cascade_task:
            self._cascade_task.cancel()
            self._cascade_task = None

        # Deactivate all relays
        if self.hardware.relay:
            asyncio.create_task(self.hardware.relay.set_all_relays(False))

    async def _run_cascade_test(self):
        """Run cascade test loop."""
        try:
            while self._cascade_running:
                for channel in range(1, 33):
                    if not self._cascade_running:
                        break

                    # Activate relay
                    await self.hardware.relay.set_relay(channel, True)
                    await asyncio.sleep(0.1)  # 100ms per relay
                    await self.hardware.relay.set_relay(channel, False)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Cascade test error: {e}")

    def on_pre_leave(self, *args):
        """Safety: stop cascade and deactivate relays when leaving screen."""
        super().on_pre_leave(*args)
        self._stop_cascade_test()
