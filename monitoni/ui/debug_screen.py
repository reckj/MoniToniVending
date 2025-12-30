"""
Debug and setup screen for hardware testing and configuration.

PIN-protected interface for operators and maintenance.
Uses simple scrollable sections instead of expansion panels to avoid overlap issues.
"""

import asyncio
import yaml
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard

from monitoni.core.config import Config
from monitoni.core.logger import Logger
from monitoni.hardware.manager import HardwareManager

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


class LargeSlider(BoxLayout):
    """Large touch-friendly slider with label."""
    
    def __init__(
        self, 
        label_text: str, 
        min_val: float = 0, 
        max_val: float = 1, 
        default_val: float = 0.7,
        on_change=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = "100dp"
        self.spacing = "5dp"
        self.on_change_callback = on_change
        
        # Label row with value display
        label_row = BoxLayout(size_hint=(1, None), height="30dp")
        
        self.label = MDLabel(
            text=label_text,
            size_hint=(0.7, 1)
        )
        label_row.add_widget(self.label)
        
        self.value_label = MDLabel(
            text=f"{int(default_val * 100)}%",
            halign='right',
            size_hint=(0.3, 1)
        )
        label_row.add_widget(self.value_label)
        self.add_widget(label_row)
        
        # Large slider with increased touch area
        slider_container = BoxLayout(size_hint=(1, None), height="60dp", padding=("0dp", "15dp"))
        
        self.slider = Slider(
            min=min_val,
            max=max_val,
            value=default_val,
            size_hint=(1, 1),
            cursor_size=("40dp", "40dp"),
            value_track=True,
            value_track_color=(0.2, 0.6, 1, 1),
            value_track_width="8dp"
        )
        self.slider.bind(value=self._on_value_change)
        slider_container.add_widget(self.slider)
        self.add_widget(slider_container)
        
    def _on_value_change(self, instance, value):
        """Handle slider value change."""
        self.value_label.text = f"{int(value * 100)}%"
        if self.on_change_callback:
            self.on_change_callback(value)
            
    def set_value(self, value):
        """Set slider value."""
        self.slider.value = value
        self.value_label.text = f"{int(value * 100)}%"


class SectionCard(MDCard):
    """Section card with title and content."""
    
    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.padding = "15dp"
        self.spacing = "10dp"
        self.md_bg_color = (0.12, 0.12, 0.12, 1)
        self.radius = [10, 10, 10, 10]
        
        # Title
        title_label = MDLabel(
            text=title,
            font_style='H6',
            size_hint=(1, None),
            height="35dp",
            theme_text_color='Custom',
            text_color=(0.3, 0.7, 1, 1)  # Blue accent
        )
        self.add_widget(title_label)
        
        # Content container
        self.content = BoxLayout(
            orientation='vertical',
            spacing="10dp",
            size_hint_y=None
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        self.add_widget(self.content)
        
        # Bind height to content
        self.content.bind(height=self._update_height)
        
    def _update_height(self, *args):
        """Update card height based on content."""
        self.height = self.content.height + 60  # 60dp for title and padding
        
    def add_content(self, widget):
        """Add widget to content area."""
        self.content.add_widget(widget)


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
        
        # Current settings (for saving)
        self.current_volume = 0.7
        self.current_brightness = 0.8
        
        self._authenticated = False
        self._build_ui()
        
    def _build_ui(self):
        """Build the debug UI with scrollable sections."""
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding="10dp", spacing="10dp")
        
        # Header with back button
        header = BoxLayout(size_hint=(1, None), height="60dp", spacing="10dp")
        
        back_btn = MDRaisedButton(
            text="< Back",
            size_hint=(None, None),
            size=("100dp", "50dp"),
            on_release=lambda x: self.app.switch_to_customer()
        )
        header.add_widget(back_btn)
        
        title = MDLabel(
            text="Debug & Setup",
            font_style='H5',
            valign='center'
        )
        header.add_widget(title)
        
        # Save button
        save_btn = MDRaisedButton(
            text="Save",
            size_hint=(None, None),
            size=("100dp", "50dp"),
            md_bg_color=(0.2, 0.6, 0.2, 1),  # Green
            on_release=lambda x: asyncio.create_task(self._save_config())
        )
        header.add_widget(save_btn)
        
        main_layout.add_widget(header)
        
        # Scrollable content
        scroll = ScrollView(size_hint=(1, 1))
        
        content = BoxLayout(
            orientation='vertical',
            spacing="15dp",
            size_hint_y=None,
            padding=("5dp", "10dp")
        )
        content.bind(minimum_height=content.setter('height'))
        
        # Audio Section
        audio_section = self._create_audio_section()
        content.add_widget(audio_section)
        
        # LED Section
        led_section = self._create_led_section()
        content.add_widget(led_section)
        
        # LED Zone Mapping Section
        zone_section = self._create_zone_section()
        content.add_widget(zone_section)
        
        # Relay Section
        relay_section = self._create_relay_section()
        content.add_widget(relay_section)
        
        # Sensor Section
        sensor_section = self._create_sensor_section()
        content.add_widget(sensor_section)
        
        # Statistics Section
        stats_section = self._create_stats_section()
        content.add_widget(stats_section)

        # QR URL Management Section
        qr_section = self._create_qr_management_section()
        content.add_widget(qr_section)

        # Logs Section
        logs_section = self._create_logs_section()
        content.add_widget(logs_section)
        
        scroll.add_widget(content)
        main_layout.add_widget(scroll)
        
        self.add_widget(main_layout)
        
    def _create_audio_section(self):
        """Create audio control section."""
        section = SectionCard(title="Audio Control")
        
        # Volume slider
        self.volume_slider = LargeSlider(
            label_text="Volume",
            min_val=0,
            max_val=1,
            default_val=self.current_volume,
            on_change=self._on_volume_change
        )
        section.add_content(self.volume_slider)
        
        # Sound test buttons
        sounds_row = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        for sound_name, display_name in [
            ("valid_purchase", "Success"),
            ("invalid_purchase", "Error"),
            ("door_alarm", "Alarm")
        ]:
            btn = MDRaisedButton(
                text=display_name,
                size_hint=(1, 1),
                on_release=lambda x, s=sound_name: asyncio.create_task(
                    self._play_sound(s)
                )
            )
            sounds_row.add_widget(btn)
            
        section.add_content(sounds_row)
        
        return section
        
    def _create_led_section(self):
        """Create LED control section."""
        section = SectionCard(title="LED Control")
        
        # Brightness slider
        self.brightness_slider = LargeSlider(
            label_text="Brightness",
            min_val=0,
            max_val=1,
            default_val=self.current_brightness,
            on_change=self._on_brightness_change
        )
        section.add_content(self.brightness_slider)
        
        # Color buttons row 1
        colors_row1 = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        for color_name, rgb in [("Red", (255, 0, 0)), ("Green", (0, 255, 0)), ("Blue", (0, 0, 255))]:
            btn = MDRaisedButton(
                text=color_name,
                size_hint=(1, 1),
                md_bg_color=(rgb[0]/255, rgb[1]/255, rgb[2]/255, 1),
                on_release=lambda x, c=rgb: asyncio.create_task(
                    self._set_led_color(c[0], c[1], c[2])
                )
            )
            colors_row1.add_widget(btn)
            
        section.add_content(colors_row1)
        
        # Color buttons row 2
        colors_row2 = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        for color_name, rgb in [("White", (255, 255, 255)), ("Yellow", (255, 255, 0)), ("Off", (0, 0, 0))]:
            text_color = (0, 0, 0, 1) if color_name in ["White", "Yellow"] else (1, 1, 1, 1)
            btn = MDRaisedButton(
                text=color_name,
                size_hint=(1, 1),
                md_bg_color=(max(0.1, rgb[0]/255), max(0.1, rgb[1]/255), max(0.1, rgb[2]/255), 1),
                text_color=text_color,
                on_release=lambda x, c=rgb: asyncio.create_task(
                    self._set_led_color(c[0], c[1], c[2])
                )
            )
            colors_row2.add_widget(btn)
            
        section.add_content(colors_row2)
        
        # Animation buttons
        anim_row = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        for anim in ["idle", "valid_purchase", "door_alarm"]:
            display = anim.replace("_", " ").title()
            btn = MDRaisedButton(
                text=display,
                size_hint=(1, 1),
                on_release=lambda x, a=anim: asyncio.create_task(
                    self._play_animation(a)
                )
            )
            anim_row.add_widget(btn)
            
        section.add_content(anim_row)
        
        return section
        
    def _create_zone_section(self):
        """Create LED zone mapping section."""
        section = SectionCard(title="LED Zone Mapping (Pixel ranges per level)")
        
        # Total pixels info
        total_pixels = self.app_config.hardware.wled.pixel_count
        info_label = MDLabel(
            text=f"Total pixels: {total_pixels}",
            size_hint=(1, None),
            height="30dp",
            font_style='Caption'
        )
        section.add_content(info_label)
        
        # Zone configuration storage
        self.zone_inputs = {}
        
        # Get current zones from config
        try:
            current_zones = self.app_config.led.zones
        except:
            # Default zones if not configured
            current_zones = [[i * 30, (i + 1) * 30 - 1] for i in range(10)]
        
        # Create inputs for each level (5 levels per row to save space)
        for level in range(1, self.app_config.vending.levels + 1):
            zone_row = BoxLayout(size_hint=(1, None), height="45dp", spacing="8dp")
            
            # Level label
            level_label = MDLabel(
                text=f"L{level}:",
                size_hint=(None, 1),
                width="40dp",
                font_style='Body2'
            )
            zone_row.add_widget(level_label)
            
            # Start pixel input
            start_val = current_zones[level - 1][0] if level <= len(current_zones) else (level - 1) * 30
            start_input = MDTextField(
                text=str(start_val),
                hint_text="Start",
                mode="rectangle",
                size_hint=(0.25, 1),
                input_filter="int"
            )
            zone_row.add_widget(start_input)
            
            # Separator
            sep_label = MDLabel(
                text="-",
                halign='center',
                size_hint=(None, 1),
                width="20dp"
            )
            zone_row.add_widget(sep_label)
            
            # End pixel input
            end_val = current_zones[level - 1][1] if level <= len(current_zones) else level * 30 - 1
            end_input = MDTextField(
                text=str(end_val),
                hint_text="End",
                mode="rectangle",
                size_hint=(0.25, 1),
                input_filter="int"
            )
            zone_row.add_widget(end_input)
            
            # Test button - lights up this zone
            test_btn = MDRaisedButton(
                text="Test",
                size_hint=(None, 1),
                width="70dp",
                on_release=lambda x, lv=level: asyncio.create_task(self._test_zone(lv))
            )
            zone_row.add_widget(test_btn)
            
            # Store references
            self.zone_inputs[level] = {
                'start': start_input,
                'end': end_input
            }
            
            section.add_content(zone_row)
        
        # Buttons row
        buttons_row = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        # Test all zones button
        test_all_btn = MDRaisedButton(
            text="Test All Zones",
            size_hint=(1, 1),
            on_release=lambda x: asyncio.create_task(self._test_all_zones())
        )
        buttons_row.add_widget(test_all_btn)
        
        # Save zones button
        save_zones_btn = MDRaisedButton(
            text="Save Zones",
            size_hint=(1, 1),
            md_bg_color=(0.2, 0.6, 0.2, 1),  # Green
            on_release=lambda x: asyncio.create_task(self._save_zones())
        )
        buttons_row.add_widget(save_zones_btn)
        
        section.add_content(buttons_row)
        
        return section
    
    def _create_relay_section(self):
        """Create relay control section."""
        section = SectionCard(title="Relay Control")
        
        # Test all button
        test_all_btn = MDRaisedButton(
            text="Test All Relays (Cascade)",
            size_hint=(1, None),
            height="50dp",
            on_release=lambda x: run_async(self._test_all_relays())
        )
        section.add_content(test_all_btn)
        
        # Relay grid (4 columns, 8 rows)
        relay_grid = GridLayout(
            cols=4,
            spacing="8dp",
            size_hint=(1, None),
            height="360dp"
        )
        
        for i in range(1, 33):
            btn = MDRaisedButton(
                text=f"R{i}",
                size_hint=(1, None),
                height="40dp",
                font_size="14sp",
                on_release=lambda x, ch=i: run_async(self._toggle_relay(ch))
            )
            relay_grid.add_widget(btn)
            
        section.add_content(relay_grid)
        
        return section
        
    def _create_sensor_section(self):
        """Create sensor status section."""
        section = SectionCard(title="Sensors")
        
        self.door_status_label = MDLabel(
            text="Door: Checking...",
            size_hint=(1, None),
            height="40dp",
            font_style='Body1'
        )
        section.add_content(self.door_status_label)
        
        # Start door status updates
        asyncio.create_task(self._update_door_status())
        
        return section
        
    def _create_stats_section(self):
        """Create statistics section."""
        section = SectionCard(title="Statistics")
        
        self.stats_label = MDLabel(
            text="Loading statistics...",
            size_hint=(1, None),
            height="100dp",
            font_style='Body1'
        )
        section.add_content(self.stats_label)
        
        # Update statistics
        asyncio.create_task(self._update_statistics())
        
        return section

    def _create_qr_management_section(self):
        """Create QR URL management section."""
        section = SectionCard(title="QR Code URL Management")

        # Current base URL display
        self.qr_base_url_label = MDLabel(
            text=f"Base URL: {self.config.vending.qr_urls.base_url}",
            size_hint=(1, None),
            height="40dp",
            font_style='Body2'
        )
        section.add_content(self.qr_base_url_label)

        # Buttons row
        buttons_row = BoxLayout(size_hint=(1, None), height="60dp", spacing="10dp")

        # Load from file button
        load_file_btn = MDRaisedButton(
            text="Load from USB",
            size_hint=(0.5, 1),
            font_size="16sp",
            md_bg_color=(0.2, 0.6, 0.8, 1),
            on_release=lambda x: self._show_file_chooser()
        )
        buttons_row.add_widget(load_file_btn)

        # Refresh/reload config button
        refresh_btn = MDRaisedButton(
            text="Reload Config",
            size_hint=(0.5, 1),
            font_size="16sp",
            md_bg_color=(0.4, 0.6, 0.4, 1),
            on_release=lambda x: self._reload_qr_config()
        )
        buttons_row.add_widget(refresh_btn)

        section.add_content(buttons_row)

        # Info label
        info_label = MDLabel(
            text="Load QR URLs from JSON/YAML file on USB stick.\nExpected format: {\"base_url\": \"...\", \"level_urls\": {\"1\": \"...\", ...}}",
            size_hint=(1, None),
            height="60dp",
            font_style='Caption',
            theme_text_color='Secondary'
        )
        section.add_content(info_label)

        return section

    def _show_file_chooser(self):
        """Show file chooser dialog for QR URL file selection."""
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.popup import Popup

        # Create file chooser
        file_chooser = FileChooserListView(
            path="/media",  # Common mount point for USB sticks
            filters=['*.json', '*.yaml', '*.yml']
        )

        # Create popup
        popup_content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        popup_content.add_widget(file_chooser)

        # Buttons
        btn_row = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")

        def on_load():
            if file_chooser.selection:
                selected_file = file_chooser.selection[0]
                popup.dismiss()
                self._load_qr_urls_from_file(selected_file)

        load_btn = MDRaisedButton(
            text="Load",
            size_hint=(0.5, 1),
            on_release=lambda x: on_load()
        )
        btn_row.add_widget(load_btn)

        cancel_btn = MDRaisedButton(
            text="Cancel",
            size_hint=(0.5, 1),
            md_bg_color=(0.5, 0.5, 0.5, 1),
            on_release=lambda x: popup.dismiss()
        )
        btn_row.add_widget(cancel_btn)

        popup_content.add_widget(btn_row)

        # Create and open popup
        popup = Popup(
            title="Select QR URL Configuration File",
            content=popup_content,
            size_hint=(0.9, 0.9)
        )
        popup.open()

    def _load_qr_urls_from_file(self, file_path: str):
        """Load QR URLs from selected file."""
        try:
            from monitoni.core.config import get_config_manager
            from pathlib import Path

            config_manager = get_config_manager()
            if config_manager:
                # Load QR URLs from file
                success = config_manager.update_qr_urls_from_file(Path(file_path))

                if success:
                    self._show_message_dialog(
                        "Success",
                        f"QR URLs loaded successfully from:\n{file_path}\n\nQR codes will be regenerated on next use.",
                        success=True
                    )
                    # Update display
                    self.qr_base_url_label.text = f"Base URL: {self.config.vending.qr_urls.base_url}"
            else:
                self._show_message_dialog(
                    "Error",
                    "Config manager not available",
                    success=False
                )

        except FileNotFoundError:
            self._show_message_dialog(
                "Error",
                f"File not found:\n{file_path}",
                success=False
            )
        except ValueError as e:
            self._show_message_dialog(
                "Error",
                f"Invalid file format:\n{str(e)}",
                success=False
            )
        except Exception as e:
            self._show_message_dialog(
                "Error",
                f"Failed to load QR URLs:\n{str(e)}",
                success=False
            )

    def _reload_qr_config(self):
        """Reload QR configuration from config file."""
        try:
            from monitoni.core.config import get_config_manager

            config_manager = get_config_manager()
            if config_manager:
                config_manager.load()
                self.qr_base_url_label.text = f"Base URL: {self.config.vending.qr_urls.base_url}"
                self._show_message_dialog(
                    "Success",
                    "QR URL configuration reloaded",
                    success=True
                )
            else:
                self._show_message_dialog(
                    "Error",
                    "Config manager not available",
                    success=False
                )
        except Exception as e:
            self._show_message_dialog(
                "Error",
                f"Failed to reload config:\n{str(e)}",
                success=False
            )

    def _show_message_dialog(self, title: str, message: str, success: bool = True):
        """Show a message dialog."""
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()

    def _create_logs_section(self):
        """Create logs section."""
        section = SectionCard(title="Logs")
        
        buttons_row = BoxLayout(size_hint=(1, None), height="50dp", spacing="10dp")
        
        view_logs_btn = MDRaisedButton(
            text="View Recent Logs",
            size_hint=(1, 1),
            on_release=lambda x: asyncio.create_task(self._show_logs())
        )
        buttons_row.add_widget(view_logs_btn)
        
        export_logs_btn = MDRaisedButton(
            text="Export Logs",
            size_hint=(1, 1),
            on_release=lambda x: asyncio.create_task(self._export_logs())
        )
        buttons_row.add_widget(export_logs_btn)
        
        section.add_content(buttons_row)
        
        return section
        
    # ===== Callback Methods =====
    
    def _on_volume_change(self, value):
        """Handle volume slider change."""
        self.current_volume = value
        if self.hardware.audio:
            asyncio.create_task(self.hardware.audio.set_volume(value))
            
    def _on_brightness_change(self, value):
        """Handle brightness slider change."""
        self.current_brightness = value
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.set_brightness(value))
            
    async def _play_sound(self, sound_name: str):
        """Play a sound."""
        if self.hardware.audio:
            await self.hardware.audio.play_sound(sound_name)
            
    async def _set_led_color(self, r: int, g: int, b: int):
        """Set LED color."""
        if self.hardware.led:
            await self.hardware.led.set_color(r, g, b, self.current_brightness)
            
    async def _play_animation(self, animation: str):
        """Play LED animation."""
        if self.hardware.led:
            await self.hardware.led.play_animation(animation)
            
    async def _test_all_relays(self):
        """Test all relays in sequence."""
        if not self.hardware.relay:
            return
            
        self.logger.info("Testing all relays")
        
        for i in range(1, 33):
            await self.hardware.relay.set_relay(i, True)
            await asyncio.sleep(0.1)
            await self.hardware.relay.set_relay(i, False)
            
        self.logger.info("Relay test complete")
        
    async def _toggle_relay(self, channel: int):
        """Toggle a specific relay."""
        if not self.hardware.relay:
            return
            
        current = await self.hardware.relay.get_relay(channel)
        await self.hardware.relay.set_relay(channel, not current)
        
    async def _update_door_status(self):
        """Update door sensor status."""
        if not self.hardware.sensor:
            self.door_status_label.text = "Door: Sensor not available"
            return
            
        while True:
            try:
                state = await self.hardware.sensor.get_door_state()
                if state is not None:
                    status = "OPEN" if state else "CLOSED"
                    color = "(1, 0.5, 0, 1)" if state else "(0, 1, 0, 1)"
                    self.door_status_label.text = f"Door: {status}"
                else:
                    self.door_status_label.text = "Door: Error reading sensor"
            except Exception as e:
                self.door_status_label.text = f"Door: Error - {e}"
                
            await asyncio.sleep(1.0)
            
    async def _update_statistics(self):
        """Update statistics display."""
        from monitoni.core.database import get_database
        
        db = await get_database()
        stats = await db.get_statistics()
        
        text = f"""Completed Purchases: {stats['completed_purchases']}
Failed Purchases: {stats['failed_purchases']}
Network Incidents: {stats['network_incidents']}
Server Incidents: {stats['server_incidents']}"""
        
        self.stats_label.text = text
        
    async def _show_logs(self):
        """Show recent logs."""
        from monitoni.core.database import get_database
        
        db = await get_database()
        logs = await db.get_logs(limit=20)
        
        # Create dialog with logs
        log_text = "\n".join([
            f"[{log['level']}] {log['message']}"
            for log in logs
        ])
        
        if not log_text:
            log_text = "No logs available"
        
        dialog = MDDialog(
            title="Recent Logs",
            text=log_text[:2000],  # Limit text length
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
        
    async def _export_logs(self):
        """Export logs to JSON file."""
        from monitoni.core.database import get_database
        from datetime import datetime
        
        db = await get_database()
        filename = f"logs/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        await db.export_logs_to_json(filename)
        
        self.logger.info(f"Logs exported to {filename}")
        
        # Show confirmation
        dialog = MDDialog(
            title="Export Complete",
            text=f"Logs exported to:\n{filename}",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
        
    async def _test_zone(self, level: int):
        """Test a specific zone by lighting it up."""
        if not self.hardware.led:
            return
            
        # Get zone range from inputs
        try:
            start = int(self.zone_inputs[level]['start'].text)
            end = int(self.zone_inputs[level]['end'].text)
        except (ValueError, KeyError):
            self.logger.warning(f"Invalid zone values for level {level}")
            return
            
        self.logger.info(f"Testing zone {level}: pixels {start}-{end}")
        
        # Turn off all LEDs first
        await self.hardware.led.turn_off()
        await asyncio.sleep(0.1)
        
        # Light up just this zone in green
        await self.hardware.led.set_zone_pixels(start, end, 0, 255, 0, self.current_brightness)
        
        # Turn off after 2 seconds
        await asyncio.sleep(2.0)
        await self.hardware.led.turn_off()
        
    async def _test_all_zones(self):
        """Test all zones sequentially."""
        if not self.hardware.led:
            return
            
        self.logger.info("Testing all zones")
        
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
            (0, 255, 128),  # Spring
            (255, 255, 255) # White
        ]
        
        for level in range(1, self.app_config.vending.levels + 1):
            try:
                start = int(self.zone_inputs[level]['start'].text)
                end = int(self.zone_inputs[level]['end'].text)
            except (ValueError, KeyError):
                continue
                
            # Turn off all first
            await self.hardware.led.turn_off()
            await asyncio.sleep(0.05)
            
            # Light up this zone with a unique color
            color = colors[(level - 1) % len(colors)]
            await self.hardware.led.set_zone_pixels(start, end, color[0], color[1], color[2], self.current_brightness)
            await asyncio.sleep(0.5)
            
        # Turn off after test
        await asyncio.sleep(1.0)
        await self.hardware.led.turn_off()
        self.logger.info("Zone test complete")
        
    async def _save_zones(self):
        """Save zone configuration to local config."""
        local_config_path = Path("config/local.yaml")
        
        # Load existing local config or create new
        if local_config_path.exists():
            with open(local_config_path, 'r') as f:
                local_config = yaml.safe_load(f) or {}
        else:
            local_config = {}
            
        # Build zones list
        zones = []
        for level in range(1, self.app_config.vending.levels + 1):
            try:
                start = int(self.zone_inputs[level]['start'].text)
                end = int(self.zone_inputs[level]['end'].text)
                zones.append([start, end])
            except (ValueError, KeyError) as e:
                self.logger.error(f"Invalid zone for level {level}: {e}")
                # Show error dialog
                dialog = MDDialog(
                    title="Error",
                    text=f"Invalid values for Level {level}. Please enter valid numbers.",
                    buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
                )
                dialog.open()
                return
                
        # Update config
        if 'led' not in local_config:
            local_config['led'] = {}
        local_config['led']['zones'] = zones
        
        # Save config
        with open(local_config_path, 'w') as f:
            yaml.dump(local_config, f, default_flow_style=False)
            
        self.logger.info(f"Zone configuration saved to {local_config_path}")
        
        # Show confirmation
        zones_text = "\n".join([f"L{i+1}: {z[0]}-{z[1]}" for i, z in enumerate(zones)])
        dialog = MDDialog(
            title="Zones Saved",
            text=f"Zone configuration saved:\n{zones_text}",
            buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()
        
    async def _save_config(self):
        """Save current settings to local config file."""
        local_config_path = Path("config/local.yaml")
        
        # Load existing local config or create new
        if local_config_path.exists():
            with open(local_config_path, 'r') as f:
                local_config = yaml.safe_load(f) or {}
        else:
            local_config = {}
            
        # Update audio settings
        if 'audio' not in local_config:
            local_config['audio'] = {}
        local_config['audio']['default_volume'] = round(self.current_volume, 2)
        
        # Update LED settings
        if 'hardware' not in local_config:
            local_config['hardware'] = {}
        if 'wled' not in local_config['hardware']:
            local_config['hardware']['wled'] = {}
        local_config['hardware']['wled']['default_brightness'] = round(self.current_brightness, 2)
        
        # Save config
        with open(local_config_path, 'w') as f:
            yaml.dump(local_config, f, default_flow_style=False)
            
        self.logger.info(f"Configuration saved to {local_config_path}")
        
        # Show confirmation
        dialog = MDDialog(
            title="Settings Saved",
            text=f"Volume: {int(self.current_volume * 100)}%\nBrightness: {int(self.current_brightness * 100)}%",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
        
    def on_enter(self):
        """Called when screen is entered."""
        # Always require PIN when entering debug screen
        self._authenticated = False
        self._show_pin_dialog()
            
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
