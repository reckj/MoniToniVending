"""
Shared widget library for settings sub-screens.

Contains reusable components:
- NumpadDialog: On-screen numeric keypad for input
- SettingsCard: Grouped settings section with header
- HoldButton: Hold-to-activate button for hardware control
- LiveStatusCard: Real-time hardware status display
- NumpadField: Convenience widget for numeric config fields
- Config helpers: Auto-save and reset-to-defaults utilities
"""

import asyncio
import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel

from monitoni.core.config import ConfigManager


# Color constants
CORAL_ACCENT = (242/255, 64/255, 51/255, 1)  # #F24033
NEAR_BLACK = (0.12, 0.12, 0.12, 1)  # #1F1F1F equivalent
ERROR_RED = (1, 0, 0, 1)


# Risky config paths that require confirmation
RISKY_PATHS = [
    "hardware.modbus.port",
    "hardware.modbus.slave_address",
    "hardware.gpio.door_sensor_pin",
    "vending.motor.relay_channel",
    "vending.motor.spindle_lock_relay",
]


class NumpadDialog:
    """
    Modal dialog with on-screen 3x4 numeric keypad.

    Accepts numeric input via touch-friendly button grid.
    Validates input against min/max bounds before submission.
    """

    def __init__(
        self,
        title: str,
        initial_value: float = 0.0,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_decimal: bool = False,
        on_submit: Optional[Callable[[float], None]] = None
    ):
        """
        Initialize numpad dialog.

        Args:
            title: Dialog title text
            initial_value: Starting value to display
            min_value: Minimum allowed value (None for no limit)
            max_value: Maximum allowed value (None for no limit)
            allow_decimal: Whether to allow decimal point input
            on_submit: Callback invoked with validated float value on OK
        """
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.allow_decimal = allow_decimal
        self.on_submit = on_submit

        # Current input state
        self.current_value = str(initial_value) if initial_value != 0 else "0"

        # Build dialog UI
        self._build_ui()

    def _build_ui(self):
        """Build the numpad dialog UI."""
        # Content container
        content = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")
        content.size_hint_y = None
        content.height = "400dp"

        # Display area showing current value
        self.display_label = MDLabel(
            text=self.current_value,
            font_style='H4',
            halign='right',
            size_hint_y=None,
            height="60dp"
        )
        content.add_widget(self.display_label)

        # Numpad grid (4 rows x 3 columns)
        numpad_grid = GridLayout(cols=3, spacing="5dp", size_hint_y=None)
        numpad_grid.height = "280dp"

        # Button layout: 1-9, decimal/0/backspace
        buttons = [
            '7', '8', '9',
            '4', '5', '6',
            '1', '2', '3',
            '.' if self.allow_decimal else '', '0', '⌫'
        ]

        for btn_text in buttons:
            if btn_text == '':
                # Empty placeholder
                numpad_grid.add_widget(BoxLayout())
            else:
                btn = MDRaisedButton(
                    text=btn_text,
                    md_bg_color=NEAR_BLACK,
                    size_hint=(1, 1),
                    on_release=lambda x, text=btn_text: self._on_key_press(text)
                )
                numpad_grid.add_widget(btn)

        content.add_widget(numpad_grid)

        # Create dialog with action buttons
        self.dialog = MDDialog(
            title=self.title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="ABBRECHEN",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: self._on_ok_pressed()
                ),
            ],
        )

    def _on_key_press(self, key: str):
        """Handle numpad key press."""
        if key == '⌫':
            # Backspace: remove last digit
            if len(self.current_value) > 1:
                self.current_value = self.current_value[:-1]
            else:
                self.current_value = "0"
        elif key == '.':
            # Decimal point: only allow one
            if '.' not in self.current_value:
                self.current_value += '.'
        else:
            # Digit: append to current value
            if self.current_value == "0":
                self.current_value = key
            else:
                self.current_value += key

        # Update display
        self.display_label.text = self.current_value

    def _on_ok_pressed(self):
        """Handle OK button press with validation."""
        try:
            # Parse value
            value = float(self.current_value)

            # Validate bounds
            if self.min_value is not None and value < self.min_value:
                self.display_label.text = f"Min: {self.min_value}"
                return

            if self.max_value is not None and value > self.max_value:
                self.display_label.text = f"Max: {self.max_value}"
                return

            # Valid: invoke callback and dismiss
            if self.on_submit:
                self.on_submit(value)

            self.dialog.dismiss()

        except ValueError:
            # Invalid number format
            self.display_label.text = "Invalid"

    def open(self):
        """Open the dialog."""
        self.dialog.open()


class SettingsCard(MDCard):
    """
    Card widget for grouping related settings with a section header.

    Provides consistent near-black styling with coral accent header.
    """

    def __init__(self, title: str, **kwargs):
        """
        Initialize settings card.

        Args:
            title: Section header text
            **kwargs: Additional MDCard arguments
        """
        # Apply default styling
        kwargs.setdefault('md_bg_color', NEAR_BLACK)
        kwargs.setdefault('radius', [10, 10, 10, 10])
        kwargs.setdefault('padding', "15dp")
        kwargs.setdefault('size_hint_y', None)

        super().__init__(**kwargs)

        # Root layout
        root = BoxLayout(orientation='vertical', spacing="10dp", size_hint_y=None)
        root.bind(minimum_height=root.setter('height'))

        # Header with coral accent
        header = MDLabel(
            text=title,
            font_style='H6',
            theme_text_color='Custom',
            text_color=CORAL_ACCENT,
            size_hint_y=None,
            height="30dp"
        )
        root.add_widget(header)

        # Content container
        self.content_box = BoxLayout(
            orientation='vertical',
            spacing="10dp",
            size_hint_y=None
        )
        self.content_box.bind(minimum_height=self.content_box.setter('height'))
        root.add_widget(self.content_box)

        self.add_widget(root)

        # Auto-update card height when content changes
        root.bind(minimum_height=lambda *args: setattr(self, 'height', root.minimum_height))

    def add_content(self, widget):
        """
        Add a widget to the card's content area.

        Args:
            widget: Widget to add
        """
        self.content_box.add_widget(widget)


def update_config_value(
    config_manager: ConfigManager,
    config_path: str,
    new_value: Any,
    hardware: Any = None
) -> Tuple[bool, bool]:
    """
    Update a configuration value and save to local.yaml.

    Builds nested dict from dot-notation path and persists immediately.

    Args:
        config_manager: ConfigManager instance
        config_path: Dot-notation path (e.g., "hardware.modbus.port")
        new_value: New value to set
        hardware: Optional hardware manager (unused, for future validation)

    Returns:
        Tuple of (success: bool, needs_confirmation: bool)
        - success: Whether update was applied
        - needs_confirmation: Whether this is a risky path requiring user confirmation
    """
    # Check if this is a risky path
    needs_confirmation = config_path in RISKY_PATHS

    # Build nested dict from dot-notation path
    path_parts = config_path.split('.')
    update_dict = {}
    current = update_dict

    for i, part in enumerate(path_parts):
        if i == len(path_parts) - 1:
            # Last part: set the value
            current[part] = new_value
        else:
            # Intermediate part: create nested dict
            current[part] = {}
            current = current[part]

    # Save to local config
    try:
        config_manager.save_local(update_dict)
        return True, needs_confirmation
    except Exception as e:
        print(f"Failed to update config: {e}")
        return False, needs_confirmation


def get_section_defaults(config_path_prefix: str) -> Dict[str, Any]:
    """
    Get factory default values for a config section from default.yaml.

    Args:
        config_path_prefix: Dot-notation prefix (e.g., "hardware.modbus")

    Returns:
        Dictionary of default values for that section
    """
    # Load default.yaml
    config_dir = Path(__file__).parent.parent.parent.parent / "config"
    default_config_path = config_dir / "default.yaml"

    with open(default_config_path, 'r') as f:
        defaults = yaml.safe_load(f)

    # Navigate to the specified section
    path_parts = config_path_prefix.split('.')
    current = defaults

    for part in path_parts:
        if part in current:
            current = current[part]
        else:
            return {}

    return current


def reset_section_to_defaults(
    config_manager: ConfigManager,
    config_path_prefix: str
) -> bool:
    """
    Reset a config section to factory defaults.

    Args:
        config_manager: ConfigManager instance
        config_path_prefix: Dot-notation prefix (e.g., "hardware.modbus")

    Returns:
        True if reset successful, False otherwise
    """
    try:
        # Get defaults for this section
        defaults = get_section_defaults(config_path_prefix)

        if not defaults:
            return False

        # Build nested dict to reset this section
        path_parts = config_path_prefix.split('.')
        update_dict = {}
        current = update_dict

        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                # Last part: set the default values
                current[part] = defaults
            else:
                # Intermediate part: create nested dict
                current[part] = {}
                current = current[part]

        # Save to local config
        config_manager.save_local(update_dict)
        return True

    except Exception as e:
        print(f"Failed to reset section to defaults: {e}")
        return False


def show_confirm_dialog(
    title: str,
    text: str,
    on_confirm: Optional[Callable[[], None]] = None
) -> MDDialog:
    """
    Show a confirmation dialog with German labels.

    Args:
        title: Dialog title
        text: Dialog content text
        on_confirm: Callback invoked on OK button press

    Returns:
        MDDialog instance
    """
    def _on_ok(instance):
        if on_confirm:
            on_confirm()
        dialog.dismiss()

    dialog = MDDialog(
        title=title,
        text=text,
        buttons=[
            MDFlatButton(
                text="ABBRECHEN",
                on_release=lambda x: dialog.dismiss()
            ),
            MDRaisedButton(
                text="OK",
                md_bg_color=CORAL_ACCENT,
                on_release=_on_ok
            ),
        ],
    )

    dialog.open()
    return dialog
