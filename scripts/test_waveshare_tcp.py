#!/usr/bin/env python3
"""
Quick test for the first Waveshare 8-CH Ethernet relay module.

Target: 10.21.56.29:4196 (Waveshare default transparent TCP Server port).
- Toggles relay 1 ON for 1s, then OFF.
- Polls DI 0 (door sensor) for 10 seconds — open/close the door to see it flip.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoni.hardware.modbus_tcp_relay import EthernetRelayController
from monitoni.hardware.modbus_digital_input import ModbusDigitalInputController

HOST = "10.21.56.29"
PORT = 4196
SLAVE = 1
DI_INDEX = 0


async def test_relay():
    print(f"\n[Relay] Connecting to {HOST}:{PORT} ...")
    relay = EthernetRelayController(
        host=HOST, port=PORT, slave_address=SLAVE, timeout=2.0, max_channels=8
    )
    ok = await relay.connect()
    if not ok:
        print(f"  FAIL: {relay.last_error}")
        return False
    print("  Connected.")

    print("  -> Relay 1 ON")
    ok = await relay.set_relay(1, True)
    print(f"     {'OK' if ok else 'FAIL: ' + str(relay.last_error)}")
    await asyncio.sleep(1.0)

    print("  -> Relay 1 OFF")
    ok = await relay.set_relay(1, False)
    print(f"     {'OK' if ok else 'FAIL: ' + str(relay.last_error)}")

    await relay.disconnect()
    return True


async def test_door_sensor(seconds: int = 10):
    print(f"\n[DI] Reading DI {DI_INDEX} for {seconds}s "
          f"(open/close the door to see changes)...")
    di = ModbusDigitalInputController(
        host=HOST,
        port=PORT,
        slave_address=SLAVE,
        timeout=2.0,
        door_di_index=DI_INDEX,
        poll_interval_ms=0,  # we poll manually here
    )
    ok = await di.connect()
    if not ok:
        print(f"  FAIL: {di.last_error}")
        return False

    last = None
    for i in range(seconds * 5):  # poll every 200ms
        state = await di.read_digital_input(DI_INDEX)
        if state != last:
            label = "ACTIVE (door open)" if state else "inactive (door closed)"
            print(f"  t={i*0.2:4.1f}s  DI{DI_INDEX} = {state}  {label}")
            last = state
        await asyncio.sleep(0.2)

    await di.disconnect()
    return True


async def main():
    print("=" * 60)
    print(f"Waveshare Ethernet Relay Test  —  {HOST}:{PORT}")
    print("=" * 60)
    await test_relay()
    await test_door_sensor(seconds=10)
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
