"""
Relay settings and testing screen — dual-module layout.

Provides two independent sections:
- Core Module (8-CH): motor, spindle, machine relays
- Levels Module (30-CH): door lock relays

Each section has: connection status, settings, relay test buttons.
"""

import asyncio
from typing import List, Optional, Tuple

from kivy.graphics import Color, Ellipse
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    CORAL_ACCENT,
    INPUT_BUTTON,
    NEAR_BLACK,
    HoldButton,
    LiveStatusCard,
    NumpadField,
    SettingsCard,
    reset_section_to_defaults,
    show_confirm_dialog,
)


class RelaySettingsScreen(BaseDebugSubScreen):
    """
    Relay configuration and testing screen — dual-module layout.

    Section 1 — Core Module (8-CH): motor, spindle, machine relays
    Section 2 — Levels Module (30-CH): door lock relays

    Provides per-module: connection status, transport settings,
    relay test hold-buttons, and combined live status card.
    """

    def __init__(
        self,
        hardware: HardwareManager,
        config_manager: ConfigManager,
        navigate_back=None,
        **kwargs,
    ):
        self.hardware = hardware
        self.config_manager = config_manager
        self.title = "Relay Control"

        # Track connection-dot labels for live updates
        self._core_dot_widget: Optional[MDLabel] = None
        self._levels_dot_widget: Optional[MDLabel] = None

        super().__init__(navigate_back=navigate_back, **kwargs)
        self._build_content()

    # ------------------------------------------------------------------
    # Top-level build
    # ------------------------------------------------------------------

    def _build_content(self):
        """Build all cards top-to-bottom."""
        # --- Core Module ---
        self._build_module_status_header("core")
        self._build_module_settings_card("core")
        self._build_module_relay_test_card("core")

        # --- Levels Module ---
        self._build_module_status_header("levels")
        self._build_module_settings_card("levels")
        self._build_module_relay_test_card("levels")

        # --- Door Lock Mapping (Levels Module) ---
        self._build_door_lock_card()

        # --- Combined Live Status ---
        self._build_status_card()

        # --- Factory Reset ---
        self._build_reset_button()

    # ------------------------------------------------------------------
    # Connection status header
    # ------------------------------------------------------------------

    def _build_module_status_header(self, module: str):
        """
        Build a connection status header row for a module.

        Shows: '<Module Name>' label + colored dot + 'IP:port' text.
        """
        is_core = module == "core"
        cfg = (
            self.config_manager.config.hardware.relay_core
            if is_core
            else self.config_manager.config.hardware.relay_levels
        )

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="44dp",
            spacing="8dp",
            padding=("0dp", "8dp", "0dp", "4dp"),
        )

        # Module name label
        name_label = MDLabel(
            text="Core Module (8-CH)" if is_core else "Levels Module (30-CH)",
            bold=True,
            font_style="Subtitle1",
            size_hint_x=0.5,
            halign="left",
        )
        row.add_widget(name_label)

        # Connection dot (small colored circle as text label)
        dot_label = MDLabel(
            text="o",
            font_style="H6",
            size_hint_x=0.1,
            halign="center",
            theme_text_color="Custom",
            text_color=(0.5, 0.5, 0.5, 1),  # grey until first poll
        )
        if is_core:
            self._core_dot_widget = dot_label
        else:
            self._levels_dot_widget = dot_label
        row.add_widget(dot_label)

        # IP:port text
        if cfg:
            ip_text = f"{cfg.host}:{cfg.port}"
        else:
            ip_text = "not configured"
        ip_label = MDLabel(
            text=ip_text,
            font_style="Body2",
            size_hint_x=0.4,
            halign="right",
            theme_text_color="Secondary",
        )
        row.add_widget(ip_label)

        self.add_content(row)

        # Schedule periodic dot refresh (1 s)
        from kivy.clock import Clock

        if is_core:
            Clock.schedule_interval(
                lambda dt: self._refresh_dot("core"), 1.0
            )
        else:
            Clock.schedule_interval(
                lambda dt: self._refresh_dot("levels"), 1.0
            )

    def _refresh_dot(self, module: str):
        """Update connection dot color based on current connection state."""
        if module == "core":
            dot = self._core_dot_widget
            controller = self.hardware.relay_core
        else:
            dot = self._levels_dot_widget
            controller = self.hardware.relay_levels

        if dot is None:
            return

        if controller is None:
            dot.text_color = (0.5, 0.5, 0.5, 1)  # grey — not configured
        elif controller.is_connected():
            dot.text_color = (0, 0.85, 0.35, 1)  # green
        else:
            dot.text_color = (1, 0.2, 0.2, 1)  # red

    # ------------------------------------------------------------------
    # Module settings card (transport / host / port / slave / timeout)
    # ------------------------------------------------------------------

    def _build_module_settings_card(self, module: str):
        """Build connection settings card for a relay module."""
        is_core = module == "core"
        title = "Core Module (8-CH) Settings" if is_core else "Levels Module (30-CH) Settings"
        prefix = "hardware.relay_core" if is_core else "hardware.relay_levels"

        cfg = (
            self.config_manager.config.hardware.relay_core
            if is_core
            else self.config_manager.config.hardware.relay_levels
        )

        card = SettingsCard(title)

        # Transport selector row
        transport_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="50dp",
            spacing="10dp",
        )
        transport_row.add_widget(
            MDLabel(text="Transport", size_hint_x=0.4, font_style="Body1")
        )

        current_transport = cfg.transport if cfg else "tcp"

        tcp_btn = MDRaisedButton(
            text="TCP",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_transport == "tcp" else NEAR_BLACK,
            on_release=lambda x, m=module: self._set_transport(m, "tcp"),
        )
        serial_btn = MDRaisedButton(
            text="Serial",
            size_hint_x=0.3,
            md_bg_color=CORAL_ACCENT if current_transport == "serial" else NEAR_BLACK,
            on_release=lambda x, m=module: self._set_transport(m, "serial"),
        )
        transport_row.add_widget(tcp_btn)
        transport_row.add_widget(serial_btn)
        card.add_content(transport_row)

        # TCP fields: Host + Port
        host_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="50dp",
            spacing="10dp",
        )
        host_row.add_widget(
            MDLabel(text="Host", size_hint_x=0.4, font_style="Body1")
        )
        current_host = cfg.host if cfg else "192.168.1.100"
        host_btn = MDRaisedButton(
            text=current_host,
            size_hint_x=0.6,
            md_bg_color=INPUT_BUTTON,
            on_release=lambda x, m=module: self._edit_host(m),
        )
        host_row.add_widget(host_btn)
        card.add_content(host_row)

        port_field = NumpadField(
            label="Port",
            config_path=f"{prefix}.port",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=65535,
        )
        card.add_content(port_field)

        # Serial fields: serial_port string + baudrate
        serial_port_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height="50dp",
            spacing="10dp",
        )
        serial_port_row.add_widget(
            MDLabel(text="Serial Port", size_hint_x=0.4, font_style="Body1")
        )
        current_serial_port = cfg.serial_port if cfg else "/dev/ttySC0"
        serial_port_btn = MDRaisedButton(
            text=current_serial_port,
            size_hint_x=0.6,
            md_bg_color=INPUT_BUTTON,
            on_release=lambda x, m=module: self._edit_serial_port(m),
        )
        serial_port_row.add_widget(serial_port_btn)
        card.add_content(serial_port_row)

        baudrate_field = NumpadField(
            label="Baudrate",
            config_path=f"{prefix}.baudrate",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1200,
            max_value=115200,
        )
        card.add_content(baudrate_field)

        # Shared: Slave Address + Timeout
        slave_field = NumpadField(
            label="Slave Address",
            config_path=f"{prefix}.slave_address",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=247,
        )
        card.add_content(slave_field)

        timeout_field = NumpadField(
            label="Timeout (s)",
            config_path=f"{prefix}.timeout",
            config_manager=self.config_manager,
            allow_decimal=True,
            min_value=0.1,
            max_value=10.0,
        )
        card.add_content(timeout_field)

        self.add_content(card)

    def _set_transport(self, module: str, transport: str):
        """Save transport choice and rebuild settings display."""
        prefix = "hardware.relay_core" if module == "core" else "hardware.relay_levels"
        from monitoni.ui.debug_screens.widgets import update_config_value
        update_config_value(self.config_manager, f"{prefix}.transport", transport)

    def _edit_host(self, module: str):
        """Show text input dialog to edit relay host IP."""
        prefix = "hardware.relay_core" if module == "core" else "hardware.relay_levels"
        cfg = (
            self.config_manager.config.hardware.relay_core
            if module == "core"
            else self.config_manager.config.hardware.relay_levels
        )
        current = cfg.host if cfg else "192.168.1.100"
        show_confirm_dialog(
            title=f"{'Core' if module == 'core' else 'Levels'} Module Host",
            text=f"Current host: {current}\n\nEdit {prefix}.host in config/local.yaml to change.",
            on_confirm=None,
        )

    def _edit_serial_port(self, module: str):
        """Show info dialog for serial port path."""
        prefix = "hardware.relay_core" if module == "core" else "hardware.relay_levels"
        cfg = (
            self.config_manager.config.hardware.relay_core
            if module == "core"
            else self.config_manager.config.hardware.relay_levels
        )
        current = cfg.serial_port if cfg else "/dev/ttySC0"
        show_confirm_dialog(
            title=f"{'Core' if module == 'core' else 'Levels'} Serial Port",
            text=f"Current port: {current}\n\nEdit {prefix}.serial_port in config/local.yaml to change.",
            on_confirm=None,
        )

    # ------------------------------------------------------------------
    # Relay test cards
    # ------------------------------------------------------------------

    def _build_module_relay_test_card(self, module: str):
        """Build relay test card for a module."""
        is_core = module == "core"

        if is_core:
            title = "Core Relay Test"
            channel_count = 8
            cols = 4
            card = self._build_core_relay_test_card_content(title, channel_count, cols)
        else:
            title = "Levels Relay Test"
            channel_count = 30
            cols = 5
            card = self._build_levels_relay_test_card_content(title, channel_count, cols)

        self.add_content(card)

    def _build_core_relay_test_card_content(self, title: str, channel_count: int, cols: int) -> SettingsCard:
        """Build Core Module relay test card (8 channels, annotated)."""
        card = SettingsCard(title)

        cfg = self.config_manager.config.vending.motor
        motor_ch = cfg.relay_channel
        spindle_ch = cfg.spindle_lock_relay

        relay_grid = GridLayout(
            cols=cols,
            spacing="5dp",
            size_hint_y=None,
        )
        relay_grid.bind(minimum_height=relay_grid.setter("height"))

        for channel in range(1, channel_count + 1):
            # Build label: "CH1\n(Motor)" etc.
            if channel == motor_ch:
                label_text = f"CH{channel}\n(Motor)"
            elif channel == spindle_ch:
                label_text = f"CH{channel}\n(Spindle)"
            else:
                label_text = f"CH{channel}"

            btn = HoldButton(
                text=label_text,
                on_hold=lambda ch=channel: self._activate_core_relay(ch),
                on_release_hold=lambda ch=channel: self._deactivate_core_relay(ch),
            )
            btn.height = "60dp"
            relay_grid.add_widget(btn)

        card.add_content(relay_grid)
        return card

    def _build_levels_relay_test_card_content(self, title: str, channel_count: int, cols: int) -> SettingsCard:
        """Build Levels Module relay test card (30 channels, mapped channels highlighted)."""
        card = SettingsCard(title)

        # Channels mapped to door locks
        mapped_channels = set(
            self.config_manager.config.vending.door_lock.relay_channels
        )

        relay_grid = GridLayout(
            cols=cols,
            spacing="5dp",
            size_hint_y=None,
        )
        relay_grid.bind(minimum_height=relay_grid.setter("height"))

        for channel in range(1, channel_count + 1):
            is_mapped = channel in mapped_channels
            label_text = f"CH{channel}"

            btn = HoldButton(
                text=label_text,
                on_hold=lambda ch=channel: self._activate_levels_relay(ch),
                on_release_hold=lambda ch=channel: self._deactivate_levels_relay(ch),
            )
            btn.height = "56dp"
            # Highlight mapped channels with coral accent
            if is_mapped:
                btn.md_bg_color = CORAL_ACCENT
            else:
                btn.md_bg_color = NEAR_BLACK

            relay_grid.add_widget(btn)

        card.add_content(relay_grid)
        return card

    # Relay activation helpers — Core Module

    def _activate_core_relay(self, channel: int):
        """Activate a relay on the Core Module."""
        if self.hardware.relay_core:
            asyncio.create_task(self.hardware.relay_core.set_relay(channel, True))

    def _deactivate_core_relay(self, channel: int):
        """Deactivate a relay on the Core Module."""
        if self.hardware.relay_core:
            asyncio.create_task(self.hardware.relay_core.set_relay(channel, False))

    # Relay activation helpers — Levels Module

    def _activate_levels_relay(self, channel: int):
        """Activate a relay on the Levels Module."""
        if self.hardware.relay_levels:
            asyncio.create_task(self.hardware.relay_levels.set_relay(channel, True))

    def _deactivate_levels_relay(self, channel: int):
        """Deactivate a relay on the Levels Module."""
        if self.hardware.relay_levels:
            asyncio.create_task(self.hardware.relay_levels.set_relay(channel, False))

    # ------------------------------------------------------------------
    # Door lock mapping card (Levels Module)
    # ------------------------------------------------------------------

    def _build_door_lock_card(self):
        """Build door lock relay mapping card — channels refer to Levels Module."""
        card = SettingsCard("Door Lock Mapping (Levels Module)")

        levels = self.config_manager.config.vending.levels
        relay_channels = self.config_manager.config.vending.door_lock.relay_channels

        for level in range(1, levels + 1):
            current_channel = relay_channels[level - 1] if level - 1 < len(relay_channels) else 0

            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="50dp",
                spacing="10dp",
            )

            label = MDLabel(
                text=f"Level {level}:",
                size_hint_x=0.6,
                font_style="Body1",
            )
            row.add_widget(label)

            btn = MDRaisedButton(
                text=str(current_channel),
                size_hint_x=0.4,
                md_bg_color=INPUT_BUTTON,
                on_release=lambda x, lv=level: self._edit_door_lock_channel(lv, x),
            )
            btn.level = level
            row.add_widget(btn)

            card.add_content(row)

        # Unlock duration
        unlock_duration_field = NumpadField(
            label="Unlock Duration (s)",
            config_path="vending.door_lock.unlock_duration_s",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=5,
            max_value=120,
        )
        card.add_content(unlock_duration_field)

        self.add_content(card)

    def _edit_door_lock_channel(self, level: int, button: MDRaisedButton):
        """Edit relay channel for a door lock level."""
        from monitoni.ui.debug_screens.widgets import NumpadDialog

        relay_channels = self.config_manager.config.vending.door_lock.relay_channels
        current_value = relay_channels[level - 1] if level - 1 < len(relay_channels) else 0

        def on_submit(new_value: float):
            new_channels = list(relay_channels)
            while len(new_channels) < level:
                new_channels.append(0)
            new_channels[level - 1] = int(new_value)

            update_dict = {
                "vending": {
                    "door_lock": {
                        "relay_channels": new_channels
                    }
                }
            }

            show_confirm_dialog(
                title="Confirmation Required",
                text=f"Set Level {level} to Levels CH{int(new_value)}?\n\nThis is a hardware-relevant setting.",
                on_confirm=lambda: self._apply_door_lock_change(update_dict, button, int(new_value)),
            )

        dialog = NumpadDialog(
            title=f"Level {level} Relay Channel (Levels Module)",
            initial_value=float(current_value),
            min_value=1,
            max_value=30,
            allow_decimal=False,
            on_submit=on_submit,
        )
        dialog.open()

    def _apply_door_lock_change(self, update_dict: dict, button: MDRaisedButton, new_value: int):
        """Apply door lock channel change."""
        try:
            self.config_manager.save_local(update_dict)
            button.text = str(new_value)
        except Exception as e:
            print(f"Failed to update door lock channel: {e}")

    # ------------------------------------------------------------------
    # Live status card (dual-module)
    # ------------------------------------------------------------------

    def _build_status_card(self):
        """Build combined live status card for both modules."""

        async def get_relay_status() -> List[Tuple[str, str, Tuple[float, float, float, float]]]:
            """Get status of key relays from both modules (async)."""
            status_items = []
            config = self.config_manager.config

            # --- Core Module ---
            motor_ch = config.vending.motor.relay_channel
            spindle_ch = config.vending.motor.spindle_lock_relay

            if not self.hardware.relay_core:
                status_items.append(("Core Module", "Not connected", (1, 0, 0, 1)))
            else:
                try:
                    motor_state = await self.hardware.relay_core.get_relay(motor_ch)
                    state_text = "ON" if motor_state else "OFF"
                    color = (0, 1, 0, 1) if motor_state else (0.5, 0.5, 0.5, 1)
                    status_items.append((f"Core: Motor (CH{motor_ch})", state_text, color))
                except Exception:
                    status_items.append((f"Core: Motor (CH{motor_ch})", "ERROR", (1, 0, 0, 1)))

                try:
                    spindle_state = await self.hardware.relay_core.get_relay(spindle_ch)
                    state_text = "ON" if spindle_state else "OFF"
                    color = (0, 1, 0, 1) if spindle_state else (0.5, 0.5, 0.5, 1)
                    status_items.append((f"Core: Spindle (CH{spindle_ch})", state_text, color))
                except Exception:
                    status_items.append((f"Core: Spindle (CH{spindle_ch})", "ERROR", (1, 0, 0, 1)))

            # --- Levels Module ---
            door_channels = config.vending.door_lock.relay_channels[:3]

            if not self.hardware.relay_levels:
                status_items.append(("Levels Module", "Not connected", (1, 0, 0, 1)))
            else:
                for i, ch in enumerate(door_channels):
                    try:
                        door_state = await self.hardware.relay_levels.get_relay(ch)
                        state_text = "ON" if door_state else "OFF"
                        color = (0, 1, 0, 1) if door_state else (0.5, 0.5, 0.5, 1)
                        status_items.append((f"Levels: Door {i + 1} (CH{ch})", state_text, color))
                    except Exception:
                        status_items.append((f"Levels: Door {i + 1} (CH{ch})", "ERROR", (1, 0, 0, 1)))

            return status_items

        status_card = LiveStatusCard(
            title="Relay Status",
            get_status_callback=get_relay_status,
            update_interval=1.0,
        )
        self.add_content(status_card)

    # ------------------------------------------------------------------
    # Factory reset
    # ------------------------------------------------------------------

    def _build_reset_button(self):
        """Build factory reset button."""
        reset_btn = MDRaisedButton(
            text="Factory Reset",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._reset_to_defaults(),
        )
        self.add_content(reset_btn)

    def _reset_to_defaults(self):
        """Reset relay and door lock settings to defaults."""
        def do_reset():
            reset_section_to_defaults(self.config_manager, "hardware.relay_core")
            reset_section_to_defaults(self.config_manager, "hardware.relay_levels")
            reset_section_to_defaults(self.config_manager, "vending.door_lock")

        show_confirm_dialog(
            title="Factory Reset",
            text=(
                "Reset relay settings?\n\n"
                "This resets Core Module, Levels Module, and door lock configuration."
            ),
            on_confirm=do_reset,
        )

    # ------------------------------------------------------------------
    # Safety cleanup
    # ------------------------------------------------------------------

    def on_pre_leave(self, *args):
        """Safety: deactivate any held relays when leaving screen."""
        super().on_pre_leave(*args)
        # No cascade test to stop — individual hold buttons auto-release via touch.grab pattern
