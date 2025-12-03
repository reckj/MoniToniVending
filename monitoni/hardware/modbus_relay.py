"""
Modbus RTU relay controller implementation.

Supports both real hardware (via pymodbus) and mock implementation.
"""

import asyncio
from typing import Optional, Dict
try:
    from pymodbus.client import AsyncModbusSerialClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False

from monitoni.hardware.base import RelayController, HardwareStatus


class ModbusRelayController(RelayController):
    """
    Real Modbus RTU relay controller.
    
    Controls 32-channel relay board via RS485/Modbus RTU.
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
            port: Serial port (e.g., /dev/ttyUSB0)
            baudrate: Baud rate
            slave_address: Modbus slave address
            timeout: Communication timeout
        """
        super().__init__("ModbusRelay")
        
        if not MODBUS_AVAILABLE:
            raise ImportError("pymodbus not available. Install with: pip install pymodbus")
            
        self.port = port
        self.baudrate = baudrate
        self.slave_address = slave_address
        self.timeout = timeout
        
        self.client: Optional[AsyncModbusSerialClient] = None
        self._relay_states: Dict[int, bool] = {}  # Cache relay states
        
    async def connect(self) -> bool:
        """Connect to Modbus device."""
        try:
            self.status = HardwareStatus.CONNECTING
            
            self.client = AsyncModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            await self.client.connect()
            
            if self.client.connected:
                self.status = HardwareStatus.CONNECTED
                self.last_error = None
                
                # Initialize all relays to OFF
                await self.set_all_relays(False)
                
                return True
            else:
                self.status = HardwareStatus.ERROR
                self.last_error = "Failed to connect to Modbus device"
                return False
                
        except Exception as e:
            self.status = HardwareStatus.ERROR
            self.last_error = str(e)
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Modbus device."""
        if self.client:
            # Turn off all relays before disconnecting
            await self.set_all_relays(False)
            self.client.close()
            self.client = None
            
        self.status = HardwareStatus.DISCONNECTED
        
    async def health_check(self) -> bool:
        """Check Modbus connection health."""
        if not self.client or not self.client.connected:
            return False
            
        try:
            # Try to read a coil to verify connection
            result = await self.client.read_coils(0, 1, slave=self.slave_address)
            return not result.isError()
        except Exception:
            return False
            
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
            
        try:
            # Modbus coil address is channel - 1 (0-indexed)
            address = channel - 1
            
            result = await self.client.write_coil(
                address,
                state,
                slave=self.slave_address
            )
            
            if not result.isError():
                self._relay_states[channel] = state
                self.last_error = None
                return True
            else:
                self.last_error = f"Modbus error: {result}"
                return False
                
        except Exception as e:
            self.last_error = str(e)
            return False
            
    async def get_relay(self, channel: int) -> Optional[bool]:
        """Get relay state."""
        if not self.is_connected():
            return None
            
        if not 1 <= channel <= 32:
            return None
            
        # Return cached state if available
        if channel in self._relay_states:
            return self._relay_states[channel]
            
        try:
            address = channel - 1
            result = await self.client.read_coils(
                address,
                1,
                slave=self.slave_address
            )
            
            if not result.isError():
                state = result.bits[0]
                self._relay_states[channel] = state
                return state
            else:
                return None
                
        except Exception:
            return None
            
    async def set_all_relays(self, state: bool) -> bool:
        """Set all relays to same state."""
        if not self.is_connected():
            return False
            
        try:
            # Write all 32 coils at once
            values = [state] * 32
            
            result = await self.client.write_coils(
                0,
                values,
                slave=self.slave_address
            )
            
            if not result.isError():
                # Update cache
                for i in range(1, 33):
                    self._relay_states[i] = state
                self.last_error = None
                return True
            else:
                self.last_error = f"Modbus error: {result}"
                return False
                
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
