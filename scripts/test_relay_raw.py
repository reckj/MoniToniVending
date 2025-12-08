#!/usr/bin/env python3
"""
Direct RS485 hex command test for Waveshare 32CH relay.

Sends raw hex commands exactly as documented by Waveshare.
"""

import serial
import time

# Configuration - try different ports
# RS232-RS485-CAN Board uses SC16IS752 SPI-to-UART chip -> /dev/ttySC0, /dev/ttySC1
ports_to_try = ['/dev/ttySC0', '/dev/ttySC1', '/dev/ttyAMA0']
baudrate = 9600

# Waveshare 32CH relay commands (from their wiki)
COMMANDS = {
    'relay0_on':  bytes.fromhex('01 05 00 00 FF 00 8C 3A'),
    'relay0_off': bytes.fromhex('01 05 00 00 00 00 CD CA'),
    'relay1_on':  bytes.fromhex('01 05 00 01 FF 00 DD FA'),
    'relay1_off': bytes.fromhex('01 05 00 01 00 00 9C 0A'),
    'all_on':     bytes.fromhex('01 05 00 FF FF 00 BC 0A'),
    'all_off':    bytes.fromhex('01 05 00 FF 00 00 FD FA'),
    'read_status': bytes.fromhex('01 01 00 00 00 08 3D CC'),
    'read_version': bytes.fromhex('01 03 80 00 00 01 AD CA'),
}

def test_port(port):
    """Test relay board on specific port."""
    print(f"\n{'='*60}")
    print(f"Testing port: {port}")
    print(f"Baudrate: {baudrate}")
    print('='*60)
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1.0  # 1 second timeout
        )
        
        print(f"✓ Serial port opened: {port}")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test 1: Read software version
        print("\n--- Test 1: Read Software Version ---")
        cmd = COMMANDS['read_version']
        print(f"Sending: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(0.2)
        response = ser.read(100)
        if response:
            print(f"Response: {response.hex(' ')}")
        else:
            print("No response (timeout)")
        
        # Test 2: Read relay status
        print("\n--- Test 2: Read Relay Status ---")
        cmd = COMMANDS['read_status']
        print(f"Sending: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(0.2)
        response = ser.read(100)
        if response:
            print(f"Response: {response.hex(' ')}")
        else:
            print("No response (timeout)")
        
        # Test 3: Turn Relay 0 ON
        print("\n--- Test 3: Relay 0 ON ---")
        cmd = COMMANDS['relay0_on']
        print(f"Sending: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(0.2)
        response = ser.read(100)
        if response:
            print(f"Response: {response.hex(' ')}")
            print("✓ Got response! Check if relay 0 clicked ON")
        else:
            print("No response (timeout)")
        
        print("\n>>> Did you hear relay 0 click? <<<")
        time.sleep(2)
        
        # Test 4: Turn Relay 0 OFF
        print("\n--- Test 4: Relay 0 OFF ---")
        cmd = COMMANDS['relay0_off']
        print(f"Sending: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(0.2)
        response = ser.read(100)
        if response:
            print(f"Response: {response.hex(' ')}")
        else:
            print("No response (timeout)")
        
        # Test 5: All relays ON briefly
        print("\n--- Test 5: ALL Relays ON (for 1 second) ---")
        cmd = COMMANDS['all_on']
        print(f"Sending: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(1)
        
        # Turn all off
        cmd = COMMANDS['all_off']
        print(f"Sending ALL OFF: {cmd.hex(' ')}")
        ser.write(cmd)
        time.sleep(0.2)
        response = ser.read(100)
        if response:
            print(f"Response: {response.hex(' ')}")
        else:
            print("No response")
        
        ser.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("Waveshare 32CH Relay - Direct Serial Test")
    print("="*60)
    
    for port in ports_to_try:
        try:
            if test_port(port):
                break
        except Exception as e:
            print(f"Could not test {port}: {e}")
    
    print("\n" + "="*60)
    print("Test complete.")
    print("\nIf no responses received and no clicks heard:")
    print("  1. Try swapping A/B wires (RS485 polarity)")
    print("  2. Check power to relay board")
    print("  3. Make sure RS485 HAT is enabled in config.txt")
    print("="*60)

if __name__ == '__main__':
    main()
