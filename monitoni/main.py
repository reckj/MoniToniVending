"""
MoniToni Vending Machine System - Main Entry Point

Starts the vending machine application with hardware control and telemetry server.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoni.core.config import get_config_manager
from monitoni.core.logger import get_sync_logger, get_logger
from monitoni.core.database import get_database, close_database
from monitoni.hardware.manager import initialize_hardware, shutdown_hardware


async def main_async(args):
    """Async main function."""
    # Get logger
    logger = get_sync_logger()
    logger.info("=" * 60)
    logger.info("MoniToni Vending Machine System Starting")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config_manager = get_config_manager()
        config = config_manager.config
        logger.info(f"Machine ID: {config.system.machine_id}")
        logger.info(f"Mock mode: {args.mock}")
        
        # Initialize database
        logger.info("Initializing database...")
        db = await get_database()
        
        # Get async logger with database support
        logger = await get_logger()
        logger.info("Database initialized")
        
        # Initialize hardware
        logger.info("Initializing hardware...")
        hardware = await initialize_hardware(config, use_mock=args.mock)
        
        # Log hardware status
        status = hardware.get_status()
        logger.info("Hardware initialization complete:")
        for component, info in status['components'].items():
            logger.info(f"  {component}: {info['status']}")
            
        # Test hardware
        if args.test:
            logger.info("Running hardware tests...")
            await test_hardware(hardware, logger)
            
        # For now, just keep running
        logger.info("System ready. Press Ctrl+C to exit.")
        
        # TODO: Start UI and telemetry server here
        # For now, just wait
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
        
    finally:
        # Cleanup
        logger.info("Shutting down...")
        await shutdown_hardware()
        await close_database()
        logger.info("Shutdown complete")
        
    return 0


async def test_hardware(hardware, logger):
    """Run basic hardware tests."""
    logger.info("Testing relay controller...")
    if hardware.relay:
        # Test relay 1
        await hardware.relay.set_relay(1, True)
        await asyncio.sleep(0.5)
        await hardware.relay.set_relay(1, False)
        logger.info("  Relay test complete")
        
    logger.info("Testing LED controller...")
    if hardware.led:
        # Test colors
        await hardware.led.set_color(255, 0, 0, 0.5)  # Red
        await asyncio.sleep(1)
        await hardware.led.set_color(0, 255, 0, 0.5)  # Green
        await asyncio.sleep(1)
        await hardware.led.set_color(0, 0, 255, 0.5)  # Blue
        await asyncio.sleep(1)
        await hardware.led.turn_off()
        logger.info("  LED test complete")
        
    logger.info("Testing audio controller...")
    if hardware.audio:
        # Volume test
        await hardware.audio.set_volume(0.5)
        logger.info("  Audio test complete")
        
    logger.info("Testing sensor controller...")
    if hardware.sensor:
        door_state = await hardware.sensor.get_door_state()
        logger.info(f"  Door state: {'OPEN' if door_state else 'CLOSED'}")
        
    logger.info("All hardware tests complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MoniToni Vending Machine System"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock hardware implementations"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run hardware tests on startup"
    )
    
    args = parser.parse_args()
    
    # Run async main
    try:
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nShutdown requested")
        sys.exit(0)


if __name__ == "__main__":
    main()
