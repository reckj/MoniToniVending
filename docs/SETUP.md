# MoniToni Vending Machine System - Setup Guide

Complete installation and deployment guide for Raspberry Pi 5.

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Systemd Service Setup](#systemd-service-setup)
- [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### Required Components

- **Raspberry Pi 5** (8GB recommended)
- **Waveshare 7.9" HDMI Capacitive Touch Display** (400x1280)
- **Waveshare Isolated RS232/RS485/CAN Expansion Board**
- **Modbus RTU 32-Ch Relay Module** (RS485 Interface)
- **Gledopto ESP32 WLED Controller** (Elite 2D-EXMU with Ethernet)
- **Digital LED Strip** (WS2812B or compatible, 300 LEDs)
- **Limit Switch Sensor** (for door monitoring)
- **MicroSD Card** (32GB minimum, Class 10)
- **Power Supply** (5V/5A USB-C for Raspberry Pi)

### Optional Components

- **Cooling Fan** for Raspberry Pi 5 (recommended for continuous operation)
- **Case** with proper ventilation

---

## Software Requirements

- **Operating System**: Raspberry Pi OS (64-bit) Bookworm or later
- **Python**: 3.11 or higher (included in Raspberry Pi OS)
- **Network**: Ethernet connection recommended

---

## Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportaudio2 \
    libgles2-mesa-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

# Enable I2C and SPI (if needed)
sudo raspi-config
# Navigate to: Interface Options -> Enable I2C, SPI
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/reckj/MoniToniVending.git
cd MoniToniVending
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Create Directory Structure

```bash
mkdir -p data logs assets/sounds
```

---

## Configuration

### 1. Create Local Configuration

```bash
cp config/local.yaml.example config/local.yaml
nano config/local.yaml
```

### 2. Configure Essential Settings

Edit `config/local.yaml`:

```yaml
system:
  machine_id: "VM001"  # Unique ID for this machine

hardware:
  wled:
    ip_address: "192.168.1.100"  # Your WLED controller IP
    
purchase_server:
  base_url: "http://your-server:5000"  # Your purchase server URL
  
telemetry:
  debug_pin: "your-secure-pin"  # Change this!
```

### 3. Hardware Configuration

#### Modbus Relay

Identify your RS485 serial port:

```bash
ls /dev/ttyUSB*
# or
ls /dev/ttyAMA*
```

Update in `config/local.yaml`:

```yaml
hardware:
  modbus:
    port: "/dev/ttyUSB0"  # Your serial port
```

#### WLED LED Controller

1. Configure WLED controller with static IP
2. Enable ArtNet in WLED settings
3. Update IP address in `config/local.yaml`

#### GPIO Door Sensor

Default configuration uses BCM pin 17. To change:

```yaml
hardware:
  gpio:
    door_sensor_pin: 17  # BCM pin number
```

### 4. Add Sound Files

Place sound files in `assets/sounds/`:

- `success.wav` - Valid purchase sound
- `error.wav` - Invalid purchase sound
- `alarm.wav` - Door alarm sound

Or update paths in `config/local.yaml`:

```yaml
audio:
  sounds:
    valid_purchase: "assets/sounds/your-success.wav"
    invalid_purchase: "assets/sounds/your-error.wav"
    door_alarm: "assets/sounds/your-alarm.wav"
```

---

## Running the System

### Development Mode (with mocks)

Test the system without physical hardware:

```bash
source venv/bin/activate
python -m monitoni.main --mock --test
```

### Production Mode

Run with real hardware:

```bash
source venv/bin/activate
python -m monitoni.main
```

### Command Line Options

- `--mock` - Use mock hardware implementations
- `--debug` - Enable debug logging
- `--test` - Run hardware tests on startup

---

## Systemd Service Setup

For automatic startup and management:

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/monitoni.service
```

Add the following content:

```ini
[Unit]
Description=MoniToni Vending Machine System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MoniToniVending
Environment="PATH=/home/pi/MoniToniVending/venv/bin"
ExecStart=/home/pi/MoniToniVending/venv/bin/python -m monitoni.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable monitoni.service

# Start service now
sudo systemctl start monitoni.service

# Check status
sudo systemctl status monitoni.service
```

### 3. Service Management Commands

```bash
# View logs
sudo journalctl -u monitoni.service -f

# Restart service
sudo systemctl restart monitoni.service

# Stop service
sudo systemctl stop monitoni.service

# Disable auto-start
sudo systemctl disable monitoni.service
```

---

## Display Configuration

### Auto-start on Boot (Kiosk Mode)

For production deployment, configure the display to auto-start:

```bash
# Edit autostart
mkdir -p ~/.config/lxsession/LXDE-pi
nano ~/.config/lxsession/LXDE-pi/autostart
```

Add:

```
@xset s off
@xset -dpms
@xset s noblank
@/home/pi/MoniToniVending/venv/bin/python -m monitoni.main
```

---

## Network Configuration

### Static IP (Recommended)

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:

```
interface eth0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Reboot to apply:

```bash
sudo reboot
```

---

## Troubleshooting

### Permission Issues

If you encounter permission errors with GPIO or serial ports:

```bash
# Add user to required groups
sudo usermod -a -G gpio,dialout,i2c,spi pi

# Logout and login again
```

### Modbus Connection Issues

```bash
# Check serial port permissions
ls -l /dev/ttyUSB0

# Test serial port
sudo apt install minicom
minicom -D /dev/ttyUSB0 -b 9600
```

### WLED Not Responding

1. Verify WLED controller is powered
2. Check network connectivity: `ping 192.168.1.100`
3. Access WLED web interface: `http://192.168.1.100`
4. Verify ArtNet is enabled in WLED settings

### Database Issues

```bash
# Check database file
ls -l data/monitoni.db

# Reset database (WARNING: deletes all data)
rm data/monitoni.db
python -m monitoni.main --mock  # Will recreate database
```

### Viewing Logs

```bash
# Application logs
tail -f logs/monitoni.log

# System service logs
sudo journalctl -u monitoni.service -f

# Database logs
python3 << EOF
import asyncio
from monitoni.core.database import get_database

async def view_logs():
    db = await get_database()
    logs = await db.get_logs(limit=50)
    for log in logs:
        print(f"{log['timestamp']} [{log['level']}] {log['message']}")

asyncio.run(view_logs())
EOF
```

### Performance Issues

```bash
# Monitor system resources
htop

# Check CPU temperature
vcgencmd measure_temp

# Monitor network
iftop
```

---

## Backup and Recovery

### Backup Configuration and Data

```bash
# Create backup directory
mkdir -p ~/backups

# Backup configuration
cp config/local.yaml ~/backups/local.yaml.backup

# Backup database
cp data/monitoni.db ~/backups/monitoni.db.backup

# Backup logs
tar -czf ~/backups/logs-$(date +%Y%m%d).tar.gz logs/
```

### Restore from Backup

```bash
# Restore configuration
cp ~/backups/local.yaml.backup config/local.yaml

# Restore database
cp ~/backups/monitoni.db.backup data/monitoni.db
```

---

## Updates and Maintenance

### Update System

```bash
cd ~/MoniToniVending
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart monitoni.service
```

### Clean Old Logs

Logs are automatically rotated. To manually clean:

```bash
# Remove old log files
find logs/ -name "*.log.*" -mtime +30 -delete

# Clean database logs (older than 30 days)
# This is done automatically by the system
```

---

## Security Considerations

1. **Change Default PIN**: Update `telemetry.debug_pin` in `config/local.yaml`
2. **Network Security**: Use firewall to restrict telemetry server access
3. **Regular Updates**: Keep system and dependencies updated
4. **Backup Regularly**: Automate backups of configuration and data

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/reckj/MoniToniVending/issues
- Documentation: See `docs/` directory

---

## Next Steps

After installation:
1. Read [SYSTEM.md](SYSTEM.md) for architecture details
2. Review [API.md](API.md) for telemetry server API
3. See [HARDWARE.md](HARDWARE.md) for wiring diagrams
4. Check [DEVELOPMENT.md](DEVELOPMENT.md) for development guide
