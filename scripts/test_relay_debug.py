#!/usr/bin/env python3
"""
Enhanced RS485 relay test - pymodbus 3.x compatible.

Tests Modbus RTU communication with various settings.
"""

import asyncio
import sys
sys.path.insert(0, '.')

async def test_relay_detailed():
    """Test relay board with detailed debugging."""
    from pymodbus.client import AsyncModbusSerialClient
    
    port = '/dev/ttyAMA0'
    baudrate = 9600
    slave_address = 1
    
    print("RS485 Relay Board Debug Test (pymodbus 3.x)")
    print("="*60)
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Slave Address: {slave_address}")
    print("="*60)
    
    # Try to connect
    client = AsyncModbusSerialClient(
        port=port,
        baudrate=baudrate,
        timeout=2.0,
        bytesize=8,
        parity='N',
        stopbits=1
    )
    
    await client.connect()
    
    if not client.connected:
        print("FAILED: Could not connect to serial port")
        return
        
    print("✓ Serial port connected")
    
    # Test 1: Read coils (to check if device responds)
    print("\n--- Test 1: Read Coils ---")
    try:
        # pymodbus 3.x uses 'slave' as positional or different name
        result = await client.read_coils(address=0, count=8, slave=slave_address)
        if result.isError():
            print(f"Read coils error: {result}")
        else:
            print(f"✓ Read coils: {result.bits[:8]}")
    except TypeError as e:
        # Try with unit= instead of slave= (pymodbus 3.x compatibility)
        print(f"Trying alternative API...")
        try:
            result = await client.read_coils(0, 8, unit=slave_address)
            if result.isError():
                print(f"Read coils error: {result}")
            else:
                print(f"✓ Read coils: {result.bits[:8]}")
        except Exception as e2:
            print(f"Exception: {e2}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Try direct call without slave parameter
    print("\n--- Test 2: Write Single Coil (Relay 1 ON) - no slave param ---")
    try:
        result = await client.write_coil(0, True)
        if result.isError():
            print(f"Write coil error: {result}")
        else:
            print(f"✓ Write coil success: {result}")
            print(">>> Did relay 1 click ON? (y/n)")
    except Exception as e:
        print(f"Exception: {e}")
    
    await asyncio.sleep(2)
    
    # Turn off
    print("\n--- Test 3: Write Single Coil (Relay 1 OFF) ---")
    try:
        result = await client.write_coil(0, False)
        if result.isError():
            print(f"Write coil error: {result}")
        else:
            print(f"✓ Write coil success: {result}")
            print(">>> Did relay 1 click OFF?")
    except Exception as e:
        print(f"Exception: {e}")
    
    await asyncio.sleep(1)
    
    # Test other relays
    print("\n--- Test 4: Testing relays 1-4 sequence ---")
    for i in range(4):
        try:
            print(f"  Relay {i+1} ON...")
            await client.write_coil(i, True)
            await asyncio.sleep(0.5)
            await client.write_coil(i, False)
            print(f"  Relay {i+1} OFF")
        except Exception as e:
            print(f"  Relay {i+1} error: {e}")
    
    client.close()
    print("\n" + "="*60)
    print("Test complete. Did any relays click during the test?")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(test_relay_detailed())
