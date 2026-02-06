"""
Statistics and logs screen for viewing system metrics and log entries.

Provides:
- Counters display (purchases, errors, uptime)
- Log viewer with level filtering
- Log export to USB or local filesystem
- Refresh functionality for real-time updates
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem

from monitoni.core.config import ConfigManager
from monitoni.core.database import get_database, LogLevel
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    show_confirm_dialog,
    CORAL_ACCENT,
    NEAR_BLACK,
    ERROR_RED,
)


class StatsSettingsScreen(BaseDebugSubScreen):
    """
    Statistics and logs screen.

    Allows operators to:
    - View transaction counters
    - Browse logs with level filtering
    - Export logs to USB or local filesystem
    - Refresh data for real-time monitoring
    """

    def __init__(self, hardware, config_manager: ConfigManager, navigate_back=None, **kwargs):
        """
        Initialize stats screen.

        Args:
            hardware: Hardware manager (unused but kept for consistency)
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager

        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "Statistics & Logs"

        # Current filter state
        self.current_filter = "ALL"
        self.log_entries = []

        # UI references
        self.counters_label = None
        self.filter_buttons = {}
        self.log_list = None

        self._build_content()

        # Load initial data
        asyncio.create_task(self._load_all_data())

    def _build_content(self):
        """Build the stats screen UI."""
        # Card 1: Counters
        counters_card = self._build_counters_card()
        self.add_content(counters_card)

        # Card 2: Log viewer with filters
        log_viewer_card = self._build_log_viewer_card()
        self.add_content(log_viewer_card)

        # Card 3: Export options
        export_card = self._build_export_card()
        self.add_content(export_card)

    def _build_counters_card(self) -> SettingsCard:
        """Build counters display card."""
        card = SettingsCard(title="Counters")

        # Container for counter values
        self.counters_label = MDLabel(
            text="Loading statistics...",
            size_hint_y=None,
            height="150dp",
            font_style='Body1',
            markup=True
        )
        card.add_content(self.counters_label)

        # Refresh button
        refresh_btn = MDRaisedButton(
            text="Refresh",
            size_hint_y=None,
            height="50dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: asyncio.create_task(self._refresh_counters())
        )
        card.add_content(refresh_btn)

        return card

    def _build_log_viewer_card(self) -> SettingsCard:
        """Build log viewer card with filtering."""
        card = SettingsCard(title="Logs")

        # Filter buttons - 2 rows to fit 400px screen
        filter_row1 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="45dp",
            spacing="5dp"
        )
        filter_row2 = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="45dp",
            spacing="5dp"
        )

        filters_row1 = ["ALL", "INFO", "DEBUG"]
        filters_row2 = ["WARNING", "ERROR"]

        for filter_name in filters_row1:
            btn = MDRaisedButton(
                text=filter_name,
                size_hint=(1, 1),
                md_bg_color=CORAL_ACCENT if filter_name == "ALL" else NEAR_BLACK,
                on_release=lambda x, f=filter_name: self._on_filter_changed(f)
            )
            self.filter_buttons[filter_name] = btn
            filter_row1.add_widget(btn)

        for filter_name in filters_row2:
            btn = MDRaisedButton(
                text=filter_name,
                size_hint=(1, 1),
                md_bg_color=NEAR_BLACK,
                on_release=lambda x, f=filter_name: self._on_filter_changed(f)
            )
            self.filter_buttons[filter_name] = btn
            filter_row2.add_widget(btn)

        card.add_content(filter_row1)
        card.add_content(filter_row2)

        # Scrollable log list
        scroll = ScrollView(
            size_hint=(1, None),
            height="400dp"
        )

        self.log_list = MDList()
        scroll.add_widget(self.log_list)

        card.add_content(scroll)

        # Refresh logs button
        refresh_logs_btn = MDRaisedButton(
            text="Refresh",
            size_hint_y=None,
            height="50dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: asyncio.create_task(self._refresh_logs())
        )
        card.add_content(refresh_logs_btn)

        return card

    def _build_export_card(self) -> SettingsCard:
        """Build export options card."""
        card = SettingsCard(title="Export")

        # USB export button
        usb_btn = MDRaisedButton(
            text="Export Logs (USB)",
            size_hint_y=None,
            height="60dp",
            md_bg_color=NEAR_BLACK,
            on_release=lambda x: asyncio.create_task(self._export_to_usb())
        )
        card.add_content(usb_btn)

        # Local export button
        local_btn = MDRaisedButton(
            text="Export Logs (local)",
            size_hint_y=None,
            height="60dp",
            md_bg_color=NEAR_BLACK,
            on_release=lambda x: asyncio.create_task(self._export_to_local())
        )
        card.add_content(local_btn)

        return card

    async def _load_all_data(self):
        """Load both counters and logs."""
        await self._refresh_counters()
        await self._refresh_logs()

    async def _refresh_counters(self):
        """Refresh counter statistics."""
        try:
            db = await get_database()
            stats = await db.get_statistics()

            # Calculate uptime (from app start or system uptime)
            # For now, show a placeholder
            uptime_text = "N/A"

            # Get last error from logs
            error_logs = await db.get_logs(limit=1, level=LogLevel.ERROR)
            if error_logs:
                last_error = error_logs[0]
                last_error_text = f"{last_error['timestamp'][:19]} - {last_error['message']}"
            else:
                last_error_text = "No errors"

            counters_text = f"""[b]Successful Purchases:[/b] {stats.get('completed_purchases', 0)}
[b]Failed Purchases:[/b] {stats.get('failed_purchases', 0)}
[b]Network Errors:[/b] {stats.get('network_incidents', 0)}
[b]Server Errors:[/b] {stats.get('server_incidents', 0)}
[b]Uptime:[/b] {uptime_text}
[b]Last Error:[/b] {last_error_text}"""

            # Update label on main thread
            Clock.schedule_once(lambda dt: setattr(self.counters_label, 'text', counters_text), 0)

        except Exception as e:
            error_text = f"[color=#ff0000]Error loading statistics: {str(e)}[/color]"
            Clock.schedule_once(lambda dt: setattr(self.counters_label, 'text', error_text), 0)

    async def _refresh_logs(self):
        """Refresh log entries based on current filter."""
        try:
            db = await get_database()

            # Map filter to log level
            level = None
            if self.current_filter == "DEBUG":
                level = LogLevel.DEBUG
            elif self.current_filter == "INFO":
                level = LogLevel.INFO
            elif self.current_filter == "WARNING":
                level = LogLevel.WARNING
            elif self.current_filter == "ERROR":
                level = LogLevel.ERROR

            # Fetch logs
            logs = await db.get_logs(limit=200, level=level)
            self.log_entries = logs

            # Update UI on main thread
            Clock.schedule_once(lambda dt: self._display_logs(), 0)

        except Exception as e:
            print(f"Error loading logs: {e}")
            Clock.schedule_once(lambda dt: self._display_error_logs(str(e)), 0)

    def _display_logs(self):
        """Display log entries in the list."""
        # Clear existing items
        self.log_list.clear_widgets()

        if not self.log_entries:
            # No logs found
            item = OneLineListItem(text="No logs found")
            self.log_list.add_widget(item)
            return

        # Add each log entry with color coding
        for log in self.log_entries:
            # Format: [LEVEL] timestamp - message
            level = log['level']
            timestamp = log['timestamp'][:19] if log.get('timestamp') else 'N/A'
            message = log['message'][:100]  # Truncate long messages

            # Determine color based on level
            color = self._get_color_for_level(level)
            color_hex = self._rgba_to_hex(color)

            # Create formatted text
            text = f"[color={color_hex}][{level}] {timestamp} - {message}[/color]"

            item = OneLineListItem(
                text=text,
                markup=True
            )
            self.log_list.add_widget(item)

    def _display_error_logs(self, error_message: str):
        """Display error message in logs list."""
        self.log_list.clear_widgets()
        item = OneLineListItem(text=f"[color=#ff0000]Error: {error_message}[/color]", markup=True)
        self.log_list.add_widget(item)

    def _on_filter_changed(self, filter_name: str):
        """Handle filter button press."""
        # Update current filter
        self.current_filter = filter_name

        # Update button colors
        for name, btn in self.filter_buttons.items():
            if name == filter_name:
                btn.md_bg_color = CORAL_ACCENT
            else:
                btn.md_bg_color = NEAR_BLACK

        # Reload logs with new filter
        asyncio.create_task(self._refresh_logs())

    def _get_color_for_level(self, level: str) -> Tuple[float, float, float, float]:
        """Get color for log level."""
        if level == "ERROR" or level == "CRITICAL":
            return (1, 0.3, 0.3, 1)  # Red
        elif level == "WARNING":
            return (1, 0.6, 0, 1)  # Orange
        elif level == "INFO":
            return (0.3, 1, 0.3, 1)  # Green
        elif level == "DEBUG":
            return (0.6, 0.6, 0.6, 1)  # Gray
        else:
            return (1, 1, 1, 1)  # White

    def _rgba_to_hex(self, rgba: Tuple[float, float, float, float]) -> str:
        """Convert RGBA tuple to hex color string."""
        r, g, b, a = rgba
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    async def _export_to_usb(self):
        """Export logs to USB drive."""
        try:
            # Find USB mount point
            usb_path = self._find_usb_mount()

            if not usb_path:
                # No USB found
                Clock.schedule_once(
                    lambda dt: self._show_dialog(
                        "No USB Drive Found",
                        "Please insert a USB drive and try again."
                    ),
                    0
                )
                return

            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"monitoni_logs_{timestamp}.json"
            filepath = usb_path / filename

            # Export logs
            db = await get_database()
            await db.export_logs_to_json(str(filepath))

            # Show success dialog
            Clock.schedule_once(
                lambda dt: self._show_dialog(
                    "Export Successful",
                    f"Logs exported to:\n{filepath}"
                ),
                0
            )

        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._show_dialog(
                    "Export Failed",
                    f"Error: {str(e)}"
                ),
                0
            )

    async def _export_to_local(self):
        """Export logs to local filesystem."""
        try:
            # Create logs export directory
            export_dir = Path("logs")
            export_dir.mkdir(exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}.json"
            filepath = export_dir / filename

            # Export logs
            db = await get_database()
            await db.export_logs_to_json(str(filepath))

            # Show success dialog
            Clock.schedule_once(
                lambda dt: self._show_dialog(
                    "Export Successful",
                    f"Logs exported to:\n{filepath.absolute()}"
                ),
                0
            )

        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._show_dialog(
                    "Export Failed",
                    f"Error: {str(e)}"
                ),
                0
            )

    def _find_usb_mount(self) -> Path:
        """Find mounted USB drive path."""
        for base in [Path('/media'), Path('/mnt')]:
            if base.exists():
                for mount in base.iterdir():
                    if mount.is_dir() and os.access(str(mount), os.W_OK):
                        return mount
        return None

    def _show_dialog(self, title: str, text: str):
        """Show info dialog."""
        dialog = MDDialog(
            title=title,
            text=text,
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
        # No polling to cancel - all data loaded on-demand
        pass
