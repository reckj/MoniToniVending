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
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.colorpicker import MDColorPicker

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
        self.title = "LED-Steuerung"

        self._build_content()

    def _build_content(self):
        """Build the LED settings screen content."""
        # Card 1: WLED Connection & Brightness
        brightness_card = SettingsCard(title="WLED-Verbindung & Helligkeit")

        # Pixel count
        pixel_count_field = NumpadField(
            label="Pixel-Anzahl",
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
            text="IP-Adresse",
            size_hint_x=0.6,
            font_style='Body1'
        )
        ip_row.add_widget(ip_label)

        current_ip = self.config_manager.config.hardware.wled.ip_address
        self.ip_button = MDRaisedButton(
            text=current_ip,
            size_hint_x=0.4,
            md_bg_color=NEAR_BLACK,
            on_release=lambda x: self._open_ip_dialog()
        )
        ip_row.add_widget(self.ip_button)
        brightness_card.add_content(ip_row)

        # FPS
        fps_field = NumpadField(
            label="FPS",
            config_path="hardware.wled.fps",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=60
        )
        brightness_card.add_content(fps_field)

        # Brightness control
        brightness_row = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing="10dp"
        )
        brightness_row.bind(minimum_height=brightness_row.setter('height'))

        brightness_label = MDLabel(
            text="Helligkeit",
            font_style='Body1',
            size_hint_y=None,
            height="30dp"
        )
        brightness_row.add_widget(brightness_label)

        # Get current brightness from config (stored in animations.idle.brightness)
        try:
            current_brightness = self.config_manager.config.led.animations.get('idle', {}).get('brightness', 0.8)
        except:
            current_brightness = 0.8

        brightness_value_field = NumpadField(
            label="Helligkeit (%)",
            config_path="led.animations.idle.brightness",
            config_manager=self.config_manager,
            allow_decimal=True,
            min_value=0,
            max_value=100,
            on_value_changed=self._on_brightness_changed
        )
        brightness_row.add_widget(brightness_value_field)

        brightness_card.add_content(brightness_row)

        self.add_content(brightness_card)

        # Card 2: Color Test
        color_card = SettingsCard(title="Farb-Test")

        # Row 1: Red, Green, Blue
        color_row1 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        for color_name, rgb in [("Rot", (255, 0, 0)), ("Grün", (0, 255, 0)), ("Blau", (0, 0, 255))]:
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
            ("Weiß", (255, 255, 255), (0, 0, 0, 1)),
            ("Gelb", (255, 255, 0), (0, 0, 0, 1)),
            ("Aus", (0, 0, 0), (1, 1, 1, 1))
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

        # Custom color picker button
        custom_color_btn = MDRaisedButton(
            text="Eigene Farbe",
            size_hint_y=None,
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._open_color_picker()
        )
        color_card.add_content(custom_color_btn)

        self.add_content(color_card)

        # Card 3: Zone Mapping
        zone_card = SettingsCard(title="Zonen-Zuordnung")

        # Info label
        pixel_count = self.config_manager.config.hardware.wled.pixel_count
        info_label = MDLabel(
            text=f"Pixel gesamt: {pixel_count}",
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
                text=f"Fach {level}:",
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
            text="Alle Zonen testen",
            size_hint_y=None,
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._test_all_zones()
        )
        zone_card.add_content(test_all_btn)

        self.add_content(zone_card)

        # Card 4: Animations
        animation_card = SettingsCard(title="Animationen")

        # Animation buttons (3 per row)
        animations = [
            ("idle", "Leerlauf"),
            ("sleep", "Schlaf"),
            ("valid_purchase", "Kauf gültig"),
            ("invalid_purchase", "Kauf ungültig"),
            ("door_alarm", "Tür-Alarm"),
            ("offline", "Offline"),
            ("level_highlight", "Fach-Highlight"),
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
            text="Alle aus",
            size_hint_y=None,
            height="60dp",
            md_bg_color=(0.3, 0.3, 0.3, 1),
            on_release=lambda x: self._turn_off_leds()
        )
        animation_card.add_content(all_off_btn)

        self.add_content(animation_card)

        # Card 5: Live Status
        status_card = LiveStatusCard(
            title="LED-Status",
            get_status_callback=self._get_led_status,
            update_interval=2.0
        )
        status_card.height = "150dp"
        self.add_content(status_card)

        # Reset button
        reset_btn = MDRaisedButton(
            text="Werkseinstellungen",
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
            title="IP-Adresse eingeben",
            type="custom",
            content_cls=content,
            buttons=[
                MDRaisedButton(
                    text="ABBRECHEN",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="SPEICHERN",
                    md_bg_color=CORAL_ACCENT,
                    on_release=on_save
                ),
            ],
        )
        dialog.open()

    def _on_brightness_changed(self, value: float):
        """Handle brightness value change."""
        # Convert percentage (0-100) to float (0.0-1.0)
        brightness = value / 100.0

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

    def _open_color_picker(self):
        """Open Kivy color picker for custom color selection."""
        def on_select_color(instance_color_picker):
            """Handle color selection from picker."""
            # MDColorPicker returns color as (r, g, b, a) with values 0-1
            color = instance_color_picker.get_rgb()
            r = int(color[0] * 255)
            g = int(color[1] * 255)
            b = int(color[2] * 255)

            # Apply to LEDs immediately
            self._set_color(r, g, b)

        color_picker = MDColorPicker(size_hint=(0.45, 0.85))
        color_picker.open()
        color_picker.bind(
            on_select_color=on_select_color,
            on_release=lambda x: color_picker.dismiss()
        )

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
            connected_text = "JA" if is_connected else "NEIN"
            connected_color = (0, 1, 0, 1) if is_connected else (1, 0, 0, 1)
            status_items.append(("Verbunden:", connected_text, connected_color))

            # IP address
            ip = self.config_manager.config.hardware.wled.ip_address
            status_items.append(("IP:", ip, (1, 1, 1, 1)))

            # Pixel count
            pixels = self.config_manager.config.hardware.wled.pixel_count
            status_items.append(("Pixel:", str(pixels), (1, 1, 1, 1)))
        else:
            status_items.append(("Status:", "Nicht verfügbar", (0.5, 0.5, 0.5, 1)))

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
            title="Werkseinstellungen wiederherstellen",
            text="Möchten Sie wirklich alle LED-Einstellungen auf Werkseinstellungen zurücksetzen?\n\nDies betrifft:\n- WLED-Verbindung\n- Zonen-Zuordnung\n- Animationen",
            on_confirm=confirm_reset
        )

    def _show_reset_success(self):
        """Show success message after reset."""
        dialog = MDDialog(
            title="Erfolgreich",
            text="LED-Einstellungen wurden zurückgesetzt.\n\nBitte kehren Sie zum Menü zurück und öffnen Sie diesen Bildschirm erneut, um die neuen Werte anzuzeigen.",
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
            title="Fehler",
            text="Fehler beim Zurücksetzen der Einstellungen.",
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
        # Cancel any pending zone test tasks
        for task in self._zone_test_tasks:
            if not task.done():
                task.cancel()

        self._zone_test_tasks.clear()

        # Turn off LEDs if a test was running
        if self.hardware.led:
            asyncio.create_task(self.hardware.led.turn_off())
