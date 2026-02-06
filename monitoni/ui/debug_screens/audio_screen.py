"""
Audio settings screen for volume control and sound testing.

Provides:
- Volume control with numpad input
- Sound test buttons for each configured sound
- Sound file path verification
- Live audio status display
- Reset to factory defaults
"""

import asyncio
from pathlib import Path
from typing import List, Tuple

from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDSwitch

from monitoni.core.config import ConfigManager
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    LiveStatusCard,
    NumpadField,
    update_config_value,
    reset_section_to_defaults,
    show_confirm_dialog,
    CORAL_ACCENT,
    NEAR_BLACK,
)


class AudioSettingsScreen(BaseDebugSubScreen):
    """
    Audio configuration and testing screen.

    Allows operators to:
    - Adjust audio volume (0-100%)
    - Test sound effects
    - View sound file status
    - Monitor audio hardware status
    - Reset to factory defaults
    """

    def __init__(self, hardware, config_manager: ConfigManager, navigate_back=None, **kwargs):
        """
        Initialize audio settings screen.

        Args:
            hardware: Hardware manager with audio controller
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager

        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "Audio"

        self._build_content()

    def _build_content(self):
        """Build the audio settings UI."""
        # Card 1: Volume control
        volume_card = self._build_volume_card()
        self.add_content(volume_card)

        # Card 2: Sound test buttons
        sound_test_card = self._build_sound_test_card()
        self.add_content(sound_test_card)

        # Card 3: Sound file status
        sound_files_card = self._build_sound_files_card()
        self.add_content(sound_files_card)

        # Card 4: Live status
        status_card = self._build_status_card()
        self.add_content(status_card)

        # Reset button
        reset_button = self._build_reset_button()
        self.add_content(reset_button)

    def _build_volume_card(self) -> SettingsCard:
        """Build volume control card."""
        card = SettingsCard(title="Lautstärke")

        # Get current volume (stored as 0.0-1.0, display as 0-100%)
        current_volume = self.config_manager.config.hardware.audio.volume
        volume_percent = int(current_volume * 100)

        # Large volume display
        volume_display = MDLabel(
            text=f"{volume_percent}%",
            font_style='H4',
            halign='center',
            size_hint_y=None,
            height="60dp"
        )
        self.volume_display_label = volume_display
        card.add_content(volume_display)

        # NumpadField for volume adjustment (0-100%)
        volume_field = NumpadField(
            label="Lautstärke (%)",
            config_path="hardware.audio.volume",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=100,
            on_value_changed=self._on_volume_changed
        )
        # Override the display to show percentage
        volume_field.current_value = volume_percent
        volume_field.value_button.text = str(volume_percent)
        card.add_content(volume_field)

        # Audio enabled toggle
        toggle_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        toggle_label = MDLabel(
            text="Audio aktiviert",
            size_hint_x=0.7,
            font_style='Body1'
        )
        toggle_row.add_widget(toggle_label)

        audio_toggle = MDSwitch(
            size_hint_x=0.3
        )
        # Set active after construction to avoid KivyMD 1.2 on_active crash
        # (self.ids.thumb doesn't exist during __init__)
        from kivy.clock import Clock
        initial_active = self.config_manager.config.hardware.audio.enabled
        Clock.schedule_once(lambda dt: setattr(audio_toggle, 'active', initial_active))
        audio_toggle.bind(active=self._on_audio_enabled_changed)
        toggle_row.add_widget(audio_toggle)

        card.add_content(toggle_row)

        return card

    def _build_sound_test_card(self) -> SettingsCard:
        """Build sound test buttons card."""
        card = SettingsCard(title="Sound-Test")

        # Get configured sounds
        sounds = self.config_manager.config.audio.sounds

        # German display names
        sound_labels = {
            'valid_purchase': 'Erfolg',
            'invalid_purchase': 'Fehler',
            'door_alarm': 'Alarm'
        }

        # Create buttons row
        buttons_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="60dp",
            spacing="10dp"
        )

        # Add a button for each sound
        for sound_name, display_name in sound_labels.items():
            if sound_name in sounds:
                btn = MDRaisedButton(
                    text=display_name,
                    md_bg_color=NEAR_BLACK,
                    size_hint_x=1,
                    on_release=lambda x, name=sound_name: self._play_sound(name)
                )
                buttons_row.add_widget(btn)

        card.add_content(buttons_row)

        # Stop all button
        stop_btn = MDRaisedButton(
            text="Alle stoppen",
            md_bg_color=CORAL_ACCENT,
            size_hint_y=None,
            height="60dp",
            on_release=lambda x: self._stop_all_sounds()
        )
        card.add_content(stop_btn)

        return card

    def _build_sound_files_card(self) -> SettingsCard:
        """Build sound files status card."""
        card = SettingsCard(title="Sound-Dateien")

        # Get configured sounds
        sounds = self.config_manager.config.audio.sounds

        # German display names
        sound_labels = {
            'valid_purchase': 'Erfolg',
            'invalid_purchase': 'Fehler',
            'door_alarm': 'Alarm'
        }

        # Display each sound file with existence status
        for sound_name, display_name in sound_labels.items():
            if sound_name in sounds:
                sound_path = sounds[sound_name]
                file_exists = Path(sound_path).exists()

                # Status indicator
                status_icon = "✓" if file_exists else "✗"
                status_color = (0, 1, 0, 1) if file_exists else (1, 0, 0, 1)

                # File info row
                file_row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height="30dp",
                    spacing="10dp"
                )

                # Status icon
                status_label = MDLabel(
                    text=status_icon,
                    size_hint_x=None,
                    width="30dp",
                    theme_text_color='Custom',
                    text_color=status_color,
                    font_style='H6'
                )
                file_row.add_widget(status_label)

                # File info
                file_info = MDLabel(
                    text=f"{display_name}: {sound_path}",
                    size_hint_x=1,
                    font_style='Body2'
                )
                file_row.add_widget(file_info)

                card.add_content(file_row)

        return card

    def _build_status_card(self) -> LiveStatusCard:
        """Build live audio status card."""
        return LiveStatusCard(
            title="Audio-Status",
            get_status_callback=self._get_audio_status,
            update_interval=2.0
        )

    def _build_reset_button(self) -> MDRaisedButton:
        """Build reset to defaults button."""
        return MDRaisedButton(
            text="Werkseinstellungen",
            size_hint_y=None,
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._reset_to_defaults()
        )

    def _on_volume_changed(self, value: float):
        """
        Handle volume change from numpad.

        Args:
            value: New volume percentage (0-100)
        """
        # Convert percentage to 0.0-1.0 and update display
        volume_fraction = value / 100.0
        self.volume_display_label.text = f"{int(value)}%"

        # Update hardware volume immediately
        asyncio.create_task(self.hardware.audio.set_volume(volume_fraction))

        # Config is already saved by NumpadField, but we need to update it
        # with the fraction value (NumpadField saves the percentage)
        update_config_value(
            self.config_manager,
            "hardware.audio.volume",
            volume_fraction
        )

    def _on_audio_enabled_changed(self, instance, value: bool):
        """Handle audio enabled toggle change."""
        update_config_value(
            self.config_manager,
            "hardware.audio.enabled",
            value
        )

    def _play_sound(self, sound_name: str):
        """
        Play a sound effect.

        Args:
            sound_name: Name of sound to play
        """
        asyncio.create_task(self.hardware.audio.play_sound(sound_name))

    def _stop_all_sounds(self):
        """Stop all playing sounds."""
        asyncio.create_task(self.hardware.audio.stop_all())

    def _get_audio_status(self) -> List[Tuple[str, str, Tuple[float, float, float, float]]]:
        """
        Get current audio status.

        Returns:
            List of (label, value, color) tuples
        """
        status_items = []

        # Connection status
        is_connected = self.hardware.audio.is_connected()
        conn_status = "JA" if is_connected else "NEIN"
        conn_color = (0, 1, 0, 1) if is_connected else (1, 0, 0, 1)
        status_items.append(("Verbunden", conn_status, conn_color))

        # Volume
        volume = self.config_manager.config.hardware.audio.volume
        volume_percent = int(volume * 100)
        status_items.append(("Lautstärke", f"{volume_percent}%", (1, 1, 1, 1)))

        return status_items

    def _reset_to_defaults(self):
        """Reset audio settings to factory defaults."""
        show_confirm_dialog(
            title="Zurücksetzen bestätigen",
            text="Möchten Sie die Audio-Einstellungen auf Werkseinstellungen zurücksetzen?",
            on_confirm=self._do_reset
        )

    def _do_reset(self):
        """Perform the reset to defaults."""
        success = reset_section_to_defaults(
            self.config_manager,
            "hardware.audio"
        )

        if success:
            # Update volume display
            volume = self.config_manager.config.hardware.audio.volume
            volume_percent = int(volume * 100)
            self.volume_display_label.text = f"{volume_percent}%"

            # Apply to hardware
            asyncio.create_task(self.hardware.audio.set_volume(volume))
