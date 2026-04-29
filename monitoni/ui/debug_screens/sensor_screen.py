"""
Sensor configuration and testing screen.

Provides controls for:
- Active method indicator (GPIO or Modbus Digital Input)
- GPIO pin configuration (pin number, pull mode, active state)
- Modbus DI info card (when method is modbus_di)
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
    - View active sensor method (GPIO or Modbus DI) — read-only indicator
    - Configure GPIO pin settings (fallback or active config)
    - View Modbus DI info (when method is modbus_di)
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

    def _get_active_method(self) -> str:
        """Return active sensor method string ('gpio' or 'modbus_di')."""
        door_sensor_cfg = self.config_manager.config.hardware.door_sensor
        if door_sensor_cfg is not None:
            return door_sensor_cfg.method
        return "gpio"

    def _build_content(self):
        """Build the sensor settings screen content."""
        active_method = self._get_active_method()

        # Card 0: Active Method Indicator
        self._build_method_indicator_card(active_method)

        # Card 1: GPIO Configuration (always visible — fallback config)
        self._build_gpio_card(active_method)

        # Card 2: Modbus DI Info (only when method is modbus_di)
        if active_method == "modbus_di":
            self._build_modbus_di_card()

        # Card 3: Live Door Status (PROMINENT)
        self._build_door_status_card()

        # Card 4: Sensor Info
        self._build_sensor_info_card()

        # Reset button
        reset_btn = MDRaisedButton(
            text="Factory Reset",
            size_hint_y=None,
            height="60dp",
            md_bg_color=(0.6, 0.3, 0.3, 1),
            on_release=lambda x: self._reset_to_defaults()
        )
        self.add_content(reset_btn)

    def _build_method_indicator_card(self, active_method: str):
        """Build read-only active sensor method indicator card."""
        card = SettingsCard(title="Sensor Method")

        method_display = (
            "Modbus Digital Input"
            if active_method == "modbus_di"
            else "GPIO"
        )

        method_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp",
        )

        method_label = MDLabel(
            text="Active Method:",
            size_hint_x=0.5,
            font_style='Body1',
        )
        method_row.add_widget(method_label)

        method_value = MDLabel(
            text=method_display,
            size_hint_x=0.5,
            font_style='Body1',
            bold=True,
            theme_text_color='Custom',
            text_color=CORAL_ACCENT,
            halign='right',
        )
        method_row.add_widget(method_value)
        card.add_content(method_row)

        note_label = MDLabel(
            text="(Change in config file)",
            font_style='Caption',
            size_hint_y=None,
            height="24dp",
            theme_text_color='Secondary',
            halign='right',
        )
        card.add_content(note_label)

        self.add_content(card)

    def _build_gpio_card(self, active_method: str):
        """Build GPIO configuration card (always visible)."""
        gpio_title = "GPIO Configuration"
        gpio_card = SettingsCard(title=gpio_title)

        # When modbus_di is active, show a note that this is fallback config
        if active_method == "modbus_di":
            fallback_label = MDLabel(
                text="Fallback configuration (currently using Modbus DI)",
                font_style='Caption',
                size_hint_y=None,
                height="24dp",
                theme_text_color='Secondary',
                halign='left',
            )
            gpio_card.add_content(fallback_label)

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

    def _build_modbus_di_card(self):
        """Build Modbus DI info card (shown only when method is modbus_di)."""
        card = SettingsCard(title="Modbus DI Info")

        door_sensor_cfg = self.config_manager.config.hardware.door_sensor
        relay_core_cfg = self.config_manager.config.hardware.relay_core

        # DI Index (read-only)
        di_index = door_sensor_cfg.di_index if door_sensor_cfg else 0
        di_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="40dp",
            spacing="10dp",
        )
        di_row.add_widget(MDLabel(text="DI Index:", size_hint_x=0.5, font_style='Body2'))
        di_row.add_widget(MDLabel(
            text=str(di_index),
            size_hint_x=0.5,
            font_style='Body2',
            halign='right',
        ))
        card.add_content(di_row)

        # Poll Interval (read-only)
        poll_ms = door_sensor_cfg.poll_interval_ms if door_sensor_cfg else 150
        poll_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="40dp",
            spacing="10dp",
        )
        poll_row.add_widget(MDLabel(text="Poll Interval:", size_hint_x=0.5, font_style='Body2'))
        poll_row.add_widget(MDLabel(
            text=f"{poll_ms}ms",
            size_hint_x=0.5,
            font_style='Body2',
            halign='right',
        ))
        card.add_content(poll_row)

        # Source Module (read-only)
        source_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="40dp",
            spacing="10dp",
        )
        source_row.add_widget(MDLabel(text="Source Module:", size_hint_x=0.5, font_style='Body2'))

        # Connection status dot
        core_connected = (
            self.hardware.relay_core is not None
            and self.hardware.relay_core.is_connected()
        )
        dot_color = (0, 0.85, 0.35, 1) if core_connected else (1, 0.2, 0.2, 1)
        dot_label = MDLabel(
            text="o",
            font_style="H6",
            size_hint_x=0.1,
            halign="center",
            theme_text_color="Custom",
            text_color=dot_color,
        )

        source_label = MDLabel(
            text="Core Module (8-CH)",
            size_hint_x=0.4,
            font_style='Body2',
            halign='right',
        )
        source_row.add_widget(dot_label)
        source_row.add_widget(source_label)
        card.add_content(source_row)

        # Host:Port from relay_core config
        if relay_core_cfg:
            host_port_row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height="40dp",
                spacing="10dp",
            )
            host_port_row.add_widget(MDLabel(text="Host:Port:", size_hint_x=0.5, font_style='Body2'))
            host_port_row.add_widget(MDLabel(
                text=f"{relay_core_cfg.host}:{relay_core_cfg.port}",
                size_hint_x=0.5,
                font_style='Body2',
                halign='right',
            ))
            card.add_content(host_port_row)

        self.add_content(card)

    def _build_door_status_card(self):
        """Build live door status card with large status display."""
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

    def _build_sensor_info_card(self):
        """Build sensor info summary card."""
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
        gpio_config = self.config_manager.config.hardware.gpio
        active_method = self._get_active_method()

        # Method
        method_display = "Modbus Digital Input" if active_method == "modbus_di" else "GPIO"
        method_label = MDLabel(
            text=f"Method: {method_display}",
            size_hint_y=None,
            height="30dp",
            font_style='Body2',
            theme_text_color='Custom',
            text_color=CORAL_ACCENT,
        )
        self.info_container.add_widget(method_label)

        if active_method == "modbus_di":
            door_sensor_cfg = self.config_manager.config.hardware.door_sensor
            relay_core_cfg = self.config_manager.config.hardware.relay_core

            di_index = door_sensor_cfg.di_index if door_sensor_cfg else 0
            poll_ms = door_sensor_cfg.poll_interval_ms if door_sensor_cfg else 150

            di_label = MDLabel(
                text=f"DI Index: {di_index}",
                size_hint_y=None,
                height="30dp",
                font_style='Body2',
            )
            self.info_container.add_widget(di_label)

            poll_label = MDLabel(
                text=f"Poll: {poll_ms}ms",
                size_hint_y=None,
                height="30dp",
                font_style='Body2',
            )
            self.info_container.add_widget(poll_label)

            if relay_core_cfg:
                source_label = MDLabel(
                    text=f"Source: Core Module {relay_core_cfg.host}:{relay_core_cfg.port}",
                    size_hint_y=None,
                    height="30dp",
                    font_style='Body2',
                )
                self.info_container.add_widget(source_label)
        else:
            # GPIO info
            pin_label = MDLabel(
                text=f"Pin: GPIO {gpio_config.door_sensor_pin} (BCM)",
                size_hint_y=None,
                height="30dp",
                font_style='Body2'
            )
            self.info_container.add_widget(pin_label)

            pull_label = MDLabel(
                text=f"Pull: {gpio_config.door_sensor_pull.upper()}",
                size_hint_y=None,
                height="30dp",
                font_style='Body2'
            )
            self.info_container.add_widget(pull_label)

            active_label = MDLabel(
                text=f"Active: {gpio_config.door_sensor_active.upper()}",
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
        """Reset sensor settings to factory defaults."""
        active_method = self._get_active_method()

        reset_sections = ["hardware.gpio"]
        reset_desc = "- GPIO pin, pull mode, active state"
        if active_method == "modbus_di":
            reset_sections.append("hardware.door_sensor")
            reset_desc += "\n- Modbus DI sensor settings"

        def confirm_reset():
            success = True
            for section in reset_sections:
                ok = reset_section_to_defaults(self.config_manager, section)
                if not ok:
                    success = False

            if success:
                self._show_reset_success()
            else:
                self._show_reset_error()

        show_confirm_dialog(
            title="Restore Factory Settings",
            text=f"Reset all sensor settings to factory defaults?\n\nThis affects:\n{reset_desc}",
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
        super().on_pre_leave(*args)
        # Cancel Clock update event
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None
