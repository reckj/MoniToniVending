"""
Modbus RTU over TCP relay controller for Waveshare Ethernet relay modules.

Implements persistent TCP connection with background reconnect and per-controller
asyncio lock. Uses raw Modbus RTU frames (with CRC) — NOT MBAP headers, NOT pymodbus.

Waveshare transparent mode: TCP socket carries raw Modbus RTU frames including CRC.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from monitoni.hardware.base import RelayController, HardwareStatus
from monitoni.hardware.modbus_utils import (
    modbus_crc,
    build_write_coil_frame,
    build_write_all_coils_frame,
)

logger = logging.getLogger(__name__)

# Reconnect backoff schedule (seconds)
RECONNECT_BACKOFF = [2, 5, 10, 30]


class EthernetRelayController(RelayController):
    """
    Modbus RTU over TCP relay controller.

    Connects to Waveshare Ethernet relay modules operating in transparent mode,
    where raw Modbus RTU frames (including CRC) are sent directly over TCP.

    Features:
    - Persistent TCP connection with asyncio.open_connection
    - Per-controller asyncio.Lock for safe concurrent access
    - Background reconnect task with exponential backoff
    - No command retry on failure (safety: avoids double-firing coils)
    - In-memory relay state cache
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        slave_address: int = 1,
        timeout: float = 1.0,
        max_channels: int = 8,
    ):
        """
        Initialize Ethernet relay controller.

        Args:
            host: TCP host (IP address) of the relay module
            port: TCP port (default 502 for Modbus)
            slave_address: Modbus slave address
            timeout: Connection and read timeout in seconds
            max_channels: Number of relay channels on this module
        """
        super().__init__("EthernetRelay")
        self.host = host
        self.port = port
        self.slave_address = slave_address
        self.timeout = timeout
        self.max_channels = max_channels

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._relay_states: Dict[int, bool] = {}
        self._reconnect_task: Optional[asyncio.Task] = None
        self._stop_reconnect = False

    async def connect(self) -> bool:
        """
        Connect to the relay module via TCP.

        Returns:
            True if connection successful
        """
        try:
            self.status = HardwareStatus.CONNECTING
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            self.status = HardwareStatus.CONNECTED
            self.last_error = None
            logger.info(f"EthernetRelay connected to {self.host}:{self.port}")

            # Initialize cache: assume all relays off (do not send command)
            for i in range(1, self.max_channels + 1):
                self._relay_states[i] = False

            return True

        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            self._reader = None
            self._writer = None
            logger.error(f"EthernetRelay connect failed ({self.host}:{self.port}): {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from relay module and stop reconnect loop."""
        self._stop_reconnect = True
        await self.stop_reconnect_loop()

        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            finally:
                self._writer = None
                self._reader = None

        self.status = HardwareStatus.DISCONNECTED
        logger.info(f"EthernetRelay disconnected from {self.host}:{self.port}")

    async def health_check(self) -> bool:
        """Check if the TCP connection is alive."""
        return self.status == HardwareStatus.CONNECTED and self._writer is not None

    async def _send_frame(self, frame: bytes) -> bytes:
        """
        Send a raw Modbus RTU frame and return the response.

        CRITICAL: Does NOT retry on failure. Returns b'' on any error.
        Safety rationale: retrying a coil write could double-fire a relay.

        Args:
            frame: Complete Modbus RTU frame including CRC

        Returns:
            Response bytes, or b'' on error
        """
        async with self._lock:
            if self._writer is None or self._reader is None:
                return b""

            try:
                self._writer.write(frame)
                await self._writer.drain()

                response = await asyncio.wait_for(
                    self._reader.readexactly(8),
                    timeout=self.timeout,
                )
                return response

            except Exception as e:
                logger.error(f"EthernetRelay frame send error ({self.host}:{self.port}): {e}")
                self.last_error = str(e)
                self.status = HardwareStatus.ERROR
                self._reader = None
                self._writer = None
                return b""

    async def set_relay(self, channel: int, state: bool) -> bool:
        """
        Set a single relay channel state.

        Args:
            channel: Relay channel (1 to max_channels)
            state: True for ON, False for OFF

        Returns:
            True if command was accepted (response received)
        """
        if not self.is_connected():
            self.last_error = "Not connected"
            return False

        if not 1 <= channel <= self.max_channels:
            self.last_error = f"Invalid channel: {channel} (max {self.max_channels})"
            return False

        frame = build_write_coil_frame(self.slave_address, channel, state)
        response = await self._send_frame(frame)

        if len(response) >= 8:
            self._relay_states[channel] = state
            self.last_error = None
            return True
        else:
            self.last_error = "No response from relay module"
            return False

    async def get_relay(self, channel: int) -> Optional[bool]:
        """
        Get relay state from in-memory cache.

        Args:
            channel: Relay channel (1 to max_channels)

        Returns:
            Cached relay state, or None if not connected/invalid channel
        """
        if not self.is_connected():
            return None

        if not 1 <= channel <= self.max_channels:
            return None

        return self._relay_states.get(channel, False)

    async def set_all_relays(self, state: bool) -> bool:
        """
        Set all relay channels to the same state using the Waveshare special address (0x00FF).

        Args:
            state: True for all ON, False for all OFF

        Returns:
            True if command was accepted
        """
        if not self.is_connected():
            self.last_error = "Not connected"
            return False

        frame = build_write_all_coils_frame(self.slave_address, state)
        response = await self._send_frame(frame)

        if len(response) >= 8:
            for i in range(1, self.max_channels + 1):
                self._relay_states[i] = state
            self.last_error = None
            return True
        else:
            self.last_error = "No response from relay module"
            return False

    async def start_reconnect_loop(self) -> None:
        """
        Start background reconnect task.

        Only reconnects transport — never replays missed commands.
        Uses backoff schedule [2, 5, 10, 30] seconds.
        """
        self._stop_reconnect = False
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return  # Already running

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def stop_reconnect_loop(self) -> None:
        """Cancel the background reconnect task if running."""
        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        self._reconnect_task = None

    async def _reconnect_loop(self) -> None:
        """Background task: reconnect when status is ERROR or DISCONNECTED."""
        backoff_index = 0
        while not self._stop_reconnect:
            # Only attempt reconnect when we're not connected
            if self.status not in (HardwareStatus.ERROR, HardwareStatus.DISCONNECTED):
                await asyncio.sleep(1.0)
                backoff_index = 0  # Reset backoff when healthy
                continue

            delay = RECONNECT_BACKOFF[min(backoff_index, len(RECONNECT_BACKOFF) - 1)]
            logger.info(
                f"EthernetRelay reconnect attempt in {delay}s "
                f"({self.host}:{self.port})"
            )
            await asyncio.sleep(delay)

            if self._stop_reconnect:
                break

            success = await self.connect()
            if success:
                logger.info(f"EthernetRelay reconnected to {self.host}:{self.port}")
                backoff_index = 0
            else:
                backoff_index += 1

    @property
    def connection_info(self) -> Dict[str, Any]:
        """
        Get connection details for UI display.

        Returns:
            Dictionary with host, port, status, last_error
        """
        return {
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "last_error": self.last_error,
        }
