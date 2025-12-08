# MoniToni UI Testing Guide

## Prerequisites

✅ KivyMD and dependencies installed
✅ Mock hardware implementations ready
✅ Configuration files in place

## Testing Options

### Option 1: Test on Raspberry Pi with Display (Recommended)

If you're running this on a Raspberry Pi 5 with the touchscreen connected:

```bash
cd /home/selecta/PiToni
source venv/bin/activate

# Run with mock hardware
python -m monitoni.main --mock

# Or run with real hardware (if connected)
python -m monitoni.main
```

**Expected Behavior:**
1. Application launches in fullscreen
2. Customer screen displays with 10 product level buttons
3. Status shows "Welcome! Select a product level"
4. Tap any level button to simulate purchase
5. LEDs change color (mock: console output)
6. Tap top-right corner 5 times to access debug screen
7. Enter PIN (default: 1234)
8. Test hardware controls in debug screen

### Option 2: Test via X11 Forwarding (SSH)

If you're connected via SSH and want to see the UI:

```bash
# On your local machine, connect with X11 forwarding
ssh -X selecta@192.168.1.165

# Then run the application
cd /home/selecta/PiToni
source venv/bin/activate
python -m monitoni.main --mock
```

**Note:** X11 forwarding may be slow for touchscreen UI.

### Option 3: Test Without Display (Headless)

Run in test mode to verify core functionality without UI:

```bash
cd /home/selecta/PiToni
source venv/bin/activate

# Test mode - no UI, just hardware tests
python -m monitoni.main --mock --test
```

This will:
- Initialize all hardware (mock mode)
- Run hardware tests
- Exit without launching UI

## UI Features to Test

### Customer Screen

1. **Product Selection:**
   - Tap each level button (1-10)
   - Verify status updates to "Processing Level X..."
   - Check LED zone highlighting (console output in mock mode)

2. **Purchase Flow:**
   - Select a level
   - Watch state transition: IDLE → CHECKING_PURCHASE → DOOR_UNLOCKED
   - Simulated door open/close (in mock mode, manually trigger)
   - Status shows "Thank you! Enjoy your product!"
   - Returns to IDLE

3. **Sleep Mode:**
   - Wait 60 seconds without interaction
   - Screen should show "Touch to wake up"
   - LEDs dim (mock: console shows sleep animation)
   - Tap anywhere to wake up

4. **Debug Access:**
   - Tap top-right corner 5 times quickly
   - PIN dialog appears
   - Enter PIN: 1234
   - Debug screen opens

### Debug Screen

1. **Relay Control:**
   - Expand "Relay Controller" panel
   - Tap "Test All Relays (Cascade)"
   - Watch console output: each relay activates/deactivates in sequence
   - Tap individual relay buttons (R1-R32)
   - Verify console shows relay state changes

2. **LED Control:**
   - Expand "LED Controller" panel
   - Tap color buttons (Red, Green, Blue, White, Off)
   - Adjust brightness slider
   - Tap animation buttons (idle, sleep, valid_purchase, etc.)
   - Verify console output shows color/animation changes

3. **Audio Control:**
   - Expand "Audio Controller" panel
   - Adjust volume slider
   - Tap sound playback buttons
   - Verify console output shows audio playback

4. **Sensors:**
   - Expand "Sensors" panel
   - View door status (mock: shows CLOSED)
   - In real hardware: open/close door to see status change

5. **Statistics:**
   - Expand "Statistics" panel
   - View purchase counts and incidents
   - Complete a purchase to see count increment

6. **Logs:**
   - Expand "Logs" panel
   - Tap "View Recent Logs"
   - Dialog shows last 20 log entries
   - Tap "Export Logs to JSON"
   - Check logs/ directory for exported file

## Troubleshooting

### Issue: "No display found"

**Solution:** You're running headless. Use Option 3 (test mode) or connect a display.

### Issue: "Permission denied" for GPIO

**Solution:** Add user to gpio group:
```bash
sudo usermod -a -G gpio $USER
# Logout and login again
```

### Issue: UI is very slow

**Possible causes:**
- X11 forwarding over slow network
- Insufficient GPU memory

**Solutions:**
- Test directly on Pi with display
- Increase GPU memory in raspi-config

### Issue: Touch not working

**Solution:** Ensure touchscreen is properly connected and configured:
```bash
# Check for touch device
ls /dev/input/event*

# Test touch input
evtest /dev/input/event0  # Adjust number as needed
```

## Mock Hardware Output

When running in mock mode, you'll see console output like:

```
[MOCK] Relay 1: ON
[MOCK] Relay 1: OFF
[MOCK] LED: All pixels set to RGB(255, 0, 0)
[MOCK] LED: Playing animation 'valid_purchase'
[MOCK] Audio: Playing 'valid_purchase' at volume 0.70
[MOCK] Sensor: Door CLOSED
[MOCK] Purchase server: Valid purchase for level 3
```

## Real Hardware Testing

When ready to test with actual hardware:

1. **Connect Hardware:**
   - Modbus relay board to RS485
   - WLED controller to network
   - Door sensor to GPIO pin 17
   - Touchscreen via HDMI

2. **Configure:**
   - Update `config/local.yaml` with actual IPs and ports
   - Verify wiring matches configuration

3. **Run:**
   ```bash
   python -m monitoni.main
   ```

4. **Verify:**
   - Relays click when activated
   - LEDs change color/animation
   - Audio plays through HDMI
   - Door sensor detects open/close

## Performance Expectations

- **Startup time:** ~2-3 seconds
- **UI responsiveness:** <100ms for button presses
- **State transitions:** Immediate
- **LED animations:** 30 FPS
- **Memory usage:** ~150-200MB
- **CPU usage:** <10% idle, <20% during animations

## Next Steps After Testing

1. ✅ Verify all UI features work
2. ✅ Test purchase flow end-to-end
3. ✅ Confirm hardware controls function
4. 🔄 Deploy to production hardware
5. 🔄 Configure systemd service
6. 🔄 Set up telemetry server
7. 🔄 Connect to real purchase server

## Support

If you encounter issues:
1. Check logs: `tail -f logs/monitoni.log`
2. View database logs: See SETUP.md for SQL queries
3. Enable debug logging: `python -m monitoni.main --mock --debug`
4. Open GitHub issue with error details

---

**Status:** UI is ready for testing! 🎉
