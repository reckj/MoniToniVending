#!/usr/bin/env python3
"""
Comprehensive LED testing script for WLED controller via ArtNet.

This script tests all LED functionality including:
- Connection and initialization
- Zone control
- Animations (rainbow, breathing, flash, etc.)
- Brightness control
- Individual pixel control

Usage:
    # Test with real hardware (specify WLED IP)
    python scripts/test_led.py --ip 192.168.1.100

    # Test with mock
    python scripts/test_led.py --mock

    # Interactive mode
    python scripts/test_led.py --ip 192.168.1.100 --interactive
"""

import asyncio
import argparse
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, '.')

from monitoni.core.config import load_config
from monitoni.hardware.wled_controller import WLEDController, MockLEDController


class LEDTester:
    """Comprehensive LED testing class."""

    def __init__(self, controller):
        """Initialize tester with LED controller."""
        self.controller = controller

    async def test_connection(self) -> bool:
        """Test connection to WLED controller."""
        print("\n" + "="*60)
        print("TEST: Connection")
        print("="*60)

        print("Connecting to LED controller...")
        result = await self.controller.connect()

        if result:
            print("✓ Connection successful")
            status = self.controller.get_status()
            print(f"  Status: {status}")
            return True
        else:
            print("✗ Connection failed")
            print(f"  Error: {self.controller.last_error}")
            return False

    async def test_solid_colors(self):
        """Test solid color output."""
        print("\n" + "="*60)
        print("TEST: Solid Colors")
        print("="*60)

        colors = [
            ("Red", 255, 0, 0),
            ("Green", 0, 255, 0),
            ("Blue", 0, 0, 255),
            ("White", 255, 255, 255),
            ("Yellow", 255, 255, 0),
            ("Cyan", 0, 255, 255),
            ("Magenta", 255, 0, 255),
        ]

        for name, r, g, b in colors:
            print(f"Setting {name} ({r}, {g}, {b})...")
            await self.controller.set_color(r, g, b, brightness=0.5)
            await asyncio.sleep(1.5)

        print("✓ Solid colors test complete")

    async def test_brightness(self):
        """Test brightness control."""
        print("\n" + "="*60)
        print("TEST: Brightness Control")
        print("="*60)

        print("Setting blue at different brightness levels...")

        # Fade in
        for brightness in [0.1, 0.3, 0.5, 0.7, 1.0]:
            print(f"  Brightness: {brightness:.1f}")
            await self.controller.set_color(0, 100, 255, brightness=brightness)
            await asyncio.sleep(1)

        # Fade out
        for brightness in [0.7, 0.5, 0.3, 0.1]:
            print(f"  Brightness: {brightness:.1f}")
            await self.controller.set_color(0, 100, 255, brightness=brightness)
            await asyncio.sleep(1)

        print("✓ Brightness test complete")

    async def test_zones(self):
        """Test zone control."""
        print("\n" + "="*60)
        print("TEST: Zone Control")
        print("="*60)

        zones_count = len(self.controller.zones)
        print(f"Testing {zones_count} zones...")

        # Clear all
        await self.controller.turn_off()
        await asyncio.sleep(0.5)

        # Light up each zone in sequence
        for zone_idx in range(zones_count):
            zone_start, zone_end = self.controller.zones[zone_idx]
            print(f"  Zone {zone_idx + 1}: Pixels {zone_start}-{zone_end} → Green")
            await self.controller.set_zone_color(zone_idx, 0, 255, 0, brightness=0.8)
            await asyncio.sleep(1.5)

        await asyncio.sleep(1)

        # Rainbow zones
        print("\nRainbow zones:")
        await self.controller.turn_off()
        await asyncio.sleep(0.5)

        colors = [
            (255, 0, 0),    # Red
            (255, 127, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (0, 255, 255),  # Cyan
            (0, 0, 255),    # Blue
            (127, 0, 255),  # Purple
            (255, 0, 255),  # Magenta
            (255, 192, 203),# Pink
            (255, 255, 255),# White
        ]

        for zone_idx in range(min(zones_count, len(colors))):
            r, g, b = colors[zone_idx]
            print(f"  Zone {zone_idx + 1} → RGB({r}, {g}, {b})")
            await self.controller.set_zone_color(zone_idx, r, g, b, brightness=0.6)

        await asyncio.sleep(3)
        print("✓ Zone test complete")

    async def test_animations(self):
        """Test animations."""
        print("\n" + "="*60)
        print("TEST: Animations")
        print("="*60)

        # Rainbow chase
        print("Animation: Rainbow Chase (5 seconds)...")
        await self.controller.play_animation("rainbow_chase")
        await asyncio.sleep(5)

        # Stop animation and clear
        await self.controller.turn_off()
        await asyncio.sleep(1)

        # Breathing
        print("Animation: Breathing Blue (8 seconds)...")
        animation_task = asyncio.create_task(self.controller._run_animation("breathing"))
        await asyncio.sleep(8)
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass

        await self.controller.turn_off()
        await asyncio.sleep(1)

        # Flash
        print("Animation: Flash Red (3 flashes)...")
        await self.controller.play_animation("flash")
        await asyncio.sleep(2)

        print("✓ Animation test complete")

    async def test_pixel_control(self):
        """Test individual pixel control."""
        print("\n" + "="*60)
        print("TEST: Individual Pixel Control")
        print("="*60)

        # Clear
        await self.controller.turn_off()
        await asyncio.sleep(0.5)

        # Light up pixels in blocks
        print("Lighting up pixels in blocks of 10...")
        for start_pixel in range(0, min(100, self.controller.pixel_count), 10):
            end_pixel = start_pixel + 9
            print(f"  Pixels {start_pixel}-{end_pixel} → White")
            await self.controller.set_zone_pixels(start_pixel, end_pixel, 255, 255, 255, brightness=0.5)
            await asyncio.sleep(0.3)

        await asyncio.sleep(2)
        print("✓ Pixel control test complete")

    async def test_zone_highlight(self):
        """Test zone highlighting (used in purchase flow)."""
        print("\n" + "="*60)
        print("TEST: Zone Highlighting (Purchase Flow Simulation)")
        print("="*60)

        # Set all to dim blue (idle state)
        print("Setting idle state (dim blue)...")
        await self.controller.set_color(0, 50, 100, brightness=0.3)
        await asyncio.sleep(2)

        # Simulate selecting each level
        for level in range(1, min(11, len(self.controller.zones) + 1)):
            zone_idx = level - 1
            print(f"\nSimulating level {level} selection:")

            # Highlight zone (green)
            print(f"  1. Highlight zone {level} (green)")
            await self.controller.set_zone_color(zone_idx, 0, 255, 0, brightness=1.0)
            await asyncio.sleep(2)

            # Flash for valid purchase
            print(f"  2. Valid purchase (flash green)")
            for _ in range(3):
                await self.controller.set_zone_color(zone_idx, 0, 255, 0, brightness=1.0)
                await asyncio.sleep(0.2)
                await self.controller.set_zone_color(zone_idx, 0, 255, 0, brightness=0.2)
                await asyncio.sleep(0.2)

            # Return to idle
            print(f"  3. Return to idle")
            await self.controller.set_color(0, 50, 100, brightness=0.3)
            await asyncio.sleep(1)

        print("✓ Zone highlighting test complete")

    async def interactive_mode(self):
        """Interactive testing mode."""
        print("\n" + "="*60)
        print("INTERACTIVE MODE")
        print("="*60)
        print("\nCommands:")
        print("  color <r> <g> <b> [brightness] - Set solid color")
        print("  zone <zone> <r> <g> <b> [brightness] - Set zone color")
        print("  pixel <start> <end> <r> <g> <b> [brightness] - Set pixel range")
        print("  rainbow - Rainbow chase animation")
        print("  breathing - Breathing animation")
        print("  flash - Flash animation")
        print("  off - Turn off all LEDs")
        print("  status - Show controller status")
        print("  quit - Exit")
        print()

        while True:
            try:
                cmd = input("LED> ").strip().split()
                if not cmd:
                    continue

                if cmd[0] == "quit":
                    break

                elif cmd[0] == "color":
                    r, g, b = int(cmd[1]), int(cmd[2]), int(cmd[3])
                    brightness = float(cmd[4]) if len(cmd) > 4 else 1.0
                    await self.controller.set_color(r, g, b, brightness)
                    print(f"Set color to RGB({r}, {g}, {b}) @ {brightness:.2f}")

                elif cmd[0] == "zone":
                    zone, r, g, b = int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4])
                    brightness = float(cmd[5]) if len(cmd) > 5 else 1.0
                    await self.controller.set_zone_color(zone, r, g, b, brightness)
                    print(f"Set zone {zone} to RGB({r}, {g}, {b}) @ {brightness:.2f}")

                elif cmd[0] == "pixel":
                    start, end, r, g, b = int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]), int(cmd[5])
                    brightness = float(cmd[6]) if len(cmd) > 6 else 1.0
                    await self.controller.set_zone_pixels(start, end, r, g, b, brightness)
                    print(f"Set pixels {start}-{end} to RGB({r}, {g}, {b}) @ {brightness:.2f}")

                elif cmd[0] == "rainbow":
                    await self.controller.play_animation("rainbow_chase")
                    print("Playing rainbow chase...")

                elif cmd[0] == "breathing":
                    task = asyncio.create_task(self.controller._run_animation("breathing"))
                    print("Playing breathing animation (will loop)...")

                elif cmd[0] == "flash":
                    await self.controller.play_animation("flash")
                    print("Playing flash animation...")

                elif cmd[0] == "off":
                    await self.controller.turn_off()
                    print("LEDs turned off")

                elif cmd[0] == "status":
                    status = self.controller.get_status()
                    print(f"Status: {status}")

                else:
                    print("Unknown command")

            except (ValueError, IndexError) as e:
                print(f"Error: {e}")
            except KeyboardInterrupt:
                print("\nExiting...")
                break

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "="*60)
        print("MONITONI LED COMPREHENSIVE TEST SUITE")
        print("="*60)

        # Connect
        if not await self.test_connection():
            print("\n✗ Connection failed. Aborting tests.")
            return False

        try:
            # Run all tests
            await self.test_solid_colors()
            await self.test_brightness()
            await self.test_zones()
            await self.test_animations()
            await self.test_pixel_control()
            await self.test_zone_highlight()

            # Final clear
            print("\nClearing LEDs...")
            await self.controller.turn_off()

            print("\n" + "="*60)
            print("✓ ALL TESTS PASSED")
            print("="*60)
            return True

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Disconnect
            print("\nDisconnecting...")
            await self.controller.disconnect()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LED testing script for WLED controller")
    parser.add_argument("--ip", type=str, help="WLED controller IP address")
    parser.add_argument("--mock", action="store_true", help="Use mock LED controller")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--config", type=str, help="Config file path (default: uses default config)")

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = load_config(args.config)
    else:
        config = load_config()

    # Create controller
    if args.mock:
        print("Using MOCK LED controller")
        controller = MockLEDController(
            pixel_count=config.hardware.wled.pixel_count,
            zones=config.led.zones
        )
    else:
        if args.ip:
            ip_address = args.ip
        else:
            ip_address = config.hardware.wled.ip_address

        print(f"Using REAL WLED controller at {ip_address}")
        controller = WLEDController(
            ip_address=ip_address,
            universe=config.hardware.wled.universe,
            pixel_count=config.hardware.wled.pixel_count,
            fps=config.hardware.wled.fps,
            zones=config.led.zones
        )

    # Create tester
    tester = LEDTester(controller)

    # Run tests
    if args.interactive:
        # Connect first
        if await tester.test_connection():
            await tester.interactive_mode()
            await controller.disconnect()
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
