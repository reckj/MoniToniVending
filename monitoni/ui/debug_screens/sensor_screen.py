"""
Sensor configuration and testing screen.

Provides controls for:
- GPIO pin configuration (pin number, pull mode, active state)
- Live door state monitoring (200ms update rate)
- Sensor info summary
- Reset to factory defaults
"""

import asyncio
from typing import Optional
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    NumpadField,
    update_config_value,
    reset_section_to_defaults,
    show_confirm_dialog,
    CORAL_ACCENT,
    NEAR_BLACK,
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class SensorSettingsScreen(BaseDebugSubScreen):
    """
    Sensor configuration and testing screen.

    Allows operators to:
    - Configure GPIO pin settings
    - Set pull resistor mode (up/down)
    - Set active state (low/high)
    - Monitor live door state in real-time
    - View sensor info summary
    """

    def __init__(
        self,
        hardware: HardwareManager,
        config_manager: ConfigManager,
        navigate_back: Optional[callable] = None,
        **kwargs
    ):
        """
        Initialize sensor settings screen.

        Args:
            hardware: Hardware manager instance
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional arguments for BaseDebugSubScreen
        """
        self.hardware = hardware
        self.config_manager = config_manager

        # Track door status update event for cleanup
        self._update_event = None

        super().__init__(navigate_back=navigate_back, **kwargs)
        self.title = "Sensors"

        self._build_content()

        # Start door status polling with strong reference
        self._update_event = Clock.schedule_interval(
            lambda dt: self._poll_door(dt),
            0.2  # 200ms update rate
        )

    def _build_content(self):
        """Build the sensor settings screen content."""
        # Card 1: GPIO Configuration
        gpio_card = SettingsCard(title="GPIO Configuration")

        # Sensor pin (BCM)
        pin_field = NumpadField(
            label="Sensor Pin (BCM)",
            config_path="hardware.gpio.door_sensor_pin",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=27
        )
        gpio_card.add_content(pin_field)

        # Pull mode selector
        pull_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        pull_label = MDLabel(
            text="Pull Mode",
            size_hint_x=0.4,
            font_style='Body1'
        )
        pull_row.add_widget(pull_label)

        # Get current pull mode
        current_pull = self.config_manager.config.hardware.gpio.door_sensor_pull

        # UP button
        self.pull_up_btn = MDRaisedButton(
            text="UP",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_pull == "up" else NEAR_BLACK,
            on_release=lambda x: self._set_pull_mode("up")
        )
        pull_row.add_widget(self.pull_up_btn)

        # DOWN button
        self.pull_down_btn = MDRaisedButton(
            text="DOWN",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_pull == "down" else NEAR_BLACK,
            on_release=lambda x: self._set_pull_mode("down")
        )
        pull_row.add_widget(self.pull_down_btn)

        gpio_card.add_content(pull_row)

        # Active state selector
        active_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        active_label = MDLabel(
            text="Active State",
            size_hint_x=0.4,
            font_style='Body1'
        )
        active_row.add_widget(active_label)

        # Get current active state
        current_active = self.config_manager.config.hardware.gpio.door_sensor_active

        # LOW button
        self.active_low_btn = MDRaisedButton(
            text="LOW",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_active == "low" else NEAR_BLACK,
            on_release=lambda x: self._set_active_state("low")
        )
        active_row.add_widget(self.active_low_btn)

        # HIGH button
        self.active_high_btn = MDRaisedButton(
            text="HIGH",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_active == "high" else NEAR_BLACK,
            on_release=lambda x: self._set_active_state("high")
        )
        active_row.add_widget(self.active_high_btn)

        gpio_card.add_content(active_row)

        # Enabled toggle
        enabled_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        enabled_label = MDLabel(
            text="Sensor Enabled",
            size_hint_x=0.7,
            font_style='Body1'
        )
        enabled_row.add_widget(enabled_label)

        # Get current enabled state
        current_enabled = self.config_manager.config.hardware.gpio.enabled

        self.enabled_btn = MDRaisedButton(
            text="ON" if current_enabled else "OFF",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_enabled else (0.5, 0.5, 0.5, 1),
            on_release=lambda x: self._toggle_enabled()
        )
        enabled_row.add_widget(self.enabled_btn)

        gpio_card.add_content(enabled_row)

        self.add_content(gpio_card)

        # Card 2: Live Door Status (PROMINENT)
        status_card = SettingsCard(title="Live Door Status")

        # Large status display
        self.door_status_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height="200dp",
            spacing="10dp",
            padding="20dp"
        )

        # Status label (very large)
        self.door_status_label = MDLabel(
            text="DOOR: CHECKING...",
            font_style='H3',
            halign='center',
            valign='center',
            size_hint_y=None,
            height="150dp",
            theme_text_color='Custom',
            text_color=(0.5, 0.5, 0.5, 1)
        )
        self.door_status_container.add_widget(self.door_status_label)

        # Add colored background
        from kivy.graphics import Color, Rectangle
        with self.door_status_container.canvas.before:
            self.door_status_bg_color = Color(0.2, 0.2, 0.2, 1)
            self.door_status_bg = Rectangle(
                pos=self.door_status_container.pos,
                size=self.door_status_container.size
            )

        # Bind to update background position/size
        self.door_status_container.bind(
            pos=lambda *args: setattr(self.door_status_bg, 'pos', self.door_status_container.pos),
            size=lambda *args: setattr(self.door_status_bg, 'size', self.door_status_container.size)
        )

        status_card.add_content(self.door_status_container)

        self.add_content(status_card)

        # Card 3: Sensor Info
        info_card = SettingsCard(title="Sensor Info")

        # Info container
        self.info_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing="5dp"
        )
        self.info_container.bind(minimum_height=self.info_container.setter('height'))

        # Build initial info display
        self._update_sensor_info()

        info_card.add_content(self.info_container)

        self.add_content(info_card)

        # Reset button
        reset_btn = MDRaisedButton(
            text="Factory Reset",
            size_hint_y=None,
            height="60dp",
            md_bg_color=(0.6, 0.3, 0.3, 1),
            on_release=lambda x: self._reset_to_defaults()
        )
        self.add_content(reset_btn)

    def _set_pull_mode(self, mode: str):
        """Set pull resistor mode."""
        def confirm_change():
            # Update config
            update_config_value(
                self.config_manager,
                "hardware.gpio.door_sensor_pull",
                mode
            )

            # Update button colors
            self.pull_up_btn.md_bg_color = CORAL_ACCENT if mode == "up" else NEAR_BLACK
            self.pull_down_btn.md_bg_color = CORAL_ACCENT if mode == "down" else NEAR_BLACK

            # Update sensor info
            self._update_sensor_info()

        # Show confirmation for risky change
        show_confirm_dialog(
            title="Confirmation Required",
            text=f"Set pull mode to {mode.upper()}?\n\nThis is a hardware-relevant setting.",
            on_confirm=confirm_change
        )

    def _set_active_state(self, state: str):
        """Set active state (low/high)."""
        def confirm_change():
            # Update config
            update_config_value(
                self.config_manager,
                "hardware.gpio.door_sensor_active",
                state
            )

            # Update button colors
            self.active_low_btn.md_bg_color = CORAL_ACCENT if state == "low" else NEAR_BLACK
            self.active_high_btn.md_bg_color = CORAL_ACCENT if state == "high" else NEAR_BLACK

            # Update sensor info
            self._update_sensor_info()

        # Show confirmation for risky change
        show_confirm_dialog(
            title="Confirmation Required",
            text=f"Set active state to {state.upper()}?\n\nThis is a hardware-relevant setting.",
            on_confirm=confirm_change
        )

    def _toggle_enabled(self):
        """Toggle sensor enabled state."""
        current_enabled = self.config_manager.config.hardware.gpio.enabled
        new_enabled = not current_enabled

        # Update config
        update_config_value(
            self.config_manager,
            "hardware.gpio.enabled",
            new_enabled
        )

        # Update button
        self.enabled_btn.text = "ON" if new_enabled else "OFF"
        self.enabled_btn.md_bg_color = CORAL_ACCENT if new_enabled else (0.5, 0.5, 0.5, 1)

        # Update sensor info
        self._update_sensor_info()

    def _update_sensor_info(self):
        """Update sensor info display."""
        # Clear existing info
        self.info_container.clear_widgets()

        # Get current config
        config = self.config_manager.config.hardware.gpio

        # Pin info
        pin_label = MDLabel(
            text=f"Pin: GPIO {config.door_sensor_pin} (BCM)",
            size_hint_y=None,
            height="30dp",
            font_style='Body2'
        )
        self.info_container.add_widget(pin_label)

        # Pull mode
        pull_label = MDLabel(
            text=f"Pull: {config.door_sensor_pull.upper()}",
            size_hint_y=None,
            height="30dp",
            font_style='Body2'
        )
        self.info_container.add_widget(pull_label)

        # Active state
        active_label = MDLabel(
            text=f"Active: {config.door_sensor_active.upper()}",
            size_hint_y=None,
            height="30dp",
            font_style='Body2'
        )
        self.info_container.add_widget(active_label)

        # Connection status
        if self.hardware.sensor and self.hardware.sensor.is_connected():
            status_text = "Status: Connected"
            status_color = (0, 1, 0, 1)
        else:
            status_text = "Status: Not connected"
            status_color = (1, 0, 0, 1)

        status_label = MDLabel(
            text=status_text,
            size_hint_y=None,
            height="30dp",
            font_style='Body2',
            theme_text_color='Custom',
            text_color=status_color
        )
        self.info_container.add_widget(status_label)

    def _poll_door(self, dt):
        """Poll door state (called by Clock at 200ms interval)."""
        asyncio.create_task(self._async_poll_door())

    async def _async_poll_door(self):
        """Async door polling implementation."""
        try:
            if not self.hardware.sensor or not self.hardware.sensor.is_connected():
                # Sensor not available or not connected
                Clock.schedule_once(lambda dt: self._update_door_display(None, disconnected=True))
                return

            # Get door state
            state = await self.hardware.sensor.get_door_state()

            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._update_door_display(state))

        except Exception as e:
            # Error reading sensor
            print(f"Error polling door sensor: {e}")
            Clock.schedule_once(lambda dt: self._update_door_display(None, error=True))

    def _update_door_display(self, state: Optional[bool], disconnected: bool = False, error: bool = False):
        """Update door status display."""
        if disconnected:
            # Sensor not connected
            self.door_status_label.text = "NOT CONNECTED"
            self.door_status_label.text_color = (0.5, 0.5, 0.5, 1)
            self.door_status_bg_color.rgba = (0.2, 0.2, 0.2, 1)
        elif error or state is None:
            # Error reading sensor
            self.door_status_label.text = "ERROR"
            self.door_status_label.text_color = (1, 0, 0, 1)
            self.door_status_bg_color.rgba = (0.3, 0.1, 0.1, 1)
        elif state:
            # Door open
            self.door_status_label.text = "DOOR: OPEN"
            self.door_status_label.text_color = CORAL_ACCENT
            self.door_status_bg_color.rgba = (0.3, 0.15, 0.15, 1)
        else:
            # Door closed
            self.door_status_label.text = "DOOR: CLOSED"
            self.door_status_label.text_color = (0, 1, 0, 1)
            self.door_status_bg_color.rgba = (0.1, 0.25, 0.1, 1)

    def _reset_to_defaults(self):
        """Reset GPIO section to factory defaults."""
        def confirm_reset():
            # Reset hardware.gpio section
            success = reset_section_to_defaults(self.config_manager, "hardware.gpio")

            if success:
                self._show_reset_success()
            else:
                self._show_reset_error()

        show_confirm_dialog(
            title="Restore Factory Settings",
            text="Reset all sensor settings to factory defaults?\n\nThis affects:\n- GPIO pin\n- Pull mode\n- Active state",
            on_confirm=confirm_reset
        )

    def _show_reset_success(self):
        """Show success message after reset."""
        dialog = MDDialog(
            title="Success",
            text="Sensor settings have been reset.\n\nPlease return to menu and reopen this screen to see new values.",
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def _show_reset_error(self):
        """Show error message if reset failed."""
        dialog = MDDialog(
            title="Error",
            text="Error resetting settings.",
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def on_pre_leave(self, *args):
        """Cleanup when leaving screen."""
        # Cancel Clock update event
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None
