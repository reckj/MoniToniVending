"""
Customer-facing screen for product selection and purchase.

Displays product levels and handles purchase flow with QR code display.
"""

import asyncio
import io
import os
from pathlib import Path
import qrcode
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.graphics import Color, Rectangle, Triangle, RoundedRectangle
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.card import MDCard

from monitoni.core.config import Config
from monitoni.core.logger import Logger
from monitoni.core.state_machine import PurchaseStateMachine, State, Event
from monitoni.hardware.manager import HardwareManager

# Register icon font
from monitoni.ui.icons import register_icon_font, get_icon
register_icon_font()


class ProductButton(MDRaisedButton):
    """Button for product level selection."""
    
    def __init__(self, level: int, **kwargs):
        """
        Initialize product button.
        
        Args:
            level: Product level (1-10)
        """
        super().__init__(**kwargs)
        self.level = level
        self.text = f"Level {level}"
        self.size_hint = (1, None)
        self.height = "90dp"
        self.font_size = "24sp"
        self.md_bg_color = (0.1, 0.5, 0.8, 1)  # Nice blue


class TurnButton(MDRaisedButton):
    """
    Button for manual motor control.
    
    While pressed: opens spindle lock, starts motor after delay.
    On release: stops motor after delay, closes spindle lock.
    """
    
    def __init__(self, hardware, config, logger, **kwargs):
        """
        Initialize turn button.
        
        Args:
            hardware: Hardware manager for relay control
            config: System configuration
            logger: Logger instance
        """
        super().__init__(**kwargs)
        self.hardware = hardware
        self.config = config
        self.logger = logger
        
        self.text = "TURN"
        self.size_hint = (1, None)
        self.height = "100dp"
        self.font_size = "28sp"
        self.md_bg_color = (0.8, 0.4, 0.1, 1)  # Orange
        
        self._is_turning = False
        self._motor_task = None
        
        # Bind touch events
        self.bind(on_touch_down=self._on_press)
        self.bind(on_touch_up=self._on_release)
        
    def _on_press(self, instance, touch):
        """Handle button press - start motor sequence."""
        if not self.collide_point(*touch.pos):
            return False
            
        if self._is_turning:
            return True
            
        self._is_turning = True
        self.md_bg_color = (0.2, 0.8, 0.2, 1)  # Green while active
        self.text = "TURNING..."
        
        # Start motor sequence in background
        import threading
        
        def start_motor_sequence():
            import time
            motor_cfg = self.config.vending.motor
            
            try:
                # Open spindle lock
                if self.hardware.relay:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Open spindle lock (relay ON)
                    loop.run_until_complete(
                        self.hardware.relay.set_relay(motor_cfg.spindle_lock_relay, True)
                    )
                    self.logger.info(f"Spindle lock opened (relay {motor_cfg.spindle_lock_relay})")
                    
                    # Wait before starting motor
                    time.sleep(motor_cfg.spindle_pre_delay_ms / 1000.0)
                    
                    # Start motor (only if still pressing)
                    if self._is_turning:
                        loop.run_until_complete(
                            self.hardware.relay.set_relay(motor_cfg.relay_channel, True)
                        )
                        self.logger.info(f"Motor started (relay {motor_cfg.relay_channel})")
                    
                    loop.close()
            except Exception as e:
                self.logger.error(f"Motor start error: {e}")
        
        self._motor_task = threading.Thread(target=start_motor_sequence, daemon=True)
        self._motor_task.start()
        
        return True
        
    def _on_release(self, instance, touch):
        """Handle button release - stop motor sequence."""
        if not self._is_turning:
            return False
            
        self._is_turning = False
        self.md_bg_color = (0.8, 0.4, 0.1, 1)  # Back to orange
        self.text = "TURN"
        
        # Stop motor sequence in background
        import threading
        
        def stop_motor_sequence():
            import time
            motor_cfg = self.config.vending.motor
            
            try:
                if self.hardware.relay:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Keep motor running for delay
                    time.sleep(motor_cfg.spin_delay_ms / 1000.0)
                    
                    # Stop motor
                    loop.run_until_complete(
                        self.hardware.relay.set_relay(motor_cfg.relay_channel, False)
                    )
                    self.logger.info(f"Motor stopped (relay {motor_cfg.relay_channel})")
                    
                    # Wait before closing spindle
                    time.sleep(motor_cfg.spindle_post_delay_ms / 1000.0)
                    
                    # Close spindle lock (relay OFF)
                    loop.run_until_complete(
                        self.hardware.relay.set_relay(motor_cfg.spindle_lock_relay, False)
                    )
                    self.logger.info(f"Spindle lock closed (relay {motor_cfg.spindle_lock_relay})")
                    
                    loop.close()
            except Exception as e:
                self.logger.error(f"Motor stop error: {e}")
        
        threading.Thread(target=stop_motor_sequence, daemon=True).start()
        
        return True

class StatusCard(MDCard):
    """Card displaying current status."""
    
    status_text = StringProperty("Welcome! Select a product level")
    
    def __init__(self, **kwargs):
        """Initialize status card."""
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = "100dp"
        self.padding = "15dp"
        self.spacing = "10dp"
        self.md_bg_color = (0.15, 0.15, 0.15, 1)
        self.radius = [15, 15, 15, 15]
        
        # Status label
        self.status_label = MDLabel(
            text=self.status_text,
            halign='center',
            font_style='H5',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1)
        )
        self.add_widget(self.status_label)
        
    def update_status(self, text: str, color: tuple = (1, 1, 1, 1)):
        """
        Update status text and color.
        
        Args:
            text: Status text
            color: Text color (RGBA)
        """
        self.status_label.text = text
        self.status_label.text_color = color


class DebugAccessIndicator(Widget):
    """Subtle triangle indicator in corner for debug access."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (40, 40)
        self.pos_hint = {'right': 1, 'top': 1}
        
        with self.canvas:
            # Subtle semi-transparent triangle in top-right corner
            Color(0.3, 0.3, 0.3, 0.4)  # Dark gray, slightly transparent
            self.triangle = Triangle(points=[
                self.x + self.width, self.y + self.height,  # top-right
                self.x + self.width, self.y,               # bottom-right
                self.x, self.y + self.height               # top-left
            ])
            
        self.bind(pos=self._update_triangle, size=self._update_triangle)
        
    def _update_triangle(self, *args):
        """Update triangle position."""
        self.triangle.points = [
            self.x + self.width, self.y + self.height,
            self.x + self.width, self.y,
            self.x, self.y + self.height
        ]


class QRCodeView(BoxLayout):
    """View for displaying QR code and return button."""

    def __init__(self, on_return_callback, app_config: Config, **kwargs):
        """
        Initialize QR code view.

        Args:
            on_return_callback: Callback when return button pressed
            app_config: System configuration for QR URL generation
        """
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = "20dp"
        self.spacing = "15dp"
        self.on_return_callback = on_return_callback
        self.app_config = app_config

        # QR code cache directory
        self.qr_cache_dir = Path("assets/qr_codes")
        self.qr_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Level label
        self.level_label = MDLabel(
            text="Level 1",
            halign='center',
            font_style='H4',
            size_hint=(1, None),
            height="50dp"
        )
        self.add_widget(self.level_label)
        
        # Instruction label
        self.instruction_label = MDLabel(
            text="Scan QR code to purchase",
            halign='center',
            font_style='Body1',
            size_hint=(1, None),
            height="30dp"
        )
        self.add_widget(self.instruction_label)
        
        # QR code image container
        qr_container = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1)
        )
        
        # QR code image
        self.qr_image = Image(
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=True
        )
        qr_container.add_widget(self.qr_image)
        self.add_widget(qr_container)
        
        # Status label for waiting/timeout
        self.status_label = MDLabel(
            text="Waiting for payment...",
            halign='center',
            font_style='Body1',
            size_hint=(1, None),
            height="40dp",
            theme_text_color='Custom',
            text_color=(1, 1, 0, 1)  # Yellow
        )
        self.add_widget(self.status_label)
        
        # Return button with arrow icon in text
        arrow_icon = get_icon('arrow-left')
        
        return_btn = MDRaisedButton(
            text=f"{arrow_icon}  Back to Levels",
            size_hint=(1, None),
            height="70dp",
            font_size="20sp",
            font_name='Icons',  # Use icon font for the whole button
            md_bg_color=(0.3, 0.3, 0.3, 1),
            on_release=lambda x: self.on_return_callback()
        )
        self.add_widget(return_btn)
        
    def set_level(self, level: int):
        """
        Set the displayed level and generate QR code.
        
        Args:
            level: Product level to display
        """
        self.level_label.text = f"Level {level}"
        
        # Generate or load QR code
        self._load_qr_code(level)
        
    def _load_qr_code(self, level: int):
        """
        Load or generate QR code for level.
        
        Args:
            level: Product level
        """
        qr_path = self.qr_cache_dir / f"level_{level}.png"
        
        # Check if custom QR code exists (uploaded via frontend)
        custom_qr_path = self.qr_cache_dir / f"custom_level_{level}.png"
        if custom_qr_path.exists():
            self.qr_image.source = str(custom_qr_path)
            return
            
        # Generate placeholder QR code if not exists
        if not qr_path.exists():
            self._generate_qr_code(level, qr_path)
            
        self.qr_image.source = str(qr_path)
        self.qr_image.reload()
        
    def _generate_qr_code(self, level: int, output_path: Path):
        """
        Generate QR code for level using configured URLs.

        Args:
            level: Product level
            output_path: Path to save QR code
        """
        # Get URL for this level from configuration
        url = self.app_config.vending.qr_urls.get_url_for_level(
            level,
            self.app_config.system.machine_id
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create image with white background
        img = qr.make_image(fill_color="black", back_color="white")

        # Save QR code
        img.save(str(output_path))
        
    def set_status(self, text: str, color: tuple = (1, 1, 0, 1)):
        """
        Set the status text.
        
        Args:
            text: Status text
            color: Text color (RGBA)
        """
        self.status_label.text = text
        self.status_label.text_color = color


class CustomerScreen(Screen):
    """
    Customer-facing screen.
    
    Displays product levels vertically and shows QR code on selection.
    """
    
    def __init__(
        self,
        app,
        app_config: Config,
        hardware: HardwareManager,
        state_machine: PurchaseStateMachine,
        logger: Logger,
        **kwargs
    ):
        """
        Initialize customer screen.
        
        Args:
            app: Main application instance
            app_config: System configuration
            hardware: Hardware manager
            state_machine: Purchase state machine
            logger: Logger instance
        """
        super().__init__(**kwargs)
        
        self.app = app
        self.app_config = app_config
        self.hardware = hardware
        self.state_machine = state_machine
        self.logger = logger
        
        # Current view: 'levels' or 'qr'
        self._current_view = 'levels'
        self._selected_level = None
        
        # Timeout tracking
        self._purchase_timeout_event = None
        
        # Build UI
        self._build_ui()
        
        # Schedule state updates
        Clock.schedule_interval(self._update_ui, 0.5)
        
        # Debug mode access (5 taps in top-right corner)
        self._debug_tap_count = 0
        self._debug_tap_timeout = None
        
    def _build_ui(self):
        """Build the customer UI."""
        # Main container
        self.main_layout = BoxLayout(orientation='vertical')
        
        # Level selection view
        self.levels_view = self._build_levels_view()
        
        # QR code view
        self.qr_view = QRCodeView(
            on_return_callback=self._on_return_pressed,
            app_config=self.app_config
        )
        
        # Start with levels view
        self.main_layout.add_widget(self.levels_view)
        
        self.add_widget(self.main_layout)
        
    def _build_levels_view(self):
        """Build the level selection view."""
        # Use FloatLayout to overlay the debug indicator
        from kivy.uix.floatlayout import FloatLayout
        
        outer_layout = FloatLayout()
        
        # Main content layout
        layout = BoxLayout(
            orientation='vertical', 
            padding="20dp", 
            spacing="15dp",
            size_hint=(1, 1)
        )
        
        # Header with logo/title
        header = MDLabel(
            text="MoniToni Vending",
            halign='center',
            font_style='H3',
            size_hint=(1, None),
            height="80dp"
        )
        layout.add_widget(header)
        
        # Status card
        self.status_card = StatusCard()
        layout.add_widget(self.status_card)
        
        # Scrollable product buttons (vertical stack)
        scroll = ScrollView(size_hint=(1, 1))
        
        button_container = BoxLayout(
            orientation='vertical',
            spacing="12dp",
            size_hint_y=None,
            padding=("0dp", "10dp")
        )
        button_container.bind(minimum_height=button_container.setter('height'))
        
        # Create buttons for each level (single column)
        self.level_buttons = {}
        for level in range(1, self.app_config.vending.levels + 1):
            btn = ProductButton(level=level)
            btn.bind(on_press=self._on_level_selected)
            self.level_buttons[level] = btn
            button_container.add_widget(btn)
            
        scroll.add_widget(button_container)
        layout.add_widget(scroll)
        
        # Add turn button at bottom
        self.turn_button = TurnButton(
            hardware=self.hardware,
            config=self.app_config,
            logger=self.logger
        )
        layout.add_widget(self.turn_button)
        
        outer_layout.add_widget(layout)
        
        # Subtle debug indicator triangle in corner
        debug_indicator = DebugAccessIndicator()
        outer_layout.add_widget(debug_indicator)
        
        # Invisible touch area for debug access
        from kivy.uix.button import Button
        debug_touch_area = Button(
            background_color=(0, 0, 0, 0),  # Fully transparent
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'right': 1, 'top': 1}
        )
        debug_touch_area.bind(on_press=self._on_debug_tap)
        outer_layout.add_widget(debug_touch_area)
        
        return outer_layout
        
    def _on_level_selected(self, button: ProductButton):
        """
        Handle product level selection.
        
        Args:
            button: Selected button
        """
        level = button.level
        
        # Only allow selection in idle state
        if not self.state_machine.is_idle():
            self.logger.warning(f"Level {level} selected but not in idle state")
            return
            
        self.logger.info(f"Level {level} selected", purchase_id=None)
        self._selected_level = level
        
        # Start purchase
        purchase_id = self.state_machine.start_purchase(level)
        self.logger.info(f"Purchase started", purchase_id=purchase_id)
        
        # Trigger state transition
        asyncio.create_task(
            self.state_machine.handle_event(Event.PURCHASE_SELECTED)
        )
        
        # Switch to QR view
        self._switch_to_qr_view(level)
        
        # Highlight selected zone on LED
        if self.hardware.led:
            asyncio.create_task(
                self.hardware.led.set_zone_color(
                    level - 1,  # 0-indexed
                    0, 255, 0,  # Green
                    brightness=1.0
                )
            )
            
        # Start timeout timer
        timeout_seconds = self.app_config.vending.timings.purchase_timeout_s
        self._start_purchase_timeout(timeout_seconds)
        
    def _switch_to_qr_view(self, level: int):
        """
        Switch to QR code view.
        
        Args:
            level: Selected product level
        """
        self._current_view = 'qr'
        
        # Update QR view with level
        self.qr_view.set_level(level)
        self.qr_view.set_status("Waiting for payment...", (1, 1, 0, 1))
        
        # Swap views
        self.main_layout.clear_widgets()
        self.main_layout.add_widget(self.qr_view)
        
    def _switch_to_levels_view(self):
        """Switch back to level selection view."""
        self._current_view = 'levels'
        self._selected_level = None
        
        # Cancel timeout
        self._cancel_purchase_timeout()
        
        # Swap views
        self.main_layout.clear_widgets()
        self.main_layout.add_widget(self.levels_view)
        
        # Reset status
        self.status_card.update_status("Welcome! Select a product level", (1, 1, 1, 1))
        
        # Reset LED
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.turn_off())
            
    def _on_return_pressed(self):
        """Handle return button press."""
        self.logger.info("Return pressed, cancelling purchase")
        
        # Reset state machine
        asyncio.create_task(
            self.state_machine.handle_event(Event.RESET)
        )
        
        # Switch back to levels
        self._switch_to_levels_view()
        
    def _start_purchase_timeout(self, seconds: float):
        """
        Start purchase timeout timer.
        
        Args:
            seconds: Timeout in seconds
        """
        self._cancel_purchase_timeout()
        self._purchase_timeout_event = Clock.schedule_once(
            self._on_purchase_timeout,
            seconds
        )
        
    def _cancel_purchase_timeout(self):
        """Cancel purchase timeout timer."""
        if self._purchase_timeout_event:
            self._purchase_timeout_event.cancel()
            self._purchase_timeout_event = None
            
    def _on_purchase_timeout(self, dt):
        """Handle purchase timeout."""
        self.logger.warning("Purchase timeout - no server response")
        
        # Update QR view status
        if self._current_view == 'qr':
            self.qr_view.set_status(
                "Timeout - No response. Please try again.",
                (1, 0.5, 0, 1)  # Orange
            )
            
        # Trigger timeout event in state machine
        asyncio.create_task(
            self.state_machine.handle_event(Event.TIMEOUT_PURCHASE)
        )
        
        # Auto-return to levels after 3 seconds
        Clock.schedule_once(
            lambda dt: self._switch_to_levels_view(),
            3.0
        )
            
    def _update_ui(self, dt):
        """
        Update UI based on current state.
        
        Args:
            dt: Delta time from Clock
        """
        state = self.state_machine.state
        
        # Handle state-based updates
        if self._current_view == 'qr':
            if state == State.DOOR_UNLOCKED:
                self.qr_view.set_status(
                    "Payment received! Door unlocked.",
                    (0, 1, 0, 1)  # Green
                )
                self._cancel_purchase_timeout()
                
            elif state == State.DOOR_OPENED:
                self.qr_view.set_status(
                    "Take your product and close the door.",
                    (0, 1, 0, 1)
                )
                
            elif state == State.DOOR_ALARM:
                self.qr_view.set_status(
                    "Please close the door!",
                    (1, 0.5, 0, 1)  # Orange
                )
                
            elif state == State.COMPLETING:
                self.qr_view.set_status(
                    "Thank you! Enjoy!",
                    (0, 1, 0, 1)
                )
                # Return to levels after completion
                Clock.schedule_once(
                    lambda dt: self._switch_to_levels_view(),
                    2.0
                )
                
            elif state == State.IDLE:
                # Reset to levels view if we're back to idle
                if self._current_view == 'qr':
                    self._switch_to_levels_view()
                    
        else:
            # Levels view updates
            if state == State.IDLE:
                self.status_card.update_status(
                    "Welcome! Select a product level",
                    color=(1, 1, 1, 1)
                )
                self._enable_buttons(True)
                
            elif state == State.SLEEP:
                self.status_card.update_status(
                    "Touch to wake up",
                    color=(0.5, 0.5, 0.5, 1)
                )
                self._enable_buttons(False)
            
    def _enable_buttons(self, enabled: bool):
        """
        Enable or disable product buttons.
        
        Args:
            enabled: True to enable, False to disable
        """
        for button in self.level_buttons.values():
            button.disabled = not enabled
            
    def _on_debug_tap(self, instance):
        """Handle debug area tap."""
        self._debug_tap_count += 1
        
        # Reset counter after timeout
        if self._debug_tap_timeout:
            self._debug_tap_timeout.cancel()
        self._debug_tap_timeout = Clock.schedule_once(
            lambda dt: setattr(self, '_debug_tap_count', 0),
            2.0
        )
        
        # Switch to debug after 5 taps
        if self._debug_tap_count >= 5:
            self.logger.info("Debug mode accessed")
            self._debug_tap_count = 0
            self.app.switch_to_debug()
            
    def on_touch_down(self, touch):
        """Handle touch events for wake-up."""
        # Wake up from sleep
        if self.state_machine.state == State.SLEEP:
            asyncio.create_task(
                self.state_machine.handle_event(Event.TOUCH_INPUT)
            )
            
        return super().on_touch_down(touch)
