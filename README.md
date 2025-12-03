# MoniToni Vending Machine System

A robust, production-ready vending machine control system designed for Raspberry Pi 5, featuring hardware control, telemetry monitoring, and remote management capabilities.

## Overview

MoniToni is a comprehensive vending machine system that provides:
- **Hardware Control**: Modbus RTU relay control, LED animations via WLED/ArtNet, GPIO sensors
- **User Interface**: KivyMD-based touchscreen interface for customers and setup/debug operations
- **Telemetry Server**: FastAPI-based monitoring and remote control
- **Reliability**: Watchdog timer, comprehensive logging, automatic recovery
- **Modularity**: Hardware abstraction layer for testing without physical hardware

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Raspberry Pi 5                         │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐       │
│  │  Vending Machine │      │ Telemetry Server │       │
│  │   Application    │◄────►│    (FastAPI)     │       │
│  │    (KivyMD)      │      │                  │       │
│  └────────┬─────────┘      └────────┬─────────┘       │
│           │                         │                  │
│           └────────┬────────────────┘                  │
│                    │                                   │
│           ┌────────▼─────────┐                         │
│           │  Hardware Layer  │                         │
│           │  (HAL + Drivers) │                         │
│           └────────┬─────────┘                         │
└────────────────────┼─────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼─────┐            ┌─────▼──────┐
   │ Modbus   │            │   WLED     │
   │ Relays   │            │ LED Strip  │
   └──────────┘            └────────────┘
```

## Features

### Vending Machine Application
- **Customer Interface**: Intuitive product selection and purchase flow
- **Debug/Setup Mode**: PIN-protected hardware testing and configuration
- **Sleep Mode**: Energy-saving mode with automatic wake-up
- **Door Monitoring**: Alarm system for unclosed doors
- **Purchase Flow**: Complete state machine with door lock/unlock control
- **Local Logging**: SQLite database for all events and errors

### Telemetry Server
- **Real-time Monitoring**: WebSocket-based status updates
- **Remote Control**: Debug commands and hardware testing
- **Log Management**: Download logs and view system statistics
- **Configuration**: Remote hardware configuration and setup
- **Web Frontend**: Browser-based telemetry dashboard

### Hardware Support
- **Modbus RTU**: 32-channel relay control for spindles and locks
- **WLED Integration**: ArtNet-based LED strip control with animations
- **GPIO Sensors**: Door status monitoring
- **Audio Feedback**: HDMI audio for user notifications
- **Watchdog Timer**: Automatic system recovery

## Quick Start

See [SETUP.md](docs/SETUP.md) for detailed installation and configuration instructions.

```bash
# Clone repository
git clone https://github.com/reckj/MoniToniVending.git
cd MoniToniVending

# Install dependencies
./scripts/setup.sh

# Configure system
cp config/default.yaml config/local.yaml
# Edit config/local.yaml with your settings

# Run in development mode (with hardware mocks)
python -m monitoni.main --mock

# Run on actual hardware
python -m monitoni.main
```

## Documentation

- [Setup Guide](docs/SETUP.md) - Installation and deployment
- [System Documentation](docs/SYSTEM.md) - Architecture and design
- [API Documentation](docs/API.md) - Telemetry server API reference
- [Hardware Configuration](docs/HARDWARE.md) - Hardware setup and wiring
- [Development Guide](docs/DEVELOPMENT.md) - Contributing and testing

## Project Structure

```
monitoni/
├── monitoni/              # Main application package
│   ├── core/             # Core infrastructure (config, database, logging)
│   ├── hardware/         # Hardware abstraction layer and drivers
│   ├── ui/               # KivyMD user interface
│   ├── telemetry/        # FastAPI telemetry server
│   └── main.py           # Application entry point
├── config/               # Configuration files
├── docs/                 # Documentation
├── scripts/              # Setup and deployment scripts
├── tests/                # Test suite
└── requirements.txt      # Python dependencies
```

## Requirements

- **Hardware**: Raspberry Pi 5 (8GB recommended)
- **OS**: Raspberry Pi OS (64-bit)
- **Python**: 3.11+
- **Display**: Waveshare 7.9" HDMI Capacitive Touch (400x1280)
- **Network**: Ethernet connection recommended

## License

[To be determined]

## Support

For issues and questions, please open an issue on GitHub.
