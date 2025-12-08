#!/usr/bin/env python3
"""
Quick test script for RS485 Modbus relay board.

Tests communication with the relay board to verify RS485 connection.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from monitoni.hardware.modbus_relay import ModbusRelayController

async def test_relay():
    """Test relay board communication."""
    
    # Try different ports
    ports_to_try = ['/dev/ttyAMA0', '/dev/ttyAMA10', '/dev/ttyUSB0']
    
    for port in ports_to_try:
        print(f"\n{'='*50}")
        print(f"Testing port: {port}")
        print('='*50)
        
        try:
            controller = ModbusRelayController(
                port=port,
                baudrate=9600,
                slave_address=1,
                timeout=1.0
            )
            
            connected = await controller.connect()
            
            if connected:
                print(f"✓ Connected to relay board on {port}")
                
                # Test relay 1 ON/OFF
                print("\nTesting Relay 1...")
                
                print("  → Turning ON relay 1")
                result = await controller.set_relay(1, True)
                print(f"  Result: {'Success' if result else 'Failed'}")
                
                await asyncio.sleep(1)
                
                print("  → Turning OFF relay 1")
                result = await controller.set_relay(1, False)
                print(f"  Result: {'Success' if result else 'Failed'}")
                
                # Read relay state
                print("\n  → Reading relay 1 state")
                state = await controller.get_relay(1)
                print(f"  State: {'ON' if state else 'OFF'}")
                
                await controller.disconnect()
                print(f"\n✓ Test complete on {port}")
                return True
                
            else:
                print(f"✗ Could not connect on {port}")
                if controller.last_error:
                    print(f"  Error: {controller.last_error}")
                    
        except Exception as e:
            print(f"✗ Error on {port}: {e}")
            
    print("\n" + "="*50)
    print("Could not connect to relay board on any port.")
    print("Please check:")
    print("  1. RS485 HAT is properly connected")
    print("  2. Relay board is powered on")
    print("  3. A/B wiring is correct (not swapped)")
    print("  4. Slave address is correct (default: 1)")
    print("="*50)
    return False

if __name__ == '__main__':
    print("RS485 Relay Board Test")
    print("="*50)
    result = asyncio.run(test_relay())
    sys.exit(0 if result else 1)
