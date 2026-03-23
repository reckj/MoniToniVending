"""
Modbus RTU over TCP digital input controller for Waveshare Ethernet relay modules.

Reads discrete digital inputs (DI) using Modbus FC02 over a persistent TCP connection.
Designed for Waveshare 8-CH Module C which provides both relay outputs and DI ports.

Uses same transparent-mode TCP pattern as EthernetRelayController:
raw Modbus RTU frames (with CRC) over TCP — NOT MBAP headers, NOT pymodbus.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from monitoni.hardware.base import DigitalInputController, HardwareStatus
from monitoni.hardware.modbus_utils import build_read_discrete_inputs_frame

logger = logging.getLogger(__name__)

# Reconnect backoff schedule (seconds) — same as EthernetRelayController
RECONNECT_BACKOFF = [2, 5, 10, 30]


class ModbusDigitalInputController(DigitalInputController):
    """
    Modbus FC02 digital input reader over TCP.

    Connects to Waveshare Ethernet relay module DI ports via TCP transparent mode.
    Polls the configured DI channel at a fixed interval and fires the door callback
    on state change.

    Features:
    - Persistent TCP connection with asyncio.open_connection
    - Per-controller asyncio.Lock
    - Background poll loop (configurable interval)
    - Background reconnect task with exponential backoff
    - No command retry on failure (safety: avoids double-firing)
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        slave_address: int = 1,
        timeout: float = 1.0,
        door_di_index: int = 0,
        poll_interval_ms: int = 150,
    ):
        """
        Initialize Modbus digital input controller.

        Args:
            host: TCP host (IP address) of the relay/DI module
            port: TCP port (default 502)
            slave_address: Modbus slave address
            timeout: Connection and read timeout in seconds
            door_di_index: DI channel index (0-indexed) mapped to door sensor
            poll_interval_ms: How often to poll DI state (0 = disable polling)
        """
        super().__init__("ModbusDigitalInput", door_di_index=door_di_index)
        self.host = host
        self.port = port
        self.slave_address = slave_address
        self.timeout = timeout
        self.poll_interval_ms = poll_interval_ms

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._poll_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._stop_reconnect = False
        self._last_door_state: Optional[bool] = None

    async def connect(self) -> bool:
        """
        Connect to the module via TCP and start polling loop.

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
            logger.info(
                f"ModbusDigitalInput connected to {self.host}:{self.port}"
            )

            # Start polling loop if interval is configured
            if self.poll_interval_ms > 0:
                self._poll_task = asyncio.create_task(self._poll_loop())

            return True

        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            self._reader = None
            self._writer = None
            logger.error(
                f"ModbusDigitalInput connect failed ({self.host}:{self.port}): {e}"
            )
            return False

    async def disconnect(self) -> None:
        """Stop polling, stop reconnect loop, and close TCP connection."""
        self._stop_reconnect = True
        await self.stop_reconnect_loop()

        # Stop poll loop
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._poll_task = None

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
        logger.info(f"ModbusDigitalInput disconnected from {self.host}:{self.port}")

    async def health_check(self) -> bool:
        """Check if TCP connection is alive."""
        return self.status == HardwareStatus.CONNECTED and self._writer is not None

    async def _send_frame(self, frame: bytes, response_length: int = 6) -> bytes:
        """
        Send a raw Modbus RTU frame and return the response.

        CRITICAL: Does NOT retry on failure. Returns b'' on any error.

        Args:
            frame: Complete Modbus RTU frame including CRC
            response_length: Expected response byte count (FC02 single-byte = 6)

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
                    self._reader.readexactly(response_length),
                    timeout=self.timeout,
                )
                return response

            except Exception as e:
                logger.error(
                    f"ModbusDigitalInput frame error ({self.host}:{self.port}): {e}"
                )
                self.last_error = str(e)
                self.status = HardwareStatus.ERROR
                self._reader = None
                self._writer = None
                return b""

    async def read_digital_input(self, di_index: int = 0) -> Optional[bool]:
        """
        Read a single digital input channel via FC02.

        FC02 response format (6 bytes for single-byte data):
          [slave_addr][0x02][byte_count][data_byte][crc_lo][crc_hi]

        The data byte is a bitmask: bit N = DI channel N.

        Args:
            di_index: DI channel index (0-indexed)

        Returns:
            True if DI is active, False if inactive, None on error
        """
        if not self.is_connected():
            return None

        # FC02: read 1 discrete input starting at di_index address
        frame = build_read_discrete_inputs_frame(self.slave_address, di_index, 1)
        # FC02 response for 1 DI = 6 bytes
        response = await self._send_frame(frame, response_length=6)

        if len(response) >= 4:
            data_byte = response[3]
            # The response data byte contains packed bits; for a single read at
            # di_index, the relevant bit is always bit 0 (since we requested 1 input)
            return bool(data_byte & 0x01)
        else:
            return None

    async def _poll_loop(self) -> None:
        """
        Background task: poll door DI channel at configured interval.

        On state change, calls the door callback if one is registered.
        """
        while True:
            try:
                if self.is_connected():
                    state = await self.read_digital_input(self._door_di_index)
                    if state is not None and state != self._last_door_state:
                        self._last_door_state = state
                        if self._door_callback is not None:
                            try:
                                self._door_callback(state)
                            except Exception as cb_err:
                                logger.error(
                                    f"ModbusDigitalInput door callback error: {cb_err}"
                                )

                await asyncio.sleep(self.poll_interval_ms / 1000.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ModbusDigitalInput poll loop error: {e}")
                await asyncio.sleep(self.poll_interval_ms / 1000.0)

    async def start_reconnect_loop(self) -> None:
        """
        Start background reconnect task.

        Only reconnects transport — never replays missed commands.
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
            if self.status not in (HardwareStatus.ERROR, HardwareStatus.DISCONNECTED):
                await asyncio.sleep(1.0)
                backoff_index = 0
                continue

            delay = RECONNECT_BACKOFF[min(backoff_index, len(RECONNECT_BACKOFF) - 1)]
            logger.info(
                f"ModbusDigitalInput reconnect attempt in {delay}s "
                f"({self.host}:{self.port})"
            )
            await asyncio.sleep(delay)

            if self._stop_reconnect:
                break

            success = await self.connect()
            if success:
                logger.info(
                    f"ModbusDigitalInput reconnected to {self.host}:{self.port}"
                )
                backoff_index = 0
            else:
                backoff_index += 1

    @property
    def connection_info(self) -> Dict[str, Any]:
        """
        Get connection details for UI display.

        Returns:
            Dictionary with host, port, status, last_error, poll_interval_ms, door_di_index
        """
        return {
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "last_error": self.last_error,
            "poll_interval_ms": self.poll_interval_ms,
            "door_di_index": self._door_di_index,
        }


class MockDigitalInputController(DigitalInputController):
    """
    Mock digital input controller for testing without hardware.

    Simulates 8 DI channels in memory. Matches the interface of
    MockSensorController for door state simulation.
    """

    def __init__(self, door_di_index: int = 0):
        """
        Initialize mock digital input controller.

        Args:
            door_di_index: DI channel index mapped to door sensor
        """
        super().__init__("MockDigitalInput", door_di_index=door_di_index)
        self._di_states: Dict[int, bool] = {i: False for i in range(8)}

    async def connect(self) -> bool:
        """Simulate successful connection."""
        await asyncio.sleep(0.01)
        self.status = HardwareStatus.CONNECTED
        self.last_error = None
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.status = HardwareStatus.DISCONNECTED

    async def health_check(self) -> bool:
        """Mock health check: always returns connected state."""
        return self.is_connected()

    async def read_digital_input(self, di_index: int = 0) -> Optional[bool]:
        """
        Read from in-memory DI state.

        Args:
            di_index: DI channel index (0-7)

        Returns:
            Simulated DI state
        """
        if not self.is_connected():
            return None
        return self._di_states.get(di_index, False)

    async def simulate_di_change(self, di_index: int, state: bool) -> None:
        """
        Simulate a DI channel state change.

        Args:
            di_index: DI channel index (0-7)
            state: New state
        """
        self._di_states[di_index] = state

        # Fire door callback if this is the door DI and a callback is registered
        if di_index == self._door_di_index and self._door_callback is not None:
            self._door_callback(state)

    async def simulate_door_open(self) -> None:
        """Simulate door opening (sets door DI to True)."""
        await self.simulate_di_change(self._door_di_index, True)

    async def simulate_door_close(self) -> None:
        """Simulate door closing (sets door DI to False)."""
        await self.simulate_di_change(self._door_di_index, False)
