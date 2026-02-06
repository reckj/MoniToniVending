"""
Network settings screen for server configuration and connectivity.

Provides:
- Server URL and machine ID configuration
- Connection test with visual feedback
- WiFi status and IP address display
- Telemetry server information
- Reset to factory defaults
"""

import asyncio
import socket
import subprocess
import urllib.request
from typing import List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.switch import MDSwitch

from monitoni.core.config import ConfigManager
from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    NumpadField,
    TextInputDialog,
    update_config_value,
    reset_section_to_defaults,
    show_confirm_dialog,
    CORAL_ACCENT,
    NEAR_BLACK,
)


class NetworkSettingsScreen(BaseDebugSubScreen):
    """
    Network configuration and status screen.

    Allows operators to:
    - Configure purchase server URL and machine ID
    - Set polling intervals and timeouts
    - Test server connectivity
    - View WiFi and IP status
    - View telemetry configuration
    - Reset to factory defaults
    """

    def __init__(self, hardware, config_manager: ConfigManager, navigate_back=None, **kwargs):
        """
        Initialize network settings screen.

        Args:
            hardware: Hardware manager
            config_manager: Configuration manager
            navigate_back: Callback to return to menu
            **kwargs: Additional Screen arguments
        """
        self.hardware = hardware
        self.config_manager = config_manager
        self._network_status_event = None
        self._connection_test_running = False

        super().__init__(navigate_back=navigate_back, **kwargs)

        self.title = "Netzwerk"

        self._build_content()

        # Start network status polling
        self._network_status_event = Clock.schedule_interval(
            lambda dt: self._update_network_status(),
            5.0
        )
        # Update immediately
        self._update_network_status()

    def _build_content(self):
        """Build the network settings UI."""
        # Card 1: Server connection settings
        server_card = self._build_server_card()
        self.add_content(server_card)

        # Card 2: Connection test
        test_card = self._build_connection_test_card()
        self.add_content(test_card)

        # Card 3: Network status
        status_card = self._build_network_status_card()
        self.add_content(status_card)

        # Card 4: Telemetry info
        telemetry_card = self._build_telemetry_card()
        self.add_content(telemetry_card)

        # Reset button
        reset_button = self._build_reset_button()
        self.add_content(reset_button)

    def _build_server_card(self) -> SettingsCard:
        """Build server connection settings card."""
        card = SettingsCard(title="Server-Verbindung")

        # Server URL (tappable text field)
        url_row = self._build_text_field_row(
            label="Server-URL",
            config_path="purchase_server.base_url",
            hint="http://example.com"
        )
        card.add_content(url_row)

        # Machine ID (tappable text field)
        machine_id_row = self._build_text_field_row(
            label="Maschinen-ID",
            config_path="system.machine_id",
            hint="VM001"
        )
        card.add_content(machine_id_row)

        # Poll interval (numeric)
        poll_interval_field = NumpadField(
            label="Abfrage-Intervall (s)",
            config_path="purchase_server.poll_interval_s",
            config_manager=self.config_manager,
            allow_decimal=True,
            min_value=0.1,
            max_value=10.0
        )
        card.add_content(poll_interval_field)

        # Timeout (numeric)
        timeout_field = NumpadField(
            label="Timeout (s)",
            config_path="purchase_server.timeout_s",
            config_manager=self.config_manager,
            allow_decimal=True,
            min_value=1.0,
            max_value=30.0
        )
        card.add_content(timeout_field)

        # Retry attempts (numeric)
        retry_field = NumpadField(
            label="Wiederholungen",
            config_path="purchase_server.retry_attempts",
            config_manager=self.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=10
        )
        card.add_content(retry_field)

        # Server enabled toggle
        toggle_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        toggle_label = MDLabel(
            text="Server aktiviert",
            size_hint_x=0.7,
            font_style='Body1'
        )
        toggle_row.add_widget(toggle_label)

        server_toggle = MDSwitch(
            active=self.config_manager.config.purchase_server.enabled,
            size_hint_x=0.3
        )
        server_toggle.bind(active=self._on_server_enabled_changed)
        toggle_row.add_widget(server_toggle)

        card.add_content(toggle_row)

        return card

    def _build_text_field_row(self, label: str, config_path: str, hint: str = "") -> BoxLayout:
        """
        Build a row with label and tappable text field.

        Args:
            label: Field label
            config_path: Dot-notation config path
            hint: Hint text for dialog

        Returns:
            BoxLayout with label and button
        """
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="50dp",
            spacing="10dp"
        )

        # Label
        label_widget = MDLabel(
            text=label,
            size_hint_x=0.4,
            font_style='Body1'
        )
        row.add_widget(label_widget)

        # Get current value
        current_value = self._get_config_value(config_path)

        # Tappable value display
        value_button = MDRaisedButton(
            text=str(current_value),
            size_hint_x=0.6,
            md_bg_color=NEAR_BLACK,
            on_release=lambda x: self._open_text_dialog(
                label, config_path, hint, value_button
            )
        )
        row.add_widget(value_button)

        return row

    def _build_connection_test_card(self) -> SettingsCard:
        """Build connection test card."""
        card = SettingsCard(title="Verbindungs-Test")

        # Test button
        test_button = MDRaisedButton(
            text="Verbindung testen",
            size_hint_y=None,
            height="70dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._test_connection()
        )
        card.add_content(test_button)

        # Result display
        self.test_result_label = MDLabel(
            text="Bereit zum Testen",
            font_style='Body1',
            halign='center',
            size_hint_y=None,
            height="40dp"
        )
        card.add_content(self.test_result_label)

        return card

    def _build_network_status_card(self) -> SettingsCard:
        """Build network status card."""
        card = SettingsCard(title="Netzwerk-Status")

        # WiFi SSID
        self.wifi_label = MDLabel(
            text="WiFi: Lade...",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(self.wifi_label)

        # IP address
        self.ip_label = MDLabel(
            text="IP-Adresse: Lade...",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(self.ip_label)

        # Server URL
        server_url = self.config_manager.config.purchase_server.base_url
        server_label = MDLabel(
            text=f"Server: {server_url}",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(server_label)

        # Status
        self.network_status_label = MDLabel(
            text="Status: Unbekannt",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(self.network_status_label)

        return card

    def _build_telemetry_card(self) -> SettingsCard:
        """Build telemetry info card."""
        card = SettingsCard(title="Telemetrie")

        # Telemetry port
        port = self.config_manager.config.telemetry.port
        port_label = MDLabel(
            text=f"Telemetrie-Port: {port}",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(port_label)

        # Debug PIN (masked with toggle to reveal)
        pin_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height="30dp",
            spacing="10dp"
        )

        self.pin_label = MDLabel(
            text="Debug-PIN: ****",
            font_style='Body2',
            size_hint_x=0.7
        )
        pin_row.add_widget(self.pin_label)

        reveal_btn = MDRaisedButton(
            text="Anzeigen",
            size_hint_x=0.3,
            md_bg_color=NEAR_BLACK,
            size_hint_y=None,
            height="30dp",
            on_release=lambda x: self._toggle_pin_visibility(x)
        )
        self._pin_revealed = False
        pin_row.add_widget(reveal_btn)

        card.add_content(pin_row)

        # Telemetry enabled
        enabled = self.config_manager.config.telemetry.enabled
        enabled_text = "JA" if enabled else "NEIN"
        enabled_label = MDLabel(
            text=f"Telemetrie aktiviert: {enabled_text}",
            font_style='Body2',
            size_hint_y=None,
            height="30dp"
        )
        card.add_content(enabled_label)

        return card

    def _build_reset_button(self) -> MDRaisedButton:
        """Build reset to defaults button."""
        return MDRaisedButton(
            text="Werkseinstellungen",
            size_hint_y=None,
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=lambda x: self._reset_to_defaults()
        )

    def _get_config_value(self, config_path: str) -> str:
        """Get a config value by dot-notation path."""
        path_parts = config_path.split('.')
        current = self.config_manager.config.dict()

        for part in path_parts:
            if part in current:
                current = current[part]
            else:
                return ""

        return str(current) if current is not None else ""

    def _open_text_dialog(self, title: str, config_path: str, hint: str, button):
        """Open text input dialog."""
        current_value = self._get_config_value(config_path)

        dialog = TextInputDialog(
            title=title,
            initial_value=current_value,
            hint_text=hint,
            on_submit=lambda value: self._on_text_submitted(config_path, value, button)
        )
        dialog.open()

    def _on_text_submitted(self, config_path: str, value: str, button):
        """Handle text input submission."""
        # Update config
        update_config_value(
            self.config_manager,
            config_path,
            value
        )

        # Update button display
        button.text = value

    def _on_server_enabled_changed(self, instance, value: bool):
        """Handle server enabled toggle change."""
        update_config_value(
            self.config_manager,
            "purchase_server.enabled",
            value
        )

    def _test_connection(self):
        """Test connection to purchase server."""
        if self._connection_test_running:
            return

        self._connection_test_running = True
        self.test_result_label.text = "Teste..."
        self.test_result_label.theme_text_color = 'Primary'

        # Run test in background thread
        asyncio.create_task(self._run_connection_test())

    async def _run_connection_test(self):
        """Run connection test asynchronously."""
        import time

        base_url = self.config_manager.config.purchase_server.base_url
        timeout = self.config_manager.config.purchase_server.timeout_s

        try:
            start_time = time.time()

            # Run HTTP request in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._http_get_request,
                base_url,
                timeout
            )

            elapsed = time.time() - start_time

            if response:
                # Success
                Clock.schedule_once(
                    lambda dt: self._display_test_result(
                        f"Verbunden - Server erreichbar ({elapsed:.2f}s)",
                        success=True
                    ),
                    0
                )
            else:
                # Failed
                Clock.schedule_once(
                    lambda dt: self._display_test_result(
                        "Fehler - Keine Antwort vom Server",
                        success=False
                    ),
                    0
                )

        except Exception as e:
            # Error
            Clock.schedule_once(
                lambda dt: self._display_test_result(
                    f"Fehler - {str(e)}",
                    success=False
                ),
                0
            )

        finally:
            self._connection_test_running = False

    def _http_get_request(self, url: str, timeout: float) -> bool:
        """
        Perform HTTP GET request.

        Args:
            url: URL to request
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except Exception:
            return False

    def _display_test_result(self, message: str, success: bool):
        """Display connection test result."""
        self.test_result_label.text = message
        self.test_result_label.theme_text_color = 'Custom'
        self.test_result_label.text_color = (0, 1, 0, 1) if success else (1, 0, 0, 1)

    def _update_network_status(self):
        """Update WiFi and IP status."""
        # Get WiFi SSID
        wifi_ssid = self._get_wifi_ssid()
        if wifi_ssid:
            self.wifi_label.text = f"WiFi: {wifi_ssid}"
        else:
            self.wifi_label.text = "WiFi: Nicht verbunden"

        # Get IP address
        ip_address = self._get_ip_address()
        if ip_address:
            self.ip_label.text = f"IP-Adresse: {ip_address}"
        else:
            self.ip_label.text = "IP: Nicht verfügbar"

        # Update network status based on connectivity
        if wifi_ssid and ip_address:
            self.network_status_label.text = "Status: Verbunden"
            self.network_status_label.theme_text_color = 'Custom'
            self.network_status_label.text_color = (0, 1, 0, 1)
        else:
            self.network_status_label.text = "Status: Getrennt"
            self.network_status_label.theme_text_color = 'Custom'
            self.network_status_label.text_color = (1, 0, 0, 1)

    def _get_wifi_ssid(self) -> str:
        """
        Get WiFi SSID using system command.

        Returns:
            WiFi SSID or empty string if not available
        """
        try:
            result = subprocess.run(
                ['iwgetid', '-r'],
                capture_output=True,
                text=True,
                timeout=2.0
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except Exception:
            pass

        return ""

    def _get_ip_address(self) -> str:
        """
        Get local IP address.

        Returns:
            IP address or empty string if not available
        """
        try:
            # Try to get IP by connecting to external host (doesn't actually connect)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # Connect to Google DNS (doesn't send data)
                s.connect(('8.8.8.8', 80))
                ip_address = s.getsockname()[0]
                return ip_address
            finally:
                s.close()

        except Exception:
            pass

        # Fallback: try hostname resolution
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            if ip_address and ip_address != '127.0.0.1':
                return ip_address
        except Exception:
            pass

        return ""

    def _toggle_pin_visibility(self, button):
        """Toggle debug PIN visibility."""
        if self._pin_revealed:
            # Hide PIN
            self.pin_label.text = "Debug-PIN: ****"
            button.text = "Anzeigen"
            self._pin_revealed = False
        else:
            # Show PIN
            pin = self.config_manager.config.telemetry.debug_pin
            self.pin_label.text = f"Debug-PIN: {pin}"
            button.text = "Verbergen"
            self._pin_revealed = True

    def _reset_to_defaults(self):
        """Reset network settings to factory defaults."""
        show_confirm_dialog(
            title="Zurücksetzen bestätigen",
            text="Möchten Sie die Netzwerk-Einstellungen auf Werkseinstellungen zurücksetzen?",
            on_confirm=self._do_reset
        )

    def _do_reset(self):
        """Perform the reset to defaults."""
        # Reset both purchase_server and system sections
        success_ps = reset_section_to_defaults(
            self.config_manager,
            "purchase_server"
        )

        success_sys = reset_section_to_defaults(
            self.config_manager,
            "system"
        )

        if success_ps or success_sys:
            # Reload config would be automatic, UI will refresh on next interaction
            pass

    def on_pre_leave(self, *args):
        """Cancel network status polling when leaving screen."""
        if self._network_status_event:
            self._network_status_event.cancel()
            self._network_status_event = None
