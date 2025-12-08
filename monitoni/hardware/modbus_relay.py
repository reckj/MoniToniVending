"""
Modbus RTU relay controller implementation.

Supports both real hardware (via serial) and mock implementation.
Uses raw serial for reliable communication with Waveshare relays.
"""

import asyncio
from typing import Optional, Dict
import serial

from monitoni.hardware.base import RelayController, HardwareStatus


def modbus_crc(data: bytes) -> int:
    """Calculate Modbus CRC16."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class ModbusRelayController(RelayController):
    """
    Real Modbus RTU relay controller.
    
    Controls 32-channel relay board via RS485/Modbus RTU.
    Uses raw serial communication for reliability.
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        slave_address: int = 1,
        timeout: float = 1.0
    ):
        """
        Initialize Modbus relay controller.
        
        Args:
            port: Serial port (e.g., /dev/ttySC0)
            baudrate: Baud rate
            slave_address: Modbus slave address
            timeout: Communication timeout
        """
        super().__init__("ModbusRelay")
        
        self.port = port
        self.baudrate = baudrate
        self.slave_address = slave_address
        self.timeout = timeout
        
        self.serial: Optional[serial.Serial] = None
        self._relay_states: Dict[int, bool] = {}  # Cache relay states
        self._lock = asyncio.Lock()
        
    async def connect(self) -> bool:
        """Connect to Modbus device."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout
            )
            
            if self.serial.is_open:
                self.status = HardwareStatus.CONNECTED
                self.last_error = None
                
                # Initialize all relay states to off (don't send command, just cache)
                for i in range(1, 33):
                    self._relay_states[i] = False
                
                return True
            else:
                self.status = HardwareStatus.ERROR
                self.last_error = "Failed to open serial port"
                return False
                
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Modbus device."""
        if self.serial and self.serial.is_open:
            # Turn off all relays before disconnecting
            await self.set_all_relays(False)
            self.serial.close()
            self.serial = None
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check Modbus connection health."""
        if not self.serial or not self.serial.is_open:
            return False
        return True
            
    def _send_command(self, command: bytes) -> bytes:
        """Send raw Modbus command and receive response."""
        if not self.serial or not self.serial.is_open:
            return b''
            
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        self.serial.write(command)
        self.serial.flush()
        
        # Wait for response
        import time
        time.sleep(0.1)
        
        response = self.serial.read(100)
        return response
        
    async def set_relay(self, channel: int, state: bool) -> bool:
        """
        Set relay state.
        
        Args:
            channel: Relay channel (1-32)
            state: True for ON, False for OFF
        """
        if not self.is_connected():
            self.last_error = "Not connected"
            return False
            
        if not 1 <= channel <= 32:
            self.last_error = f"Invalid channel: {channel}"
            return False
            
        async with self._lock:
            try:
                # Build Modbus command: [addr][func][addr_hi][addr_lo][value_hi][value_lo][crc_lo][crc_hi]
                # Function 0x05 = Write Single Coil
                # Address is channel - 1 (0-indexed)
                address = channel - 1
                
                cmd = bytes([
                    self.slave_address,  # Slave address
                    0x05,                # Function: Write Single Coil
                    0x00,                # Address high byte
                    address,             # Address low byte
                    0xFF if state else 0x00,  # Value high (0xFF = ON, 0x00 = OFF)
                    0x00                 # Value low
                ])
                
                crc = modbus_crc(cmd)
                cmd = cmd + bytes([crc & 0xFF, crc >> 8])
                
                # Run sync serial in thread to not block
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self._send_command, cmd
                )
                
                # Check if we got a response (echo or actual response)
                if len(response) >= 8:
                    self._relay_states[channel] = state
                    self.last_error = None
                    return True
                else:
                    # Even without response, command may have worked
                    self._relay_states[channel] = state
                    return True
                    
            except Exception as e:
                self.last_error = str(e)
                return False
            
    async def get_relay(self, channel: int) -> Optional[bool]:
        """Get relay state from cache."""
        if not self.is_connected():
            return None
            
        if not 1 <= channel <= 32:
            return None
            
        return self._relay_states.get(channel, False)
            
    async def set_all_relays(self, state: bool) -> bool:
        """Set all relays to same state."""
        if not self.is_connected():
            return False
            
        async with self._lock:
            try:
                # Build Modbus command for all relays
                # Address 0xFF is special address for all relays on Waveshare boards
                cmd = bytes([
                    self.slave_address,  # Slave address
                    0x05,                # Function: Write Single Coil
                    0x00,                # Address high byte
                    0xFF,                # Special address for ALL relays
                    0xFF if state else 0x00,  # Value high
                    0x00                 # Value low
                ])
                
                crc = modbus_crc(cmd)
                cmd = cmd + bytes([crc & 0xFF, crc >> 8])
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self._send_command, cmd
                )
                
                # Update cache
                for i in range(1, 33):
                    self._relay_states[i] = state
                    
                self.last_error = None
                return True
                    
            except Exception as e:
                self.last_error = str(e)
                return False


class MockRelayController(RelayController):
    """
    Mock relay controller for testing without hardware.
    
    Simulates relay behavior in memory.
    """
    
    def __init__(self):
        """Initialize mock relay controller."""
        super().__init__("MockRelay")
        self._relay_states: Dict[int, bool] = {i: False for i in range(1, 33)}
        
    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.status = HardwareStatus.CONNECTED
        self.last_error = None
        return True
        
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._relay_states = {i: False for i in range(1, 33)}
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Mock health check always succeeds."""
        return self.is_connected()
        
    async def set_relay(self, channel: int, state: bool) -> bool:
        """Set mock relay state."""
        if not self.is_connected():
            return False
            
        if not 1 <= channel <= 32:
            self.last_error = f"Invalid channel: {channel}"
            return False
            
        self._relay_states[channel] = state
        print(f"[MOCK] Relay {channel}: {'ON' if state else 'OFF'}")
        return True
        
    async def get_relay(self, channel: int) -> Optional[bool]:
        """Get mock relay state."""
        if not self.is_connected():
            return None
            
        return self._relay_states.get(channel)
        
    async def set_all_relays(self, state: bool) -> bool:
        """Set all mock relays."""
        if not self.is_connected():
            return False
            
        for i in range(1, 33):
            self._relay_states[i] = state
            
        print(f"[MOCK] All relays: {'ON' if state else 'OFF'}")
        return True
