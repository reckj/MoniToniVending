---
created: 2026-02-06T20:30
title: Fix motor asyncio lock bound to different event loop
area: hardware
files:
  - monitoni/ui/debug_screen.py:39-50
---

## Problem

When pressing the turn button on the customer screen, motor operations fail with:

```
Motor start error: <asyncio.locks.Lock object at 0x7fffae5d4050 [unlocked, waiters:1]> is bound to a different event loop
Motor stop error: <asyncio.locks.Lock object at 0x7fffae5d4050 [unlocked, waiters:1]> is bound to a different event loop
```

The `asyncio.Lock` in the motor/relay code was created on one event loop but is being used from another. This happens because `debug_screen.py` has a `run_async()` helper that creates a new event loop in a thread (`asyncio.new_event_loop()`), but the Lock was likely created on the main Kivy async loop. The spindle lock opens successfully but motor start/stop fails.

Pre-existing bug, not introduced by Phase 4.

## Solution

TBD — likely needs one of:
1. Recreate the Lock on the correct event loop when motor operations run
2. Use a threading Lock instead of asyncio Lock for the motor since it's called cross-loop
3. Ensure all motor async operations run on the same event loop where the Lock was created
