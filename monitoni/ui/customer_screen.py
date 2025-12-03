"""
Customer-facing screen for product selection and purchase.

Displays product levels and handles purchase flow.
"""

import asyncio
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.card import MDCard

from monitoni.core.config import Config
from monitoni.core.logger import Logger
from monitoni.core.state_machine import PurchaseStateMachine, State, Event
from monitoni.hardware.manager import HardwareManager


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
        self.height = "80dp"
        self.md_bg_color = (0, 0.6, 1, 1)  # Blue
        

class StatusCard(MDCard):
    """Card displaying current status."""
    
    status_text = StringProperty("Welcome! Select a product level")
    
    def __init__(self, **kwargs):
        """Initialize status card."""
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = "120dp"
        self.padding = "20dp"
        self.spacing = "10dp"
        self.md_bg_color = (0.1, 0.1, 0.1, 1)
        
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


class CustomerScreen(Screen):
    """
    Customer-facing screen.
    
    Displays product levels and handles purchase flow.
    """
    
    def __init__(
        self,
        app,
        config: Config,
        hardware: HardwareManager,
        state_machine: PurchaseStateMachine,
        logger: Logger,
        **kwargs
    ):
        """
        Initialize customer screen.
        
        Args:
            app: Main application instance
            config: System configuration
            hardware: Hardware manager
            state_machine: Purchase state machine
            logger: Logger instance
        """
        super().__init__(**kwargs)
        
        self.app = app
        self.config = config
        self.hardware = hardware
        self.state_machine = state_machine
        self.logger = logger
        
        # Build UI
        self._build_ui()
        
        # Schedule state updates
        Clock.schedule_interval(self._update_ui, 0.5)
        
        # Debug mode access (5 taps in top-right corner)
        self._debug_tap_count = 0
        self._debug_tap_timeout = None
        
    def _build_ui(self):
        """Build the customer UI."""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding="20dp", spacing="20dp")
        
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
        
        # Product level grid
        grid = GridLayout(
            cols=2,
            spacing="15dp",
            size_hint=(1, 1)
        )
        
        # Create buttons for each level
        self.level_buttons = {}
        for level in range(1, self.config.vending.levels + 1):
            btn = ProductButton(level=level)
            btn.bind(on_press=self._on_level_selected)
            self.level_buttons[level] = btn
            grid.add_widget(btn)
            
        layout.add_widget(grid)
        
        # Debug access area (invisible)
        debug_area = MDIconButton(
            icon="",
            pos_hint={'right': 1, 'top': 1},
            size_hint=(None, None),
            size=("60dp", "60dp")
        )
        debug_area.bind(on_press=self._on_debug_tap)
        
        # Add to screen
        self.add_widget(layout)
        self.add_widget(debug_area)
        
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
        
        # Start purchase
        purchase_id = self.state_machine.start_purchase(level)
        self.logger.info(f"Purchase started", purchase_id=purchase_id)
        
        # Trigger state transition
        asyncio.create_task(
            self.state_machine.handle_event(Event.PURCHASE_SELECTED)
        )
        
        # Update UI
        self.status_card.update_status(
            f"Processing Level {level}...",
            color=(1, 1, 0, 1)  # Yellow
        )
        
        # Highlight selected zone on LED
        if self.hardware.led:
            asyncio.create_task(
                self.hardware.led.set_zone_color(
                    level - 1,  # 0-indexed
                    0, 255, 0,  # Green
                    brightness=1.0
                )
            )
            
    def _update_ui(self, dt):
        """
        Update UI based on current state.
        
        Args:
            dt: Delta time from Clock
        """
        state = self.state_machine.state
        
        # Update status based on state
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
            
        elif state == State.CHECKING_PURCHASE:
            level = self.state_machine.selected_level
            self.status_card.update_status(
                f"Checking purchase for Level {level}...",
                color=(1, 1, 0, 1)
            )
            self._enable_buttons(False)
            
        elif state == State.DOOR_UNLOCKED:
            level = self.state_machine.selected_level
            self.status_card.update_status(
                f"Door unlocked! Open Level {level}",
                color=(0, 1, 0, 1)
            )
            self._enable_buttons(False)
            
        elif state == State.DOOR_OPENED:
            self.status_card.update_status(
                "Take your product and close the door",
                color=(0, 1, 0, 1)
            )
            self._enable_buttons(False)
            
        elif state == State.DOOR_ALARM:
            self.status_card.update_status(
                "⚠️ Please close the door! ⚠️",
                color=(1, 0.5, 0, 1)
            )
            self._enable_buttons(False)
            
        elif state == State.COMPLETING:
            self.status_card.update_status(
                "Thank you! Enjoy your product!",
                color=(0, 1, 0, 1)
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
