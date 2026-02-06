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
        self.hardware = hardware
        self.config_manager = config_manager

        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "QR Code Management"

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
            preview=True,
            ext=['.png', '.jpg', '.jpeg'],
        )

        self._build_content()

    def _build_content(self):
        """Build the QR management UI."""
        level_card = self._build_level_card()
        self.add_content(level_card)

        preview_card = self._build_preview_card()
        self.add_content(preview_card)

        actions_card = self._build_actions_card()
        self.add_content(actions_card)

    def _build_level_card(self) -> SettingsCard:
        """Build level selection card."""
        card = SettingsCard(title="Select Level")

        level_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        level_label = MDLabel(
            text="Product Level:",
            size_hint_x=0.6,
            font_style='Body1'
        )
        level_row.add_widget(level_label)

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
            title="Select Product Level",
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
        card = SettingsCard(title="Current QR Code")

        self.qr_preview = Image(
            size_hint=(1, None),
            height="300dp",
            allow_stretch=True,
            keep_ratio=True
        )
        card.add_content(self.qr_preview)

        self.status_label = MDLabel(
            text="Level 1 (No QR Code)",
            halign='center',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(self.status_label)

        return card

    def _build_actions_card(self) -> SettingsCard:
        """Build actions card."""
        card = SettingsCard(title="Actions")

        generate_btn = MDRaisedButton(
            text="Generate QR Code",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=self.show_generate_dialog
        )
        card.add_content(generate_btn)

        upload_btn = MDRaisedButton(
            text="Upload from USB",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=NEAR_BLACK,
            on_release=self.open_usb_browser
        )
        card.add_content(upload_btn)

        self.delete_btn = MDRaisedButton(
            text="Delete Custom QR",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=ERROR_RED,
            on_release=self.delete_custom_qr
        )
        card.add_content(self.delete_btn)

        return card

    def on_enter(self):
        """Called when screen is entered."""
        self.on_level_changed(1)

    def on_level_changed(self, level: float):
        """Handle level selection change."""
        self.selected_level = int(level)
        self.update_preview()

    def update_preview(self):
        """Update QR code preview for selected level."""
        if self.selected_level is None:
            return

        # Check for custom QR first (takes precedence)
        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"
        if custom_path.exists():
            self.qr_preview.source = ""
            Clock.schedule_once(lambda dt: self._set_preview_source(str(custom_path)), 0.1)
            self.status_label.text = f"Level {self.selected_level} (Custom)"
            return

        # Check for generated QR
        generated_path = self.qr_dir / f"level_{self.selected_level}.png"
        if generated_path.exists():
            self.qr_preview.source = ""
            Clock.schedule_once(lambda dt: self._set_preview_source(str(generated_path)), 0.1)
            self.status_label.text = f"Level {self.selected_level} (Generated)"
            return

        # No QR code exists
        self.qr_preview.source = ""
        self.status_label.text = f"Level {self.selected_level} (No QR Code)"

    def _set_preview_source(self, source_path: str):
        """Set preview image source (deferred to ensure reload)."""
        self.qr_preview.source = source_path
        self.qr_preview.reload()

    def show_generate_dialog(self, instance):
        """Show dialog to enter payment URL."""
        if self.selected_level is None:
            return

        default_url = f"https://www.monitoni.zhdk.ch?level={self.selected_level}"

        self.text_input_dialog = TextInputDialog(
            title="Enter Payment URL",
            label=f"URL for Level {self.selected_level}:",
            initial_value=default_url,
            on_submit=self.generate_qr_from_url
        )
        self.text_input_dialog.open()

    def generate_qr_from_url(self, url: str):
        """Generate QR code from payment URL."""
        if not url or self.selected_level is None:
            return

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            output_path = self.qr_dir / f"level_{self.selected_level}.png"
            img.save(str(output_path))

            self.update_preview()
            self._show_dialog("Success", f"QR code generated for Level {self.selected_level}!")

        except Exception as e:
            self._show_dialog("Error", f"Failed to generate: {str(e)}", error=True)

    def open_usb_browser(self, instance):
        """Open file browser for USB drive."""
        if self.selected_level is None:
            return

        usb_path = Path("/media") / os.getenv("USER", "admin")
        if usb_path.exists():
            self.file_manager.show(str(usb_path))
        else:
            self.file_manager.show("/media")

    def exit_file_manager(self, *args):
        """Called when file manager reaches root or exits."""
        self.file_manager.close()

    def select_qr_file(self, path):
        """Handle file selection from USB."""
        src = Path(path)

        if not src.is_file():
            return

        if src.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
            self._show_dialog("Error", "Only PNG/JPG files supported", error=True)
            self.file_manager.close()
            return

        try:
            dst = self.qr_dir / f"custom_level_{self.selected_level}.png"
            shutil.copy2(src, dst)
            self.update_preview()
            self._show_dialog("Success", f"QR code uploaded for Level {self.selected_level}!")
        except Exception as e:
            self._show_dialog("Error", f"Failed to upload: {str(e)}", error=True)

        self.file_manager.close()

    def delete_custom_qr(self, instance):
        """Delete custom QR code for selected level."""
        if self.selected_level is None:
            return

        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"

        if not custom_path.exists():
            self._show_dialog("Error", "No custom QR code exists", error=True)
            return

        dialog = MDDialog(
            title="Delete QR Code?",
            text=f"Delete custom QR code for Level {self.selected_level}?",
            buttons=[
                MDRaisedButton(
                    text="Cancel",
                    md_bg_color=NEAR_BLACK,
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Delete",
                    md_bg_color=ERROR_RED,
                    on_release=lambda x: self._confirm_delete(dialog, custom_path)
                ),
            ],
        )
        dialog.open()

    def _confirm_delete(self, dialog, path: Path):
        """Confirm deletion and remove file."""
        try:
            path.unlink()
            self.update_preview()
            self._show_dialog("Success", "Custom QR code deleted")
        except Exception as e:
            self._show_dialog("Error", f"Failed to delete: {str(e)}", error=True)
        finally:
            dialog.dismiss()

    def _show_dialog(self, title: str, message: str, error: bool = False):
        """Show a message dialog."""
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=ERROR_RED if error else CORAL_ACCENT,
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()
