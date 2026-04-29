"""
LED configuration and testing screen.

Provides controls for:
- WLED connection settings (pixel count, IP, FPS)
- Brightness adjustment
- Color testing (preset colors + custom color picker)
- Zone mapping configuration and testing
- Animation previews
- Live LED status display
- Reset to factory defaults
"""

import asyncio
from typing import Optional
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    NumpadField,
    LiveStatusCard,
    update_config_value,
    reset_section_to_defaults,
    show_confirm_dialog,
    CORAL_ACCENT,
    NEAR_BLACK,
    INPUT_BUTTON,
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class LEDSettingsScreen(BaseDebugSubScreen):
    """
    LED configuration and testing screen.

    Allows operators to:
    - Configure WLED connection parameters
    - Test LED colors and brightness
    - Map LED zones to product levels
    - Preview animations
    - Monitor LED controller status
    """

    def __init__(
        self,
        hardware: HardwareManager,
        config_manager: ConfigManager,
        navigate_back: Optional[callable] = None,
        **kwargs
    ):
        """
        Initialize LED settings screen.

        Args:
            hardware: Hardware manager instance
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional arguments for BaseDebugSubScreen
        """
        self.hardware = hardware
        self.config_manager = config_manager

        # Track active zone test tasks for cleanup
        self._zone_test_tasks = []

        super().__init__(navigate_back=navigate_back, **kwargs)
        self.title = "LED Control"

        self._build_content()

    def _build_content(self):
        """Build the LED settings screen content."""
        # Card 1: WLED Connection & Brightness
        brightness_card = SettingsCard(title="WLED Connection & Brightness")

        # Pixel count
        pixel_count_field = NumpadField(
            label="Pixel Count",
            config_path="hardware.wled.pixel_count",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=1000
        )
        brightness_card.add_content(pixel_count_field)

        # IP Address - use a button that opens a text input dialog
        ip_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )
        ip_label = MDLabel(
            text="IP Address",
            size_hint_x=0.6,
            font_style='Body1'
        )
        ip_row.add_widget(ip_label)

        current_ip = self.config_manager.config.hardware.wled.ip_address
        self.ip_button = MDRaisedButton(
            text=current_ip,
            size_hint_x=0.4,
            md_bg_color=INPUT_BUTTON,
            on_release=lambda x: self._open_ip_dialog()
        )
        ip_row.add_widget(self.ip_button)
        brightness_card.add_content(ip_row)

        # Brightness control with slider
        brightness_row = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height="80dp",
            spacing="5dp"
        )

        # Label + value display
        brightness_header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="30dp"
        )
        brightness_label = MDLabel(
            text="Brightness",
            size_hint_x=0.6,
            font_style='Body1'
        )
        brightness_header.add_widget(brightness_label)

        try:
            current_brightness = self.config_manager.config.led.animations.get('idle', {}).get('brightness', 0.8)
        except:
            current_brightness = 0.8
        brightness_pct = min(100, int(current_brightness * 100))

        self.brightness_value_label = MDLabel(
            text=f"{brightness_pct}%",
            size_hint_x=0.4,
            font_style='Body1',
            halign='right'
        )
        brightness_header.add_widget(self.brightness_value_label)
        brightness_row.add_widget(brightness_header)

        # Slider (0-100)
        brightness_slider = Slider(
            min=0,
            max=100,
            value=brightness_pct,
            step=1,
            size_hint_y=None,
            height="40dp"
        )
        brightness_slider.bind(value=self._on_brightness_slider_changed)
        brightness_row.add_widget(brightness_slider)

        brightness_card.add_content(brightness_row)

        self.add_content(brightness_card)

        # Card 2: Color Test
        color_card = SettingsCard(title="Color Test")

        # Row 1: Red, Green, Blue
        color_row1 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        for color_name, rgb in [("Red", (255, 0, 0)), ("Green", (0, 255, 0)), ("Blue", (0, 0, 255))]:
            btn = MDRaisedButton(
                text=color_name,
                size_hint=(1, 1),
                md_bg_color=(rgb[0]/255, rgb[1]/255, rgb[2]/255, 1),
                on_release=lambda x, r=rgb[0], g=rgb[1], b=rgb[2]: self._set_color(r, g, b)
            )
            color_row1.add_widget(btn)

        color_card.add_content(color_row1)

        # Row 2: White, Yellow, Off
        color_row2 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        for color_name, rgb, text_color in [
            ("White", (255, 255, 255), (0, 0, 0, 1)),
            ("Yellow", (255, 255, 0), (0, 0, 0, 1)),
            ("Off", (0, 0, 0), (1, 1, 1, 1))
        ]:
            btn = MDRaisedButton(
                text=color_name,
                size_hint=(1, 1),
                md_bg_color=(max(0.1, rgb[0]/255), max(0.1, rgb[1]/255), max(0.1, rgb[2]/255), 1),
                text_color=text_color,
                on_release=lambda x, r=rgb[0], g=rgb[1], b=rgb[2]: self._set_color(r, g, b)
            )
            color_row2.add_widget(btn)

        color_card.add_content(color_row2)

        # Row 3: Magenta, Cyan, Orange
        color_row3 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        for color_name, rgb, text_color in [
            ("Magenta", (255, 0, 255), (1, 1, 1, 1)),
            ("Cyan", (0, 255, 255), (0, 0, 0, 1)),
            ("Orange", (255, 128, 0), (0, 0, 0, 1))
        ]:
            btn = MDRaisedButton(
                text=color_name,
                size_hint=(1, 1),
                md_bg_color=(rgb[0]/255, rgb[1]/255, rgb[2]/255, 1),
                text_color=text_color,
                on_release=lambda x, r=rgb[0], g=rgb[1], b=rgb[2]: self._set_color(r, g, b)
            )
            color_row3.add_widget(btn)

        color_card.add_content(color_row3)

        self.add_content(color_card)

        # Card 3: Zone Mapping
        zone_card = SettingsCard(title="Zone Mapping")

        # Info label
        pixel_count = self.config_manager.config.hardware.wled.pixel_count
        info_label = MDLabel(
            text=f"Total pixels: {pixel_count}",
            size_hint_y=None,
            height="30dp",
            font_style='Caption'
        )
        zone_card.add_content(info_label)

        # Zone inputs storage
        self.zone_inputs = {}

        # Get current zones from config
        zones = self.config_manager.config.led.zones
        levels = self.config_manager.config.vending.levels

        # Create inputs for each level
        for level in range(1, levels + 1):
            zone_row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height="50dp",
                spacing="10dp"
            )

            # Level label
            level_label = MDLabel(
                text=f"Level {level}:",
                size_hint_x=0.25,
                font_style='Body2'
            )
            zone_row.add_widget(level_label)

            # Start pixel
            start_val = zones[level - 1][0] if level <= len(zones) else (level - 1) * 30
            start_field = NumpadField(
                label="",
                config_path=f"led.zones.{level-1}.0",  # zones[index][0]
                config_manager=self.config_manager,
                allow_decimal=False,
                min_value=0,
                max_value=pixel_count - 1
            )
            start_field.size_hint_x = 0.25
            zone_row.add_widget(start_field)

            # Separator
            sep_label = MDLabel(
                text="-",
                halign='center',
                size_hint_x=0.05
            )
            zone_row.add_widget(sep_label)

            # End pixel
            end_val = zones[level - 1][1] if level <= len(zones) else level * 30 - 1
            end_field = NumpadField(
                label="",
                config_path=f"led.zones.{level-1}.1",  # zones[index][1]
                config_manager=self.config_manager,
                allow_decimal=False,
                min_value=0,
                max_value=pixel_count - 1
            )
            end_field.size_hint_x = 0.25
            zone_row.add_widget(end_field)

            # Test button
            test_btn = MDRaisedButton(
                text="Test",
                size_hint_x=0.2,
                on_release=lambda x, lv=level: self._test_zone(lv)
            )
            zone_row.add_widget(test_btn)

            # Store references for zone testing
            self.zone_inputs[level] = {
                'start': start_field,
                'end': end_field
            }

            zone_card.add_content(zone_row)

        # Test all zones button
        test_all_btn = MDRaisedButton(
            text="Test All Zones",
            size_hint_y=None,
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._test_all_zones()
        )
        zone_card.add_content(test_all_btn)

        self.add_content(zone_card)

        # Card 4: Animations
        animation_card = SettingsCard(title="Animations")

        # Animation buttons (3 per row)
        animations = [
            ("idle", "Idle"),
            ("sleep", "Sleep"),
            ("valid_purchase", "Valid Purchase"),
            ("invalid_purchase", "Invalid Purchase"),
            ("door_alarm", "Door Alarm"),
            ("offline", "Offline"),
            ("level_highlight", "Level Highlight"),
        ]

        # Create rows of 3 buttons each
        for i in range(0, len(animations), 3):
            anim_row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height="60dp",
                spacing="10dp"
            )

            for j in range(3):
                if i + j < len(animations):
                    anim_name, display_name = animations[i + j]
                    btn = MDRaisedButton(
                        text=display_name,
                        size_hint=(1, 1),
                        on_release=lambda x, a=anim_name: self._play_animation(a)
                    )
                    anim_row.add_widget(btn)
                else:
                    # Empty placeholder
                    anim_row.add_widget(BoxLayout())

            animation_card.add_content(anim_row)

        # All off button
        all_off_btn = MDRaisedButton(
            text="All Off",
            size_hint_y=None,
            height="60dp",
            md_bg_color=(0.3, 0.3, 0.3, 1),
            on_release=lambda x: self._turn_off_leds()
        )
        animation_card.add_content(all_off_btn)

        self.add_content(animation_card)

        # Card 5: Live Status
        status_card = LiveStatusCard(
            title="LED Status",
            get_status_callback=self._get_led_status,
            update_interval=2.0
        )
        status_card.height = "150dp"
        self.add_content(status_card)

        # Reset button
        reset_btn = MDRaisedButton(
            text="Factory Reset",
            size_hint_y=None,
            height="60dp",
            md_bg_color=(0.6, 0.3, 0.3, 1),
            on_release=lambda x: self._reset_to_defaults()
        )
        self.add_content(reset_btn)

    def _open_ip_dialog(self):
        """Open dialog for IP address input."""
        from kivymd.uix.textfield import MDTextField

        # Content with text field
        content = BoxLayout(
            orientation='vertical',
            spacing="10dp",
            size_hint_y=None,
            height="100dp"
        )

        ip_field = MDTextField(
            text=self.config_manager.config.hardware.wled.ip_address,
            hint_text="192.168.1.100",
            mode="rectangle"
        )
        content.add_widget(ip_field)

        def on_save(instance):
            new_ip = ip_field.text.strip()
            if new_ip:
                # Update config
                update_config_value(
                    self.config_manager,
                    "hardware.wled.ip_address",
                    new_ip
                )
                # Update button text
                self.ip_button.text = new_ip
            dialog.dismiss()

        dialog = MDDialog(
            title="Enter IP Address",
            type="custom",
            content_cls=content,
            buttons=[
                MDRaisedButton(
                    text="CANCEL",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="SAVE",
                    md_bg_color=CORAL_ACCENT,
                    on_release=on_save
                ),
            ],
        )
        dialog.open()

    def _on_brightness_slider_changed(self, instance, value):
        """Handle brightness slider change."""
        pct = int(value)
        self.brightness_value_label.text = f"{pct}%"
        brightness = pct / 100.0

        # Save to config
        update_config_value(
            self.config_manager,
            "led.animations.idle.brightness",
            brightness
        )

        # Apply to hardware immediately
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.set_brightness(brightness))

    def _set_color(self, r: int, g: int, b: int):
        """Set LED color."""
        if self.hardware.led:
            # Get current brightness
            try:
                brightness = self.config_manager.config.led.animations.get('idle', {}).get('brightness', 0.8)
            except:
                brightness = 0.8

            asyncio.create_task(self.hardware.led.set_color(r, g, b, brightness))

    def _test_zone(self, level: int):
        """Test a specific zone by lighting it up in green for 2 seconds."""
        async def test_zone_async():
            if not self.hardware.led:
                return

            # Get zone range from current config
            try:
                zones = self.config_manager.config.led.zones
                start, end = zones[level - 1]
            except (IndexError, KeyError):
                print(f"Invalid zone for level {level}")
                return

            # Get current brightness
            try:
                brightness = self.config_manager.config.led.animations.get('idle', {}).get('brightness', 0.8)
            except:
                brightness = 0.8

            # Turn off all LEDs first
            await self.hardware.led.turn_off()
            await asyncio.sleep(0.1)

            # Light up this zone in green
            await self.hardware.led.set_zone_pixels(start, end, 0, 255, 0, brightness)

            # Turn off after 2 seconds
            await asyncio.sleep(2.0)
            await self.hardware.led.turn_off()

        # Track task for cleanup
        task = asyncio.create_task(test_zone_async())
        self._zone_test_tasks.append(task)

    def _test_all_zones(self):
        """Test all zones sequentially with different colors."""
        async def test_all_zones_async():
            if not self.hardware.led:
                return

            # Colors for each zone
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

            # Get current brightness
            try:
                brightness = self.config_manager.config.led.animations.get('idle', {}).get('brightness', 0.8)
            except:
                brightness = 0.8

            zones = self.config_manager.config.led.zones

            for level in range(1, len(zones) + 1):
                try:
                    start, end = zones[level - 1]
                except IndexError:
                    continue

                # Turn off all first
                await self.hardware.led.turn_off()
                await asyncio.sleep(0.05)

                # Light up this zone with unique color
                color = colors[(level - 1) % len(colors)]
                await self.hardware.led.set_zone_pixels(start, end, color[0], color[1], color[2], brightness)
                await asyncio.sleep(0.5)

            # Turn off after test
            await asyncio.sleep(1.0)
            await self.hardware.led.turn_off()

        # Track task for cleanup
        task = asyncio.create_task(test_all_zones_async())
        self._zone_test_tasks.append(task)

    def _play_animation(self, animation_name: str):
        """Play a predefined animation."""
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.play_animation(animation_name))

    def _turn_off_leds(self):
        """Turn off all LEDs."""
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.turn_off())

    def _get_led_status(self):
        """Get current LED status for live display."""
        status_items = []

        if self.hardware.led:
            # Connection status
            is_connected = self.hardware.led.is_connected()
            connected_text = "YES" if is_connected else "NO"
            connected_color = (0, 1, 0, 1) if is_connected else (1, 0, 0, 1)
            status_items.append(("Connected:", connected_text, connected_color))

            # IP address
            ip = self.config_manager.config.hardware.wled.ip_address
            status_items.append(("IP:", ip, (1, 1, 1, 1)))

            # Pixel count
            pixels = self.config_manager.config.hardware.wled.pixel_count
            status_items.append(("Pixels:", str(pixels), (1, 1, 1, 1)))
        else:
            status_items.append(("Status:", "Not available", (0.5, 0.5, 0.5, 1)))

        return status_items

    def _reset_to_defaults(self):
        """Reset LED and WLED sections to factory defaults."""
        def confirm_reset():
            # Reset both hardware.wled and led sections
            success_wled = reset_section_to_defaults(self.config_manager, "hardware.wled")
            success_led = reset_section_to_defaults(self.config_manager, "led")

            if success_wled and success_led:
                # Reload screen to show new values
                self._show_reset_success()
            else:
                self._show_reset_error()

        show_confirm_dialog(
            title="Restore Factory Settings",
            text="Reset all LED settings to factory defaults?\n\nThis affects:\n- WLED connection\n- Zone mapping\n- Animations",
            on_confirm=confirm_reset
        )

    def _show_reset_success(self):
        """Show success message after reset."""
        dialog = MDDialog(
            title="Success",
            text="LED settings have been reset.\n\nPlease return to menu and reopen this screen to see new values.",
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
        # Cancel any pending zone test tasks
        for task in self._zone_test_tasks:
            if not task.done():
                task.cancel()

        self._zone_test_tasks.clear()

        # Turn off LEDs if a test was running
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.turn_off())
