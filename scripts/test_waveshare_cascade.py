#!/usr/bin/env python3
"""
Cascade test for second Waveshare relay module (output-only, 32 channels).

Target: 10.21.56.30:502, transparent RTU-over-TCP mode.
Turns each channel ON briefly, then OFF, in sequence 1..32.
Reports any channel that fails the ON or OFF command.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoni.hardware.modbus_tcp_relay import EthernetRelayController

HOST = "10.21.56.30"
PORT = 502
SLAVE = 1
CHANNELS = 32
ON_TIME = 0.15      # how long each relay stays on
GAP_TIME = 0.05     # pause after OFF before next channel


async def main():
    print("=" * 60)
    print(f"Cascade Test  —  {HOST}:{PORT}  —  channels 1..{CHANNELS}")
    print("=" * 60)

    relay = EthernetRelayController(
        host=HOST, port=PORT, slave_address=SLAVE,
        timeout=2.0, max_channels=CHANNELS,
    )
    if not await relay.connect():
        print(f"Connect FAIL: {relay.last_error}")
        sys.exit(1)
    print(f"Connected. Cascading {CHANNELS} channels "
          f"({ON_TIME*1000:.0f}ms on, {GAP_TIME*1000:.0f}ms gap)...\n")

    failures = []
    try:
        for ch in range(1, CHANNELS + 1):
            ok_on = await relay.set_relay(ch, True)
            await asyncio.sleep(ON_TIME)
            ok_off = await relay.set_relay(ch, False)
            await asyncio.sleep(GAP_TIME)

            if ok_on and ok_off:
                print(f"  ch{ch:2d}  OK")
            else:
                err = relay.last_error or "unknown"
                print(f"  ch{ch:2d}  FAIL  on={ok_on} off={ok_off}  err={err}")
                failures.append(ch)
    finally:
        # Belt-and-braces: force all off at the end
        await relay.set_all_relays(False)
        await relay.disconnect()

    print()
    if failures:
        print(f"FAILED channels: {failures}")
        sys.exit(1)
    print(f"All {CHANNELS} channels cycled successfully.")


if __name__ == "__main__":
    asyncio.run(main())
