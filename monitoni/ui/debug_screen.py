"""
Debug and setup screen for hardware testing and configuration.

PIN-protected interface for operators and maintenance.
"""

import asyncio
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.expansionpanel import MDExpansionPanel, MDExpansionPanelOneLine
from kivymd.uix.slider import MDSlider

from monitoni.core.config import Config
from monitoni.core.logger import Logger
from monitoni.hardware.manager import HardwareManager


class PINDialog(MDDialog):
    """Dialog for PIN entry."""
    
    def __init__(self, on_success, **kwargs):
        """
        Initialize PIN dialog.
        
        Args:
            on_success: Callback when correct PIN entered
        """
        self.on_success = on_success
        
        # PIN text field
        self.pin_field = MDTextField(
            hint_text="Enter PIN",
            password=True,
            size_hint_x=0.8
        )
        
        super().__init__(
            title="Debug Mode Access",
            type="custom",
            content_cls=self.pin_field,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self.dismiss()
                ),
                MDRaisedButton(
                    text="ENTER",
                    on_release=self._check_pin
                )
            ],
            **kwargs
        )
        
    def _check_pin(self, instance):
        """Check if entered PIN is correct."""
        if self.pin_field.text == self.expected_pin:
            self.dismiss()
            self.on_success()
        else:
            self.pin_field.error = True
            self.pin_field.helper_text = "Incorrect PIN"
            

class DebugScreen(Screen):
    """
    Debug and setup screen.
    
    PIN-protected interface for hardware testing and configuration.
    """
    
    def __init__(
        self,
        app,
        config: Config,
        hardware: HardwareManager,
        logger: Logger,
        **kwargs
    ):
        """
        Initialize debug screen.
        
        Args:
            app: Main application instance
            config: System configuration
            hardware: Hardware manager
            logger: Logger instance
        """
        super().__init__(**kwargs)
        
        self.app = app
        self.config = config
        self.hardware = hardware
        self.logger = logger
        
        self._authenticated = False
        self._build_ui()
        
    def _build_ui(self):
        """Build the debug UI."""
        # Main layout
        layout = BoxLayout(orientation='vertical', padding="10dp", spacing="10dp")
        
        # Header with back button
        header = BoxLayout(size_hint=(1, None), height="60dp", spacing="10dp")
        
        back_btn = MDIconButton(
            icon="arrow-left",
            on_release=lambda x: self.app.switch_to_customer()
        )
        header.add_widget(back_btn)
        
        title = MDLabel(
            text="Debug & Setup",
            font_style='H5',
            size_hint=(1, None),
            height="60dp"
        )
        header.add_widget(title)
        
        layout.add_widget(header)
        
        # Scrollable content
        scroll = ScrollView()
        content = MDList()
        
        # Hardware Control Section
        content.add_widget(self._create_section_header("Hardware Control"))
        
        # Relay controls
        relay_panel = self._create_relay_panel()
        content.add_widget(relay_panel)
        
        # LED controls
        led_panel = self._create_led_panel()
        content.add_widget(led_panel)
        
        # Audio controls
        audio_panel = self._create_audio_panel()
        content.add_widget(audio_panel)
        
        # Sensor status
        sensor_panel = self._create_sensor_panel()
        content.add_widget(sensor_panel)
        
        # System Info Section
        content.add_widget(self._create_section_header("System Information"))
        
        # Statistics
        stats_panel = self._create_stats_panel()
        content.add_widget(stats_panel)
        
        # Logs
        logs_panel = self._create_logs_panel()
        content.add_widget(logs_panel)
        
        scroll.add_widget(content)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
    def _create_section_header(self, text: str):
        """Create a section header."""
        return MDLabel(
            text=text,
            font_style='H6',
            size_hint=(1, None),
            height="40dp",
            padding=("10dp", "10dp")
        )
        
    def _create_relay_panel(self):
        """Create relay control panel."""
        # Content
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        # Test all relays button
        test_btn = MDRaisedButton(
            text="Test All Relays (Cascade)",
            on_release=lambda x: asyncio.create_task(self._test_all_relays())
        )
        content.add_widget(test_btn)
        
        # Individual relay grid
        grid = GridLayout(cols=4, spacing="5dp")
        for i in range(1, 33):
            btn = MDRaisedButton(
                text=f"R{i}",
                size_hint=(None, None),
                size=("60dp", "60dp"),
                on_release=lambda x, ch=i: asyncio.create_task(self._toggle_relay(ch))
            )
            grid.add_widget(btn)
            
        content.add_widget(grid)
        
        # Create expansion panel
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="Relay Controller")
        )
        
        return panel
        
    def _create_led_panel(self):
        """Create LED control panel."""
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        # Color buttons
        colors = [
            ("Red", (255, 0, 0)),
            ("Green", (0, 255, 0)),
            ("Blue", (0, 0, 255)),
            ("White", (255, 255, 255)),
            ("Off", (0, 0, 0))
        ]
        
        for name, color in colors:
            btn = MDRaisedButton(
                text=name,
                on_release=lambda x, c=color: asyncio.create_task(
                    self.hardware.led.set_color(c[0], c[1], c[2], 0.8)
                )
            )
            content.add_widget(btn)
            
        # Brightness slider
        brightness_label = MDLabel(text="Brightness", size_hint=(1, None), height="30dp")
        content.add_widget(brightness_label)
        
        brightness_slider = MDSlider(
            min=0,
            max=1,
            value=0.8,
            on_release=lambda x: asyncio.create_task(
                self.hardware.led.set_brightness(x.value)
            )
        )
        content.add_widget(brightness_slider)
        
        # Animation buttons
        animations = ["idle", "sleep", "valid_purchase", "invalid_purchase", "door_alarm"]
        for anim in animations:
            btn = MDRaisedButton(
                text=f"Play: {anim}",
                on_release=lambda x, a=anim: asyncio.create_task(
                    self.hardware.led.play_animation(a)
                )
            )
            content.add_widget(btn)
            
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="LED Controller")
        )
        
        return panel
        
    def _create_audio_panel(self):
        """Create audio control panel."""
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        # Volume slider
        volume_label = MDLabel(text="Volume", size_hint=(1, None), height="30dp")
        content.add_widget(volume_label)
        
        volume_slider = MDSlider(
            min=0,
            max=1,
            value=0.7,
            on_release=lambda x: asyncio.create_task(
                self.hardware.audio.set_volume(x.value)
            )
        )
        content.add_widget(volume_slider)
        
        # Sound test buttons
        sounds = ["valid_purchase", "invalid_purchase", "door_alarm"]
        for sound in sounds:
            btn = MDRaisedButton(
                text=f"Play: {sound}",
                on_release=lambda x, s=sound: asyncio.create_task(
                    self.hardware.audio.play_sound(s)
                )
            )
            content.add_widget(btn)
            
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="Audio Controller")
        )
        
        return panel
        
    def _create_sensor_panel(self):
        """Create sensor status panel."""
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        self.door_status_label = MDLabel(
            text="Door: Checking...",
            size_hint=(1, None),
            height="40dp"
        )
        content.add_widget(self.door_status_label)
        
        # Update door status
        asyncio.create_task(self._update_door_status())
        
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="Sensors")
        )
        
        return panel
        
    def _create_stats_panel(self):
        """Create statistics panel."""
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        self.stats_label = MDLabel(
            text="Loading statistics...",
            size_hint=(1, None),
            height="120dp"
        )
        content.add_widget(self.stats_label)
        
        # Update statistics
        asyncio.create_task(self._update_statistics())
        
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="Statistics")
        )
        
        return panel
        
    def _create_logs_panel(self):
        """Create logs panel."""
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        
        view_logs_btn = MDRaisedButton(
            text="View Recent Logs",
            on_release=lambda x: asyncio.create_task(self._show_logs())
        )
        content.add_widget(view_logs_btn)
        
        export_logs_btn = MDRaisedButton(
            text="Export Logs to JSON",
            on_release=lambda x: asyncio.create_task(self._export_logs())
        )
        content.add_widget(export_logs_btn)
        
        panel = MDExpansionPanel(
            icon="",
            content=content,
            panel_cls=MDExpansionPanelOneLine(text="Logs")
        )
        
        return panel
        
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
            state = await self.hardware.sensor.get_door_state()
            if state is not None:
                self.door_status_label.text = f"Door: {'OPEN' if state else 'CLOSED'}"
            else:
                self.door_status_label.text = "Door: Error reading sensor"
                
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
        
        dialog = MDDialog(
            title="Recent Logs",
            text=log_text,
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
        
    def on_enter(self):
        """Called when screen is entered."""
        # Check PIN if not authenticated
        if not self._authenticated:
            self._show_pin_dialog()
            
    def _show_pin_dialog(self):
        """Show PIN entry dialog."""
        dialog = PINDialog(on_success=self._on_authenticated)
        dialog.expected_pin = self.config.telemetry.debug_pin
        dialog.open()
        
    def _on_authenticated(self):
        """Called when successfully authenticated."""
        self._authenticated = True
        self.logger.info("Debug screen authenticated")
