"""
Shared Modbus RTU frame utilities.

Provides CRC calculation and frame builders for Modbus RTU communication.
Used by both TCP (Ethernet) and serial (RS485) relay controllers.

Note: Waveshare transparent mode = raw Modbus RTU frames (with CRC) over TCP.
Do NOT use MBAP headers. Do NOT use pymodbus.
"""


def modbus_crc(data: bytes) -> int:
    """
    Calculate Modbus CRC16.

    Args:
        data: Raw bytes to compute CRC over (not including CRC bytes)

    Returns:
        CRC value as int (16-bit)
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_write_coil_frame(slave_address: int, channel: int, state: bool) -> bytes:
    """
    Build a Modbus FC05 (Write Single Coil) frame.

    Channel is 1-indexed externally; converted to 0-indexed coil address internally.

    Args:
        slave_address: Modbus slave address
        channel: Relay channel number (1-indexed)
        state: True for ON, False for OFF

    Returns:
        Complete 8-byte frame ready to send (includes CRC)
    """
    address = channel - 1  # Convert 1-indexed channel to 0-indexed coil address
    payload = bytes([
        slave_address,
        0x05,                           # FC05: Write Single Coil
        (address >> 8) & 0xFF,          # Address high byte
        address & 0xFF,                 # Address low byte
        0xFF if state else 0x00,        # Value high: 0xFF = ON, 0x00 = OFF
        0x00,                           # Value low (always 0 for FC05)
    ])
    crc = modbus_crc(payload)
    return payload + bytes([crc & 0xFF, crc >> 8])


def build_write_all_coils_frame(slave_address: int, state: bool) -> bytes:
    """
    Build a Modbus FC05 frame targeting the Waveshare all-relay special address (0x00FF).

    Used to turn all relays ON or OFF simultaneously.

    Args:
        slave_address: Modbus slave address
        state: True for all ON, False for all OFF

    Returns:
        Complete 8-byte frame ready to send (includes CRC)
    """
    payload = bytes([
        slave_address,
        0x05,                           # FC05: Write Single Coil
        0x00,                           # Address high byte
        0xFF,                           # Special address: all relays
        0xFF if state else 0x00,        # Value high: 0xFF = ON, 0x00 = OFF
        0x00,                           # Value low
    ])
    crc = modbus_crc(payload)
    return payload + bytes([crc & 0xFF, crc >> 8])


def build_read_coils_frame(slave_address: int, start_address: int, count: int) -> bytes:
    """
    Build a Modbus FC01 (Read Coils) frame.

    Args:
        slave_address: Modbus slave address
        start_address: Starting coil address (0-indexed)
        count: Number of coils to read

    Returns:
        Complete 8-byte frame ready to send (includes CRC)
    """
    payload = bytes([
        slave_address,
        0x01,                           # FC01: Read Coils
        (start_address >> 8) & 0xFF,    # Start address high byte
        start_address & 0xFF,           # Start address low byte
        (count >> 8) & 0xFF,            # Quantity high byte
        count & 0xFF,                   # Quantity low byte
    ])
    crc = modbus_crc(payload)
    return payload + bytes([crc & 0xFF, crc >> 8])


def build_read_discrete_inputs_frame(slave_address: int, start_address: int, count: int) -> bytes:
    """
    Build a Modbus FC02 (Read Discrete Inputs) frame.

    Used to read digital inputs (DI) on modules like the Waveshare 8-CH Module C.

    Args:
        slave_address: Modbus slave address
        start_address: Starting DI address (0-indexed)
        count: Number of discrete inputs to read

    Returns:
        Complete 8-byte frame ready to send (includes CRC)
    """
    payload = bytes([
        slave_address,
        0x02,                           # FC02: Read Discrete Inputs
        (start_address >> 8) & 0xFF,    # Start address high byte
        start_address & 0xFF,           # Start address low byte
        (count >> 8) & 0xFF,            # Quantity high byte
        count & 0xFF,                   # Quantity low byte
    ])
    crc = modbus_crc(payload)
    return payload + bytes([crc & 0xFF, crc >> 8])
