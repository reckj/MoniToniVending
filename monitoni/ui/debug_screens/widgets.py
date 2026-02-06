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
from kivy.metrics import dp
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
INPUT_BUTTON = (0.28, 0.28, 0.28, 1)  # Brighter than NEAR_BLACK for input fields
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
                # Backspace button in red, others in dark gray
                bg_color = ERROR_RED if btn_text == '⌫' else NEAR_BLACK
                btn = MDRaisedButton(
                    text=btn_text,
                    md_bg_color=bg_color,
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
                    text="CANCEL",
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
        # Add 2x padding (top + bottom = 30dp) so title doesn't overlap borders
        root.bind(minimum_height=lambda *args: setattr(self, 'height', root.minimum_height + dp(30)))

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
    Show a confirmation dialog.

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
                text="CANCEL",
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


class HoldButton(MDRaisedButton):
    """
    Button that activates on touch_down and deactivates on touch_up.

    Designed for hardware control where holding the button keeps hardware active.
    Uses touch.grab pattern to ensure release is detected even if finger moves off button.
    """

    def __init__(
        self,
        text: str,
        on_hold: Optional[Callable[[], None]] = None,
        on_release_hold: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize hold button.

        Args:
            text: Button text
            on_hold: Callback invoked when button is pressed down
            on_release_hold: Callback invoked when button is released
            **kwargs: Additional MDRaisedButton arguments
        """
        # Default styling
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', "60dp")

        super().__init__(text=text, **kwargs)

        self.on_hold = on_hold
        self.on_release_hold = on_release_hold
        self._holding = False
        self._original_color = self.md_bg_color

    def on_touch_down(self, touch):
        """Handle touch down event."""
        # Check if touch is within button bounds
        if self.collide_point(*touch.pos):
            # Grab the touch to receive on_touch_up even if finger moves
            touch.grab(self)

            # Mark as holding and activate
            self._holding = True

            # Visual feedback: change to coral
            self._original_color = self.md_bg_color
            self.md_bg_color = CORAL_ACCENT

            # Invoke hold callback
            if self.on_hold:
                self.on_hold()

            return True

        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        """Handle touch up event."""
        # Only process if this touch was grabbed by this button
        if touch.grab_current is self:
            # Release the grab
            touch.ungrab(self)

            # If we were holding, release
            if self._holding:
                self._holding = False

                # Restore original color
                self.md_bg_color = self._original_color

                # Invoke release callback
                if self.on_release_hold:
                    self.on_release_hold()

            return True

        return super().on_touch_up(touch)

    def on_pre_leave(self, *args):
        """Safety: release if widget removed from tree while holding."""
        if self._holding:
            self._holding = False
            if self.on_release_hold:
                self.on_release_hold()


class LiveStatusCard(MDCard):
    """
    Card that displays real-time hardware status with polling.

    Periodically calls a callback to get status and updates the display.
    Status items shown with colored text for visual indicators.
    """

    def __init__(
        self,
        title: str,
        get_status_callback: Callable[[], List[Tuple[str, str, Tuple[float, float, float, float]]]],
        update_interval: float = 0.5,
        **kwargs
    ):
        """
        Initialize live status card.

        Args:
            title: Card header text
            get_status_callback: Callable returning list of (label, value, color) tuples
                                 Can be sync or async function
            update_interval: Seconds between status updates
            **kwargs: Additional MDCard arguments
        """
        # Default styling
        kwargs.setdefault('md_bg_color', NEAR_BLACK)
        kwargs.setdefault('radius', [10, 10, 10, 10])
        kwargs.setdefault('padding', "15dp")
        kwargs.setdefault('size_hint_y', None)

        super().__init__(**kwargs)

        self.get_status_callback = get_status_callback
        self.update_interval = update_interval

        # Build UI
        self._build_ui(title)

        # Schedule status updates with lambda for strong reference
        self._update_event = Clock.schedule_interval(
            lambda dt: self._update_status(),
            update_interval
        )

    def _build_ui(self, title: str):
        """Build the status card UI."""
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

        # Status items container
        self.status_container = BoxLayout(
            orientation='vertical',
            spacing="5dp",
            size_hint_y=None
        )
        self.status_container.bind(minimum_height=self.status_container.setter('height'))
        root.add_widget(self.status_container)

        self.add_widget(root)

        # Auto-update card height (add 2x padding for top + bottom)
        root.bind(minimum_height=lambda *args: setattr(self, 'height', root.minimum_height + dp(30)))

    def _update_status(self):
        """Update status display by calling the callback."""
        try:
            # Call the status callback
            if inspect.iscoroutinefunction(self.get_status_callback):
                # Async callback: schedule via asyncio
                asyncio.create_task(self._update_status_async())
            else:
                # Sync callback: call directly
                status_items = self.get_status_callback()
                self._display_status(status_items)

        except Exception as e:
            # Handle errors gracefully: show error in red
            print(f"LiveStatusCard error: {e}")
            self._display_status([("Status", "ERROR", ERROR_RED)])

    async def _update_status_async(self):
        """Handle async status callback."""
        try:
            status_items = await self.get_status_callback()
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self._display_status(status_items), 0)
        except Exception as e:
            print(f"LiveStatusCard async error: {e}")
            Clock.schedule_once(lambda dt: self._display_status([("Status", "ERROR", ERROR_RED)]), 0)

    def _display_status(self, status_items: List[Tuple[str, str, Tuple[float, float, float, float]]]):
        """Display status items in the UI."""
        # Clear existing items
        self.status_container.clear_widgets()

        # Add each status item as a row
        for label, value, color in status_items:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height="25dp",
                spacing="10dp"
            )

            # Label on left
            label_widget = MDLabel(
                text=label,
                size_hint_x=0.5,
                font_style='Body2'
            )
            row.add_widget(label_widget)

            # Value on right with colored text
            value_widget = MDLabel(
                text=value,
                size_hint_x=0.5,
                font_style='Body2',
                theme_text_color='Custom',
                text_color=color,
                halign='right'
            )
            row.add_widget(value_widget)

            self.status_container.add_widget(row)

    def on_pre_leave(self, *args):
        """Cancel scheduled updates when widget is removed."""
        if hasattr(self, '_update_event') and self._update_event:
            self._update_event.cancel()

    def cleanup(self):
        """Explicit cleanup method for manual cleanup."""
        if hasattr(self, '_update_event') and self._update_event:
            self._update_event.cancel()


class NumpadField(BoxLayout):
    """
    Convenience widget for numeric config fields.

    Displays current value and opens NumpadDialog on tap.
    Auto-saves to config and handles risky path confirmations.
    """

    def __init__(
        self,
        label: str,
        config_path: str,
        config_manager: ConfigManager,
        allow_decimal: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        on_value_changed: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        """
        Initialize numpad field.

        Args:
            label: Field label text
            config_path: Dot-notation config path (e.g., "hardware.modbus.port")
            config_manager: ConfigManager instance
            allow_decimal: Whether to allow decimal input
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            on_value_changed: Optional callback invoked after value changes
            **kwargs: Additional BoxLayout arguments
        """
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', "50dp")
        kwargs.setdefault('spacing', "10dp")

        super().__init__(**kwargs)

        self.label = label
        self.config_path = config_path
        self.config_manager = config_manager
        self.allow_decimal = allow_decimal
        self.min_value = min_value
        self.max_value = max_value
        self.on_value_changed = on_value_changed

        # Get current value from config
        self.current_value = self._get_current_value()

        # Build UI
        self._build_ui()

    def _get_current_value(self) -> float:
        """Get current value from config."""
        path_parts = self.config_path.split('.')
        current = self.config_manager.config.dict()

        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return 0.0

        return float(current) if current is not None else 0.0

    def _format_value(self, value: float) -> str:
        """Format value for display (int if no decimals allowed)."""
        if not self.allow_decimal and value == int(value):
            return str(int(value))
        return str(value)

    def _build_ui(self):
        """Build the field UI."""
        # Label on left
        label_widget = MDLabel(
            text=self.label,
            size_hint_x=0.6,
            font_style='Body1'
        )
        self.add_widget(label_widget)

        # Tappable value display on right (brighter for visibility)
        self.value_button = MDRaisedButton(
            text=self._format_value(self.current_value),
            size_hint_x=0.4,
            md_bg_color=INPUT_BUTTON,
            on_release=lambda x: self._open_numpad()
        )
        self.add_widget(self.value_button)

    def _open_numpad(self):
        """Open numpad dialog for input."""
        dialog = NumpadDialog(
            title=self.label,
            initial_value=self.current_value,
            min_value=self.min_value,
            max_value=self.max_value,
            allow_decimal=self.allow_decimal,
            on_submit=self._on_value_submitted
        )
        dialog.open()

    def _on_value_submitted(self, new_value: float):
        """Handle value submission from numpad."""
        # Update config
        success, needs_confirmation = update_config_value(
            self.config_manager,
            self.config_path,
            new_value
        )

        if success:
            if needs_confirmation:
                # Show confirmation dialog for risky paths
                show_confirm_dialog(
                    title="Confirmation Required",
                    text=f"Set {self.label} to {self._format_value(new_value)}?\n\nThis is a hardware-relevant setting.",
                    on_confirm=lambda: self._apply_value(new_value)
                )
            else:
                # Apply directly for non-risky paths
                self._apply_value(new_value)
        else:
            print(f"Failed to update config for {self.config_path}")

    def _apply_value(self, new_value: float):
        """Apply the new value and update display."""
        self.current_value = new_value
        self.value_button.text = self._format_value(new_value)

        # Invoke callback if provided
        if self.on_value_changed:
            self.on_value_changed(new_value)


class TextInputDialog:
    """
    Modal dialog with text input field.

    Used for string inputs like URLs, machine IDs, IP addresses.
    """

    def __init__(
        self,
        title: str,
        initial_value: str = "",
        hint_text: str = "",
        on_submit: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize text input dialog.

        Args:
            title: Dialog title text
            initial_value: Starting value to display
            hint_text: Placeholder hint text
            on_submit: Callback invoked with string value on OK
        """
        self.title = title
        self.initial_value = initial_value
        self.hint_text = hint_text
        self.on_submit = on_submit

        # Import here to avoid circular dependencies
        from kivymd.uix.textfield import MDTextField

        # Build dialog UI
        self._build_ui()

    def _build_ui(self):
        """Build the text input dialog UI."""
        from kivymd.uix.textfield import MDTextField

        # Text field for input
        self.text_field = MDTextField(
            text=self.initial_value,
            hint_text=self.hint_text,
            size_hint_y=None,
            height="50dp",
            multiline=False
        )

        # Create dialog with action buttons
        self.dialog = MDDialog(
            title=self.title,
            type="custom",
            content_cls=self.text_field,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: self._on_ok_pressed()
                ),
            ],
        )

    def _on_ok_pressed(self):
        """Handle OK button press."""
        value = self.text_field.text.strip()

        # Invoke callback with value
        if self.on_submit:
            self.on_submit(value)

        self.dialog.dismiss()

    def open(self):
        """Open the dialog."""
        self.dialog.open()
