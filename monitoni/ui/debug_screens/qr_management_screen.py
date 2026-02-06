"""
QR code management screen for operator maintenance.

Allows operators to:
- Generate QR codes from payment URLs
- Upload QR codes from USB drive
- Preview QR codes for each level
- Delete custom QR codes (revert to generated)
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
import qrcode

from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    NumpadDialog,
    TextInputDialog,
    CORAL_ACCENT,
    NEAR_BLACK,
    ERROR_RED,
    INPUT_BUTTON,
)


class QRManagementScreen(BaseDebugSubScreen):
    """QR code generation and assignment for product levels."""

    def __init__(self, hardware: HardwareManager, config_manager: ConfigManager,
                 navigate_back=None, **kwargs):
        """
        Initialize QR management screen.

        Args:
            hardware: Hardware manager (unused but required for consistency)
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager

        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "QR Code Verwaltung"

        # QR code directory
        self.qr_dir = Path("assets/qr_codes")
        self.qr_dir.mkdir(parents=True, exist_ok=True)

        # Current selected level
        self.selected_level: Optional[int] = None

        # Text input dialog reference
        self.text_input_dialog: Optional[TextInputDialog] = None

        # File manager for USB browsing
        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.select_qr_file,
            preview=True,  # Show image previews
            ext=['.png', '.jpg', '.jpeg'],
        )

        self._build_content()

    def _build_content(self):
        """Build the QR management UI."""
        # Card 1: Level selection
        level_card = self._build_level_card()
        self.add_content(level_card)

        # Card 2: QR preview
        preview_card = self._build_preview_card()
        self.add_content(preview_card)

        # Card 3: Actions
        actions_card = self._build_actions_card()
        self.add_content(actions_card)

    def _build_level_card(self) -> SettingsCard:
        """Build level selection card."""
        card = SettingsCard(title="Level auswählen")

        # Level selection row
        level_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        # Label
        level_label = MDLabel(
            text="Product Level:",
            size_hint_x=0.6,
            font_style='Body1'
        )
        level_row.add_widget(level_label)

        # Tappable value button
        self.level_button = MDRaisedButton(
            text="1",
            size_hint_x=0.4,
            md_bg_color=INPUT_BUTTON,
            on_release=lambda x: self._open_level_numpad()
        )
        level_row.add_widget(self.level_button)

        card.add_content(level_row)

        return card

    def _open_level_numpad(self):
        """Open numpad dialog for level selection."""
        current_level = self.selected_level if self.selected_level is not None else 1

        dialog = NumpadDialog(
            title="Product Level auswählen",
            initial_value=current_level,
            min_value=1,
            max_value=self.config_manager.config.vending.levels,
            allow_decimal=False,
            on_submit=self._on_level_submitted
        )
        dialog.open()

    def _on_level_submitted(self, level: float):
        """Handle level selection from numpad."""
        level_int = int(level)
        self.level_button.text = str(level_int)
        self.on_level_changed(level)

    def _build_preview_card(self) -> SettingsCard:
        """Build QR preview card."""
        card = SettingsCard(title="Aktuelle QR Code")

        # QR preview image
        self.qr_preview = Image(
            size_hint=(1, None),
            height="300dp",
            allow_stretch=True,
            keep_ratio=True
        )
        card.add_content(self.qr_preview)

        # Status label
        self.status_label = MDLabel(
            text="Level 1 (Kein QR Code)",
            halign='center',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(self.status_label)

        return card

    def _build_actions_card(self) -> SettingsCard:
        """Build actions card."""
        card = SettingsCard(title="Aktionen")

        # Generate button
        generate_btn = MDRaisedButton(
            text="QR Code generieren",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=self.show_generate_dialog
        )
        card.add_content(generate_btn)

        # Upload button
        upload_btn = MDRaisedButton(
            text="Von USB hochladen",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=NEAR_BLACK,
            on_release=self.open_usb_browser
        )
        card.add_content(upload_btn)

        # Delete custom button
        self.delete_btn = MDRaisedButton(
            text="Custom QR löschen",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=ERROR_RED,
            on_release=self.delete_custom_qr
        )
        card.add_content(self.delete_btn)

        return card

    def on_enter(self):
        """Called when screen is entered."""
        # Initialize with level 1
        self.on_level_changed(1)

    def on_level_changed(self, level: float):
        """
        Handle level selection change.

        Args:
            level: Selected level number
        """
        self.selected_level = int(level)
        self.update_preview()

    def update_preview(self):
        """Update QR code preview for selected level."""
        if self.selected_level is None:
            return

        # Check for custom QR first (takes precedence)
        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"
        if custom_path.exists():
            # Force reload by clearing source first
            self.qr_preview.source = ""
            Clock.schedule_once(lambda dt: self._set_preview_source(str(custom_path)), 0.1)
            self.status_label.text = f"Level {self.selected_level} (Custom)"
            return

        # Check for generated QR
        generated_path = self.qr_dir / f"level_{self.selected_level}.png"
        if generated_path.exists():
            # Force reload by clearing source first
            self.qr_preview.source = ""
            Clock.schedule_once(lambda dt: self._set_preview_source(str(generated_path)), 0.1)
            self.status_label.text = f"Level {self.selected_level} (Generiert)"
            return

        # No QR code exists
        self.qr_preview.source = ""
        self.status_label.text = f"Level {self.selected_level} (Kein QR Code)"

    def _set_preview_source(self, source_path: str):
        """Set preview image source (deferred to ensure reload)."""
        self.qr_preview.source = source_path
        self.qr_preview.reload()

    def show_generate_dialog(self, instance):
        """Show dialog to enter payment URL."""
        if self.selected_level is None:
            return

        # Default URL based on customer_screen.py pattern
        default_url = f"https://www.monitoni.zhdk.ch?level={self.selected_level}"

        self.text_input_dialog = TextInputDialog(
            title="Zahlungslink URL eingeben",
            label=f"URL für Level {self.selected_level}:",
            initial_value=default_url,
            on_submit=self.generate_qr_from_url
        )
        self.text_input_dialog.open()

    def generate_qr_from_url(self, url: str):
        """
        Generate QR code from payment URL.

        Args:
            url: Payment URL to encode
        """
        if not url or self.selected_level is None:
            return

        try:
            # Generate QR code with ERROR_CORRECT_M (15% correction)
            qr = qrcode.QRCode(
                version=1,  # Auto-size
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Save to generated slot
            output_path = self.qr_dir / f"level_{self.selected_level}.png"
            img.save(str(output_path))

            # Update preview
            self.update_preview()

            # Show success
            self.show_success_dialog(f"QR Code für Level {self.selected_level} generiert!")

        except Exception as e:
            self.show_error_dialog(f"Fehler beim Generieren: {str(e)}")

    def open_usb_browser(self, instance):
        """Open file browser for USB drive."""
        if self.selected_level is None:
            return

        # Try user-specific mount point first (Raspberry Pi OS Desktop)
        usb_path = Path("/media") / os.getenv("USER", "admin")
        if usb_path.exists():
            self.file_manager.show(str(usb_path))
        else:
            # Fallback to /media root
            self.file_manager.show("/media")

    def exit_file_manager(self, *args):
        """Called when file manager reaches root or exits."""
        self.file_manager.close()

    def select_qr_file(self, path):
        """
        Handle file selection from USB.

        Args:
            path: Selected file path
        """
        src = Path(path)

        if not src.is_file():
            return

        if src.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
            self.show_error_dialog("Nur PNG/JPG Dateien unterstützt")
            self.file_manager.close()
            return

        try:
            # Copy to custom slot (takes precedence over generated)
            dst = self.qr_dir / f"custom_level_{self.selected_level}.png"
            shutil.copy2(src, dst)

            # Update preview
            self.update_preview()

            # Show success
            self.show_success_dialog(f"QR Code für Level {self.selected_level} hochgeladen!")

        except Exception as e:
            self.show_error_dialog(f"Fehler beim Hochladen: {str(e)}")

        self.file_manager.close()

    def delete_custom_qr(self, instance):
        """Delete custom QR code for selected level."""
        if self.selected_level is None:
            return

        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"

        if not custom_path.exists():
            self.show_error_dialog("Kein custom QR Code vorhanden")
            return

        # Show confirmation dialog
        dialog = MDDialog(
            title="QR Code löschen?",
            text=f"Custom QR Code für Level {self.selected_level} wirklich löschen?",
            buttons=[
                MDRaisedButton(
                    text="Abbrechen",
                    md_bg_color=NEAR_BLACK,
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Löschen",
                    md_bg_color=ERROR_RED,
                    on_release=lambda x: self._confirm_delete(dialog, custom_path)
                ),
            ],
        )
        dialog.open()

    def _confirm_delete(self, dialog, path: Path):
        """
        Confirm deletion and remove file.

        Args:
            dialog: Dialog to dismiss
            path: Path to delete
        """
        try:
            path.unlink()
            self.update_preview()
            self.show_success_dialog("Custom QR Code gelöscht")
        except Exception as e:
            self.show_error_dialog(f"Fehler beim Löschen: {str(e)}")
        finally:
            dialog.dismiss()

    def show_success_dialog(self, message: str):
        """
        Show success message dialog.

        Args:
            message: Success message
        """
        dialog = MDDialog(
            title="Erfolg",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()

    def show_error_dialog(self, message: str):
        """
        Show error message dialog.

        Args:
            message: Error message
        """
        dialog = MDDialog(
            title="Fehler",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=ERROR_RED,
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()
