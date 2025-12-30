# Remote Development Workflow

Guide for developing MoniToni on MacBook and testing on Raspberry Pi.

## Overview

This workflow allows you to:
- Develop code on your MacBook with mock hardware
- Test on actual Raspberry Pi hardware
- Sync code changes efficiently
- Remote debugging and monitoring

## Prerequisites

- MacBook with Git and Python 3.11+ installed
- Raspberry Pi 5 on the same network
- SSH access to the Pi

## Initial Setup

### 1. Set Up Raspberry Pi

Transfer the setup script to your Pi and run it:

```bash
# From MacBook, copy setup script to Pi
scp scripts/setup_pi.sh pi@<pi-ip-address>:~/

# SSH into Pi
ssh pi@<pi-ip-address>

# Clone the repository
cd ~
git clone https://github.com/reckj/MoniToniVending.git
cd MoniToniVending

# Run setup script
chmod +x scripts/setup_pi.sh
./scripts/setup_pi.sh
```

This script will:
- Install system dependencies
- Install Python packages
- Create config directories
- Optionally set up systemd service
- Configure touchscreen display

### 2. Configure Local Settings on Pi

Edit the hardware-specific configuration:

```bash
# On the Pi
cd ~/MoniToniVending
nano config/local.yaml
```

Update these settings for your hardware:
```yaml
hardware:
  modbus:
    port: /dev/ttySC0  # Your Modbus serial port
  wled:
    ip_address: 192.168.1.100  # Your WLED controller IP
  gpio:
    door_sensor_pin: 5  # Your door sensor GPIO pin

telemetry:
  debug_pin: "1234"  # Change from default PIN

database:
  path: /home/pi/MoniToniVending/data/monitoni.db
```

### 3. Set Up MacBook for Remote Development

On your MacBook, configure the workflow script:

```bash
# Make script executable
chmod +x scripts/dev_workflow.sh

# Set Pi connection details
export PI_USER=pi
export PI_HOST=<pi-ip-address>  # or monitoni-pi.local if mDNS works

# Optional: Add to ~/.zshrc or ~/.bashrc
echo 'export PI_HOST=<pi-ip-address>' >> ~/.zshrc
echo 'export PI_USER=pi' >> ~/.zshrc
```

### 4. Set Up Passwordless SSH (Recommended)

```bash
# From MacBook
./scripts/dev_workflow.sh setup-ssh

# Or manually
ssh-keygen -t rsa -b 4096  # If you don't have a key
ssh-copy-id pi@<pi-ip-address>
```

### 5. Configure VS Code Remote SSH (Optional but Recommended)

1. Install "Remote - SSH" extension in VS Code
2. Press `Cmd+Shift+P` → "Remote-SSH: Open SSH Configuration File"
3. Add this entry:

```
Host monitoni-pi
    HostName <pi-ip-address>
    User pi
    ForwardAgent yes
    ForwardX11 no
```

4. Connect: `Cmd+Shift+P` → "Remote-SSH: Connect to Host" → Select `monitoni-pi`

## Development Workflows

### Workflow A: Git-Based Development (Clean & Simple)

**Best for:** Official changes, feature development, collaboration

```bash
# On MacBook - Develop with mocks
python -m monitoni.main --mock

# Make changes, test locally
git add .
git commit -m "Update LED animations"
git push origin main

# On Pi - Pull and test
ssh pi@<pi-ip>
cd ~/MoniToniVending
git pull origin main
python -m monitoni.main  # Test with real hardware

# If changes needed, push from Pi
git add .
git commit -m "Fix hardware-specific timing"
git push origin main

# On MacBook - Pull changes back
git pull origin main
```

### Workflow B: Quick Iteration with Sync Script (Fast)

**Best for:** Rapid testing, hardware debugging, LED tweaking

```bash
# On MacBook - Use the workflow menu
./scripts/dev_workflow.sh

# Or use direct commands:
./scripts/dev_workflow.sh sync      # Sync code to Pi
./scripts/dev_workflow.sh run       # Run on Pi with real hardware
./scripts/dev_workflow.sh run --mock # Run on Pi with mocks
./scripts/dev_workflow.sh logs      # View logs
./scripts/dev_workflow.sh ssh       # SSH to Pi
./scripts/dev_workflow.sh led       # Test LED control
./scripts/dev_workflow.sh status    # Show Pi status
```

### Workflow C: VS Code Remote SSH (Most Convenient)

**Best for:** Extended debugging sessions, direct editing on Pi

```bash
# In VS Code
# 1. Cmd+Shift+P → "Remote-SSH: Connect to Host" → monitoni-pi
# 2. Open folder: /home/pi/MoniToniVending
# 3. Edit files directly on Pi
# 4. Run in integrated terminal: python -m monitoni.main
```

**Benefits:**
- Edit files on Pi as if they're local
- Terminal runs commands on Pi
- Extensions (Python, linting) work on Pi
- No sync delays

## Common Development Tasks

### Test LED Control

**On MacBook (with mocks):**
```bash
python -m monitoni.main --mock
# LED output will be printed to console
```

**On Pi (with real hardware):**
```bash
# Using workflow script
./scripts/dev_workflow.sh led

# Or manually via SSH
ssh pi@<pi-ip>
cd ~/MoniToniVending
python -c "
import asyncio
from monitoni.hardware.wled_controller import WLEDController

async def test():
    from monitoni.core.config import load_config
    config = load_config()
    controller = WLEDController(config.hardware.wled)
    await controller.connect()

    # Test animations
    await controller.set_animation('rainbow_chase', brightness=0.5)
    await asyncio.sleep(5)

    # Test zone highlighting
    for zone in range(10):
        await controller.highlight_zone(zone, color=(255, 0, 0))
        await asyncio.sleep(1)

    await controller.clear()
    await controller.disconnect()

asyncio.run(test())
"
```

### View Real-Time Logs

**From MacBook:**
```bash
# Using workflow script
./scripts/dev_workflow.sh logs

# Or manually
ssh pi@<pi-ip> "tail -f ~/MoniToniVending/logs/monitoni.log"
```

**Via Telemetry Dashboard:**
```bash
# In browser on MacBook
http://<pi-ip>:8000
```

### Test Motor Control

**On Pi:**
```bash
python -c "
import asyncio
from monitoni.hardware.modbus_relay import ModbusRelayController

async def test():
    from monitoni.core.config import load_config
    config = load_config()
    controller = ModbusRelayController(config.hardware.modbus)
    await controller.connect()

    # Test relay 1 (motor)
    await controller.set_channel(1, True)
    await asyncio.sleep(2)
    await controller.set_channel(1, False)

    await controller.disconnect()

asyncio.run(test())
"
```

### Debug Purchase Flow

**On MacBook (with mocks):**
```bash
python -m monitoni.main --mock --debug
# Interact with UI to test state machine
```

**On Pi (with hardware):**
```bash
# Run and monitor logs
python -m monitoni.main 2>&1 | tee debug.log
```

## Troubleshooting

### Cannot Connect to Pi

1. Check Pi is powered on and connected to network
2. Find Pi's IP address: `arp -a | grep -i b8:27:eb` (Raspberry Pi MAC prefix)
3. Or on Pi directly: `hostname -I`
4. Update PI_HOST environment variable or script

### Code Changes Not Reflected

**If using Git workflow:**
```bash
# On Pi, make sure you pulled latest
git status
git pull origin main
```

**If using sync script:**
```bash
# Make sure sync completed successfully
./scripts/dev_workflow.sh sync
./scripts/dev_workflow.sh status  # Verify
```

### LED Not Working

1. Check WLED controller is powered and on network
2. Verify WLED IP address in `config/local.yaml`
3. Test WLED directly: Visit `http://<wled-ip>` in browser
4. Check ArtNet is enabled in WLED settings
5. Run LED test script: `./scripts/dev_workflow.sh led`

### Modbus Relay Not Responding

1. Check RS485 adapter is connected: `ls -l /dev/tty*`
2. Verify serial port in `config/local.yaml` matches actual device
3. Test raw communication: `python scripts/test_relay_raw.py`
4. Check baud rate (9600), parity (None), stop bits (1)

### Permission Denied on Serial Port

```bash
# On Pi
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Touchscreen Not Working

1. Check HDMI connection
2. Verify `/boot/config.txt` has correct settings (setup script adds them)
3. Reboot Pi
4. Test touch: `evtest` (install with `sudo apt-get install evtest`)

## Best Practices

### Development Cycle

1. **Develop locally** on MacBook with `--mock` flag
2. **Test locally** to verify basic functionality
3. **Sync to Pi** using git or rsync
4. **Test on hardware** to verify hardware integration
5. **Iterate** as needed
6. **Commit final version** to git

### Git Workflow

- **Main branch**: Stable, production-ready code
- **Feature branches**: Use for major changes
- **Test on Pi before merging** to main
- **Keep commits atomic**: One logical change per commit

### Configuration Management

- **Never commit `config/local.yaml`** (it's gitignored)
- **Document required settings** in `config/default.yaml` comments
- **Use environment-specific values** in `local.yaml`

### Testing Strategy

1. **Unit tests**: Run locally on MacBook
2. **Integration tests**: Test state machine, purchase flow with mocks
3. **Hardware tests**: Only on Pi with real hardware
4. **UI tests**: Test on Pi's touchscreen display

## Quick Reference

### MacBook Commands

```bash
# Run locally with mocks
python -m monitoni.main --mock

# Run tests
pytest

# Sync to Pi
./scripts/dev_workflow.sh sync

# Run on Pi
./scripts/dev_workflow.sh run

# View Pi logs
./scripts/dev_workflow.sh logs

# SSH to Pi
./scripts/dev_workflow.sh ssh
```

### Pi Commands

```bash
# Pull latest code
cd ~/MoniToniVending && git pull

# Run with hardware
python -m monitoni.main

# Run with mocks (for testing)
python -m monitoni.main --mock

# View logs
tail -f logs/monitoni.log

# Start as service
sudo systemctl start monitoni

# Stop service
sudo systemctl stop monitoni

# View service status
sudo systemctl status monitoni
```

### VS Code Remote SSH

1. `Cmd+Shift+P` → "Remote-SSH: Connect to Host"
2. Select `monitoni-pi`
3. Open folder: `/home/pi/MoniToniVending`
4. Edit and run directly on Pi

## Additional Resources

- [SETUP.md](SETUP.md) - Detailed installation guide
- [SYSTEM.md](SYSTEM.md) - Architecture documentation
- [UI_TESTING.md](UI_TESTING.md) - UI testing procedures
- [CLAUDE.MD](../CLAUDE.MD) - AI assistant context
