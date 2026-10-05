#!/usr/bin/env python3
"""
Test second Waveshare 8-CH Ethernet relay module in "Modbus TCP to RTU" mode.

Target: 10.21.56.30:502. In this mode the device expects standard Modbus TCP
frames (MBAP header, no CRC) — NOT the raw RTU-over-TCP frames the project's
EthernetRelayController sends. So we talk Modbus TCP directly here.

- Toggles relay 1 ON for 1s, then OFF (FC05 Write Single Coil).
- Polls DI 0 (door sensor) for 10s (FC02 Read Discrete Inputs).
"""

import asyncio
import struct
import sys

HOST = "10.21.56.30"
PORT = 502
UNIT_ID = 1          # Modbus slave / unit id
DI_INDEX = 0
TIMEOUT = 2.0


def mbap(tid: int, unit_id: int, pdu: bytes) -> bytes:
    """Wrap a Modbus PDU in an MBAP header."""
    # transaction_id(2), protocol_id=0(2), length=unit_id+pdu(2), unit_id(1)
    length = len(pdu) + 1
    return struct.pack(">HHHB", tid, 0, length, unit_id) + pdu


async def send(reader, writer, frame: bytes) -> bytes:
    """Send request and read response using MBAP length field."""
    writer.write(frame)
    await writer.drain()
    header = await asyncio.wait_for(reader.readexactly(7), timeout=TIMEOUT)
    # MBAP: tid(2) protocol(2) length(2) unit(1). length counts unit + PDU.
    length = struct.unpack(">H", header[4:6])[0]
    body = await asyncio.wait_for(reader.readexactly(length - 1), timeout=TIMEOUT)
    return header + body


def _check_exception(resp: bytes, expected_fc: int) -> str | None:
    """Return human-readable exception string, or None if normal."""
    fc = resp[7]
    if fc & 0x80:
        exc = resp[8] if len(resp) >= 9 else 0
        names = {
            1: "ILLEGAL FUNCTION", 2: "ILLEGAL DATA ADDRESS",
            3: "ILLEGAL DATA VALUE", 4: "SLAVE DEVICE FAILURE",
            11: "GATEWAY TARGET DEVICE FAILED TO RESPOND",
        }
        return f"exception fc=0x{fc:02X} code={exc} ({names.get(exc, '?')})"
    if fc != expected_fc:
        return f"unexpected fc=0x{fc:02X}"
    return None


async def write_coil(reader, writer, tid: int, channel: int, state: bool) -> bool:
    """FC05: write single coil. Channel is 1-indexed."""
    address = channel - 1
    pdu = struct.pack(">BHH", 0x05, address, 0xFF00 if state else 0x0000)
    resp = await send(reader, writer, mbap(tid, UNIT_ID, pdu))
    err = _check_exception(resp, 0x05)
    if err:
        print(f"         FC05 error: {err}")
        return False
    return True


async def read_di(reader, writer, tid: int, di_index: int) -> bool | None:
    """FC02: read 1 discrete input."""
    pdu = struct.pack(">BHH", 0x02, di_index, 1)
    resp = await send(reader, writer, mbap(tid, UNIT_ID, pdu))
    err = _check_exception(resp, 0x02)
    if err:
        print(f"  FC02 error: {err}")
        return None
    return bool(resp[9] & 0x01)


async def read_coil(reader, writer, tid: int, channel: int) -> bool | None:
    """FC01: read 1 coil (sanity-check for relay state readback)."""
    address = channel - 1
    pdu = struct.pack(">BHH", 0x01, address, 1)
    resp = await send(reader, writer, mbap(tid, UNIT_ID, pdu))
    err = _check_exception(resp, 0x01)
    if err:
        print(f"  FC01 error: {err}")
        return None
    return bool(resp[9] & 0x01)


async def main():
    print("=" * 60)
    print(f"Waveshare Modbus-TCP-to-RTU Test  —  {HOST}:{PORT}")
    print("=" * 60)

    print(f"\n[Connect] Opening TCP {HOST}:{PORT} ...")
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(HOST, PORT), timeout=TIMEOUT
        )
    except Exception as e:
        print(f"  FAIL: {e}")
        sys.exit(1)
    print("  Connected.")

    try:
        print("\n[Relay] -> Relay 1 ON")
        ok = await write_coil(reader, writer, tid=1, channel=1, state=True)
        print(f"         {'OK' if ok else 'FAIL'}")
        await asyncio.sleep(1.0)

        print("[Relay] -> Relay 1 OFF")
        ok = await write_coil(reader, writer, tid=2, channel=1, state=False)
        print(f"         {'OK' if ok else 'FAIL'}")

        print("\n[Sanity] Reading coil 1 state back via FC01")
        state = await read_coil(reader, writer, tid=3, channel=1)
        print(f"         coil1 = {state}")

        print(f"\n[DI] Reading DI {DI_INDEX} for 10s "
              f"(open/close the door to see changes)...")
        last = None
        tid = 10
        for i in range(50):  # 10s @ 200ms
            state = await read_di(reader, writer, tid, DI_INDEX)
            tid += 1
            if state != last:
                label = "ACTIVE (door open)" if state else "inactive (door closed)"
                print(f"  t={i*0.2:4.1f}s  DI{DI_INDEX} = {state}  {label}")
                last = state
            await asyncio.sleep(0.2)

    finally:
        writer.close()
        await writer.wait_closed()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
