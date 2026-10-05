#!/usr/bin/env python3
"""
Diagnose which Modbus address space the Waveshare DIs actually live in.

Phase 1 (one-shot): probe several addr+function_code combinations to find
                    which one returns a valid DI frame.
Phase 2 (poll):     continuously poll the working combo for 60s so the
                    user can move the door and watch the bits flip.
"""

import asyncio
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoni.hardware.modbus_utils import (
    modbus_crc,
    build_read_discrete_inputs_frame,
    build_read_coils_frame,
)

HOST = "10.21.56.29"
PORT = 502
SLAVE = 1
POLL_HZ = 5
DURATION_S = 60


def build_fc04_frame(slave: int, addr: int, count: int) -> bytes:
    """FC04 Read Input Registers."""
    payload = bytes([
        slave, 0x04,
        (addr >> 8) & 0xFF, addr & 0xFF,
        (count >> 8) & 0xFF, count & 0xFF,
    ])
    crc = modbus_crc(payload)
    return payload + bytes([crc & 0xFF, crc >> 8])


async def read_once(reader, writer, frame: bytes) -> bytes:
    writer.write(frame)
    await writer.drain()
    try:
        # Over-read — tolerate exception responses (5 bytes) or data (6-25 bytes)
        first = await asyncio.wait_for(reader.readexactly(3), timeout=1.5)
        # First 3 bytes: slave, fc, (byte_count OR exception_code)
        fc = first[1]
        if fc & 0x80:
            # Exception response: slave+fc+code+crc(2) = 5 bytes total, 2 more
            rest = await asyncio.wait_for(reader.readexactly(2), timeout=1.5)
            return first + rest
        # Normal response: byte_count is first[2]; need bc + 2 more bytes
        bc = first[2]
        rest = await asyncio.wait_for(reader.readexactly(bc + 2), timeout=1.5)
        return first + rest
    except asyncio.TimeoutError:
        return b""


async def main():
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(HOST, PORT), timeout=2.0
    )

    print("Phase 1: probing DI address spaces...\n")

    probes = [
        ("FC02 addr=0x0000 count=8",  build_read_discrete_inputs_frame(SLAVE, 0x0000, 8)),
        ("FC02 addr=0x0000 count=16", build_read_discrete_inputs_frame(SLAVE, 0x0000, 16)),
        ("FC02 addr=0x00C8 count=8",  build_read_discrete_inputs_frame(SLAVE, 0x00C8, 8)),
        ("FC02 addr=0x0100 count=8",  build_read_discrete_inputs_frame(SLAVE, 0x0100, 8)),
        ("FC02 addr=0x1000 count=8",  build_read_discrete_inputs_frame(SLAVE, 0x1000, 8)),
        ("FC01 addr=0x0000 count=8",  build_read_coils_frame(SLAVE, 0x0000, 8)),
        ("FC01 addr=0x00FF count=8",  build_read_coils_frame(SLAVE, 0x00FF, 8)),
        ("FC04 addr=0x0000 count=1",  build_fc04_frame(SLAVE, 0x0000, 1)),
    ]

    workers = []
    for label, frame in probes:
        resp = await read_once(reader, writer, frame)
        if not resp:
            print(f"  {label:38s}  → timeout / no response")
            continue
        fc = resp[1]
        if fc & 0x80:
            print(f"  {label:38s}  → exception fc=0x{fc:02X} code={resp[2]}")
            continue
        bc = resp[2]
        data = resp[3:3 + bc]
        print(f"  {label:38s}  → OK bc={bc} data={data.hex()}")
        if fc in (0x01, 0x02) and bc >= 1:
            workers.append((label, frame, data[0]))

    if not workers:
        print("\nNo working DI read found. Giving up.")
        writer.close(); await writer.wait_closed()
        return

    # Prefer FC02 at 0x0000 if available, else first worker
    label, frame, first_byte = workers[0]
    for lb, fr, fb in workers:
        if "FC02 addr=0x0000 count=8" in lb:
            label, frame, first_byte = lb, fr, fb
            break

    print(f"\nPhase 2: polling '{label}' for {DURATION_S}s — move the door NOW.\n")
    last = None
    try:
        for i in range(DURATION_S * POLL_HZ):
            resp = await read_once(reader, writer, frame)
            if not resp or (resp[1] & 0x80):
                continue
            bc = resp[2]
            data = resp[3:3 + bc]
            # Pretty-print as DI0..DI(bc*8-1), low bit first
            bits = "".join(f"{b:08b}"[::-1] for b in data)
            if bits != last:
                t = i / POLL_HZ
                labelled = " ".join(f"DI{n}={bits[n]}" for n in range(min(8, len(bits))))
                print(f"  t={t:5.1f}s  raw={data.hex()}  {labelled}")
                last = bits
            await asyncio.sleep(1 / POLL_HZ)
    finally:
        writer.close()
        await writer.wait_closed()
        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
