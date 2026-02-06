"""
Motor settings and testing screen.

Provides motor timing configuration, test functions, and live status.
"""

import asyncio
from typing import Optional, List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard, HoldButton, NumpadField, LiveStatusCard,
    show_confirm_dialog, reset_section_to_defaults, CORAL_ACCENT
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class MotorSettingsScreen(BaseDebugSubScreen):
    """
    Motor configuration and testing screen.

    Provides:
    - Motor and spindle relay channel configuration
    - Timing parameters (spin delay, spindle pre/post delay)
    - Full motor test sequence (hold-to-activate with spindle)
    - Individual component tests (motor only, spindle only)
    - Timing sequence visualization
    - Live motor and spindle status
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
        Initialize motor settings screen.

        Args:
            hardware: HardwareManager instance
            config_manager: ConfigManager instance
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager
        self.title = "Motor-Einstellungen"

        # Motor test state tracking
        self._motor_test_running = False
        self._spindle_open = False
        self._scheduled_events = []

        super().__init__(navigate_back=navigate_back, **kwargs)
        self._build_content()

    def _build_content(self):
        """Build the motor settings screen content."""
        # Card 1: Motor Configuration
        self._build_motor_config_card()

        # Card 2: Motor Test
        self._build_motor_test_card()

        # Card 3: Timing Visualization
        self._build_timing_visualization_card()

        # Card 4: Live Status
        self._build_status_card()

        # Reset button
        self._build_reset_button()

    def _build_motor_config_card(self):
        """Build motor configuration card."""
        card = SettingsCard("Motor-Konfiguration")

        # Motor relay channel
        motor_channel_field = NumpadField(
            label="Motor Relay-Kanal",
            config_path="vending.motor.relay_channel",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=32,
            on_value_changed=lambda v: self._update_timing_visualization()
        )
        card.add_content(motor_channel_field)

        # Spindle lock relay
        spindle_channel_field = NumpadField(
            label="Spindel-Schloss Relay",
            config_path="vending.motor.spindle_lock_relay",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=32,
            on_value_changed=lambda v: self._update_timing_visualization()
        )
        card.add_content(spindle_channel_field)

        # Spin delay
        spin_delay_field = NumpadField(
            label="Drehzeit (ms)",
            config_path="vending.motor.spin_delay_ms",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=50,
            max_value=5000,
            on_value_changed=lambda v: self._update_timing_visualization()
        )
        card.add_content(spin_delay_field)

        # Spindle pre-delay
        pre_delay_field = NumpadField(
            label="Spindel Vorlaufzeit (ms)",
            config_path="vending.motor.spindle_pre_delay_ms",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=2000,
            on_value_changed=lambda v: self._update_timing_visualization()
        )
        card.add_content(pre_delay_field)

        # Spindle post-delay
        post_delay_field = NumpadField(
            label="Spindel Nachlaufzeit (ms)",
            config_path="vending.motor.spindle_post_delay_ms",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=2000,
            on_value_changed=lambda v: self._update_timing_visualization()
        )
        card.add_content(post_delay_field)

        self.add_content(card)

    def _build_motor_test_card(self):
        """Build motor testing card."""
        card = SettingsCard("Motor-Test")

        # Full motor test with spindle sequence
        full_test_btn = HoldButton(
            text="Motor testen",
            on_hold=self._start_motor_test,
            on_release_hold=self._stop_motor_test
        )
        full_test_btn.height = "80dp"
        card.add_content(full_test_btn)

        # Spacer
        spacer = BoxLayout(size_hint_y=None, height="10dp")
        card.add_content(spacer)

        # Individual test buttons row
        test_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        # Spindle lock test
        spindle_test_btn = HoldButton(
            text="Spindel-Schloss testen",
            on_hold=self._activate_spindle,
            on_release_hold=self._deactivate_spindle
        )
        test_row.add_widget(spindle_test_btn)

        # Motor direct test
        motor_direct_test_btn = HoldButton(
            text="Motor direkt testen",
            on_hold=self._activate_motor,
            on_release_hold=self._deactivate_motor
        )
        test_row.add_widget(motor_direct_test_btn)

        card.add_content(test_row)
        self.add_content(card)

    def _build_timing_visualization_card(self):
        """Build timing sequence visualization card."""
        card = SettingsCard("Timing-Visualisierung")

        # Timing sequence display
        self.timing_label = MDLabel(
            text=self._get_timing_text(),
            font_style='Body2',
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.timing_label.bind(texture_size=self.timing_label.setter('size'))
        card.add_content(self.timing_label)

        self.add_content(card)

    def _get_timing_text(self) -> str:
        """Generate timing sequence text."""
        config = self.config_manager.config.vending.motor
        pre_delay = config.spindle_pre_delay_ms
        post_delay = config.spindle_post_delay_ms

        return f"""Sequenz:
1. Spindel öffnen (Relay {config.spindle_lock_relay})
2. Warte {pre_delay}ms
3. Motor AN (Relay {config.relay_channel}) - solange gehalten
4. Motor AUS
5. Warte {post_delay}ms
6. Spindel schließen"""

    def _update_timing_visualization(self):
        """Update timing visualization text."""
        if hasattr(self, 'timing_label'):
            self.timing_label.text = self._get_timing_text()

    def _build_status_card(self):
        """Build live motor and spindle status card."""
        def get_motor_status() -> List[Tuple[str, str, Tuple[float, float, float, float]]]:
            """Get status of motor and spindle relays."""
            if not self.hardware.relay:
                return [("Motor", "Relay nicht verbunden", (1, 0, 0, 1))]

            status_items = []
            config = self.config_manager.config.vending.motor

            # Motor relay
            try:
                motor_state = asyncio.run(self.hardware.relay.get_relay(config.relay_channel))
                state_text = "AN" if motor_state else "AUS"
                color = (0, 1, 0, 1) if motor_state else (0.5, 0.5, 0.5, 1)
                status_items.append((f"Motor (R{config.relay_channel})", state_text, color))
            except Exception:
                status_items.append((f"Motor (R{config.relay_channel})", "ERROR", (1, 0, 0, 1)))

            # Spindle lock relay
            try:
                spindle_state = asyncio.run(self.hardware.relay.get_relay(config.spindle_lock_relay))
                state_text = "AN" if spindle_state else "AUS"
                color = (0, 1, 0, 1) if spindle_state else (0.5, 0.5, 0.5, 1)
                status_items.append((f"Spindel (R{config.spindle_lock_relay})", state_text, color))
            except Exception:
                status_items.append((f"Spindel (R{config.spindle_lock_relay})", "ERROR", (1, 0, 0, 1)))

            return status_items

        status_card = LiveStatusCard(
            title="Motor-Status",
            get_status_callback=get_motor_status,
            update_interval=0.5
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
        """Reset motor settings to defaults."""
        def do_reset():
            reset_section_to_defaults(self.config_manager, "vending.motor")
            self._update_timing_visualization()

        show_confirm_dialog(
            title="Werkseinstellungen",
            text="Motor-Einstellungen zurücksetzen?",
            on_confirm=do_reset
        )

    def _start_motor_test(self):
        """Start full motor test with spindle sequence."""
        if not self._motor_test_running and self.hardware.relay:
            self._motor_test_running = True
            asyncio.create_task(self._run_motor_sequence())

    def _stop_motor_test(self):
        """Stop motor test and safely shut down sequence."""
        if self._motor_test_running:
            self._motor_test_running = False

            # Cancel all scheduled events
            for event in self._scheduled_events:
                event.cancel()
            self._scheduled_events.clear()

            # Immediately deactivate motor
            asyncio.create_task(self._shutdown_motor_sequence())

    async def _run_motor_sequence(self):
        """Run the full motor sequence: spindle open -> delay -> motor on."""
        try:
            config = self.config_manager.config.vending.motor

            # Step 1: Open spindle lock
            await self.hardware.relay.set_relay(config.spindle_lock_relay, True)
            self._spindle_open = True

            # Step 2: Wait pre-delay
            await asyncio.sleep(config.spindle_pre_delay_ms / 1000.0)

            # Step 3: Activate motor (will run while held)
            if self._motor_test_running:
                await self.hardware.relay.set_relay(config.relay_channel, True)

        except Exception as e:
            print(f"Motor sequence error: {e}")
            self._motor_test_running = False

    async def _shutdown_motor_sequence(self):
        """Shutdown motor sequence: motor off -> delay -> spindle close."""
        try:
            config = self.config_manager.config.vending.motor

            # Step 1: Deactivate motor immediately
            await self.hardware.relay.set_relay(config.relay_channel, False)

            # Step 2: Wait post-delay
            await asyncio.sleep(config.spindle_post_delay_ms / 1000.0)

            # Step 3: Close spindle lock
            await self.hardware.relay.set_relay(config.spindle_lock_relay, False)
            self._spindle_open = False

        except Exception as e:
            print(f"Motor shutdown error: {e}")

    def _activate_spindle(self):
        """Activate spindle lock relay only."""
        if self.hardware.relay:
            config = self.config_manager.config.vending.motor
            asyncio.create_task(self.hardware.relay.set_relay(config.spindle_lock_relay, True))

    def _deactivate_spindle(self):
        """Deactivate spindle lock relay only."""
        if self.hardware.relay:
            config = self.config_manager.config.vending.motor
            asyncio.create_task(self.hardware.relay.set_relay(config.spindle_lock_relay, False))

    def _activate_motor(self):
        """Activate motor relay only (direct test)."""
        if self.hardware.relay:
            config = self.config_manager.config.vending.motor
            asyncio.create_task(self.hardware.relay.set_relay(config.relay_channel, True))

    def _deactivate_motor(self):
        """Deactivate motor relay only (direct test)."""
        if self.hardware.relay:
            config = self.config_manager.config.vending.motor
            asyncio.create_task(self.hardware.relay.set_relay(config.relay_channel, False))

    def on_pre_leave(self, *args):
        """Safety: deactivate motor and spindle when leaving screen."""
        super().on_pre_leave(*args)

        # Stop any running motor test
        self._stop_motor_test()

        # Ensure both relays are off
        if self.hardware.relay:
            config = self.config_manager.config.vending.motor
            asyncio.create_task(self.hardware.relay.set_relay(config.relay_channel, False))
            asyncio.create_task(self.hardware.relay.set_relay(config.spindle_lock_relay, False))
