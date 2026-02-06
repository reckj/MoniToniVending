"""
Debug and setup screen for hardware testing and configuration.

PIN-protected interface for operators and maintenance.
Uses nested ScreenManager for sub-screen navigation.
"""

import asyncio
from pathlib import Path
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog

from monitoni.core.config import Config, get_config_manager
from monitoni.core.logger import Logger
from monitoni.hardware.manager import HardwareManager
from monitoni.ui.debug_screens import (
    BaseDebugSubScreen,
    DebugMenuScreen,
    RelaySettingsScreen,
    MotorSettingsScreen,
    LEDSettingsScreen,
    SensorSettingsScreen,
    AudioSettingsScreen,
    NetworkSettingsScreen,
    StatsSettingsScreen,
    QRManagementScreen,
    MaintenanceScreen,
)

# Register icon font
from monitoni.ui.icons import register_icon_font, get_icon
register_icon_font()


def run_async(coro):
    """Run an async coroutine from a sync context (e.g., Kivy callback).
    
    This is needed because Kivy's event loop doesn't integrate with asyncio by default.
    """
    import threading
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()


class PINKeypad(BoxLayout):
    """Numeric keypad for PIN entry."""
    
    def __init__(self, on_digit, on_clear, on_backspace, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = "10dp"
        self.size_hint = (1, None)
        self.height = "320dp"
        
        self.on_digit = on_digit
        self.on_clear = on_clear
        self.on_backspace = on_backspace
        
        # Number pad layout (3x4 grid)
        button_height = "70dp"
        
        # Row 1: 1 2 3
        row1 = BoxLayout(spacing="10dp", size_hint=(1, None), height=button_height)
        for digit in ["1", "2", "3"]:
            btn = MDRaisedButton(
                text=digit,
                size_hint=(1, 1),
                font_size="28sp",
                on_release=lambda x, d=digit: self.on_digit(d)
            )
            row1.add_widget(btn)
        self.add_widget(row1)
        
        # Row 2: 4 5 6
        row2 = BoxLayout(spacing="10dp", size_hint=(1, None), height=button_height)
        for digit in ["4", "5", "6"]:
            btn = MDRaisedButton(
                text=digit,
                size_hint=(1, 1),
                font_size="28sp",
                on_release=lambda x, d=digit: self.on_digit(d)
            )
            row2.add_widget(btn)
        self.add_widget(row2)
        
        # Row 3: 7 8 9
        row3 = BoxLayout(spacing="10dp", size_hint=(1, None), height=button_height)
        for digit in ["7", "8", "9"]:
            btn = MDRaisedButton(
                text=digit,
                size_hint=(1, 1),
                font_size="28sp",
                on_release=lambda x, d=digit: self.on_digit(d)
            )
            row3.add_widget(btn)
        self.add_widget(row3)
        
        # Row 4: Clear 0 Backspace
        row4 = BoxLayout(spacing="10dp", size_hint=(1, None), height=button_height)
        
        clear_btn = MDRaisedButton(
            text="C",
            size_hint=(1, 1),
            font_size="24sp",
            md_bg_color=(0.6, 0.3, 0.3, 1),  # Red-ish
            on_release=lambda x: self.on_clear()
        )
        row4.add_widget(clear_btn)
        
        zero_btn = MDRaisedButton(
            text="0",
            size_hint=(1, 1),
            font_size="28sp",
            on_release=lambda x: self.on_digit("0")
        )
        row4.add_widget(zero_btn)
        
        backspace_btn = MDRaisedButton(
            text="<",
            size_hint=(1, 1),
            font_size="28sp",
            md_bg_color=(0.4, 0.4, 0.4, 1),
            on_release=lambda x: self.on_backspace()
        )
        row4.add_widget(backspace_btn)
        
        self.add_widget(row4)


class PINDialogContent(BoxLayout):
    """Content for PIN dialog with display and keypad."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = "15dp"
        self.size_hint_y = None
        self.height = "420dp"
        
        self.pin_value = ""
        
        # PIN display (shows dots for entered digits)
        self.display = MDLabel(
            text="_ _ _ _",
            halign='center',
            font_style='H4',
            size_hint=(1, None),
            height="60dp",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1)
        )
        self.add_widget(self.display)
        
        # Error label (hidden initially)
        self.error_label = MDLabel(
            text="",
            halign='center',
            font_style='Body2',
            size_hint=(1, None),
            height="30dp",
            theme_text_color='Custom',
            text_color=(1, 0.3, 0.3, 1)  # Red
        )
        self.add_widget(self.error_label)
        
        # Keypad
        self.keypad = PINKeypad(
            on_digit=self._on_digit,
            on_clear=self._on_clear,
            on_backspace=self._on_backspace
        )
        self.add_widget(self.keypad)
        
    def _on_digit(self, digit: str):
        """Handle digit press."""
        if len(self.pin_value) < 8:  # Max 8 digits
            self.pin_value += digit
            self._update_display()
            self.error_label.text = ""
            
    def _on_clear(self):
        """Handle clear press."""
        self.pin_value = ""
        self._update_display()
        self.error_label.text = ""
        
    def _on_backspace(self):
        """Handle backspace press."""
        if self.pin_value:
            self.pin_value = self.pin_value[:-1]
            self._update_display()
            self.error_label.text = ""
            
    def _update_display(self):
        """Update the PIN display."""
        if self.pin_value:
            # Show filled circles for entered digits
            dots = "  ".join(["O"] * len(self.pin_value))
            # Add dashes for remaining digits (assuming 4-digit PIN)
            remaining = 4 - len(self.pin_value)
            if remaining > 0:
                dots += "  " + "  ".join(["-"] * remaining)
            self.display.text = dots
        else:
            self.display.text = "_ _ _ _"
            
    def show_error(self, message: str):
        """Show error message."""
        self.error_label.text = message
        self.pin_value = ""
        self._update_display()
        
    def get_pin(self) -> str:
        """Get entered PIN."""
        return self.pin_value


class PINDialog(MDDialog):
    """Dialog for PIN entry with onscreen keypad."""
    
    def __init__(self, on_success, on_cancel=None, **kwargs):
        """
        Initialize PIN dialog.
        
        Args:
            on_success: Callback when correct PIN entered
            on_cancel: Callback when dialog is cancelled
        """
        self.on_success = on_success
        self.on_cancel_callback = on_cancel
        self.expected_pin = "1234"
        
        # Create keypad content
        self.content = PINDialogContent()
        
        super().__init__(
            title="Enter PIN",
            type="custom",
            content_cls=self.content,
            auto_dismiss=False,  # Prevent closing by clicking outside
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self._on_cancel
                ),
                MDRaisedButton(
                    text="ENTER",
                    md_bg_color=(0.2, 0.6, 0.2, 1),
                    on_release=self._check_pin
                )
            ],
            **kwargs
        )
        
    def _on_cancel(self, instance):
        """Handle cancel button press."""
        self.dismiss()
        if self.on_cancel_callback:
            self.on_cancel_callback()
        
    def _check_pin(self, instance):
        """Check if entered PIN is correct."""
        entered_pin = self.content.get_pin()
        if entered_pin == self.expected_pin:
            self.dismiss()
            self.on_success()
        else:
            self.content.show_error("Incorrect PIN")


class DebugScreen(Screen):
    """
    Debug and setup screen.
    
    PIN-protected interface for hardware testing and configuration.
    """
    
    def __init__(
        self,
        app,
        app_config: Config,
        hardware: HardwareManager,
        logger: Logger,
        **kwargs
    ):
        """
        Initialize debug screen.
        
        Args:
            app: Main application instance
            app_config: System configuration
            hardware: Hardware manager
            logger: Logger instance
        """
        super().__init__(**kwargs)
        
        self.app = app
        self.app_config = app_config
        self.hardware = hardware
        self.logger = logger

        self._authenticated = False
        self._build_ui()
        
    def _build_ui(self):
        """Build the debug UI with nested ScreenManager for sub-screen navigation."""
        # Create nested ScreenManager with NoTransition to avoid touch-handling bugs
        self.sub_screen_manager = ScreenManager(
            transition=NoTransition()
        )

        # Create and add menu screen
        menu_screen = DebugMenuScreen(
            name='menu',
            navigate_callback=self.navigate_to,
            back_to_customer_callback=self.app.switch_to_customer
        )
        self.sub_screen_manager.add_widget(menu_screen)

        # Create real sub-screens for each category
        config_manager = get_config_manager()

        sub_screen_classes = {
            'relay': (RelaySettingsScreen, "Relay-Steuerung"),
            'motor': (MotorSettingsScreen, "Motor-Einstellungen"),
            'led': (LEDSettingsScreen, "LED-Steuerung"),
            'sensor': (SensorSettingsScreen, "Sensoren"),
            'audio': (AudioSettingsScreen, "Audio"),
            'network': (NetworkSettingsScreen, "Netzwerk"),
            'stats': (StatsSettingsScreen, "Statistik & Logs"),
            'qr_management': (QRManagementScreen, "QR Codes"),
            'maintenance': (MaintenanceScreen, "Maintenance & Status"),
        }

        for screen_name, (screen_class, title) in sub_screen_classes.items():
            sub_screen = screen_class(
                name=screen_name,
                hardware=self.hardware,
                config_manager=config_manager,
                navigate_back=self.navigate_back,
            )
            self.sub_screen_manager.add_widget(sub_screen)

        # Set menu as default screen
        self.sub_screen_manager.current = 'menu'

        # Add ScreenManager to this screen
        self.add_widget(self.sub_screen_manager)

    def navigate_to(self, screen_name: str):
        """Navigate to a sub-screen."""
        self.sub_screen_manager.current = screen_name

    def navigate_back(self):
        """Return to menu."""
        self.sub_screen_manager.current = 'menu'

    def on_enter(self):
        """Called when screen is entered - show PIN if not yet authenticated."""
        if not self._authenticated:
            self._show_pin_dialog()

    def on_leave(self):
        """Called when leaving debug screen - reset authentication."""
        self._authenticated = False
            
    def _show_pin_dialog(self):
        """Show PIN entry dialog."""
        dialog = PINDialog(
            on_success=self._on_authenticated,
            on_cancel=self._on_pin_cancelled
        )
        dialog.expected_pin = self.app_config.telemetry.debug_pin
        dialog.open()
        
    def _on_authenticated(self):
        """Called when successfully authenticated."""
        self._authenticated = True
        self.logger.info("Debug screen authenticated")
        
    def _on_pin_cancelled(self):
        """Called when PIN entry is cancelled - return to customer screen."""
        self.logger.info("PIN entry cancelled, returning to main screen")
        self.app.switch_to_customer()
