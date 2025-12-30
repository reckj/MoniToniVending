# QR Code URL Management

Complete guide for managing QR code URLs in the MoniToni vending machine system.

## Overview

The QR code URL management system allows you to configure and update the URLs that are encoded in QR codes displayed to customers. This enables flexibility in changing payment endpoints without modifying code.

## Features

- **Configurable Base URL**: Set a default base URL for all levels
- **Per-Level Custom URLs**: Override URLs for specific product levels
- **Multiple Update Methods**:
  - Web dashboard (telemetry frontend)
  - Hardware debug screen (via USB stick)
  - Direct config file editing
  - REST API
- **Automatic QR Code Regeneration**: QR codes are regenerated when URLs change
- **Placeholder Support**: URLs support `{level}` and `{machine_id}` placeholders

## Configuration

### Default Configuration

Located in `config/default.yaml`:

```yaml
vending:
  qr_urls:
    base_url: "https://example.com/purchase"
    level_urls:
      1: ""  # Empty = use base_url?level=1&machine={machine_id}
      2: ""
      3: ""
      4: ""
      5: ""
      6: ""
      7: ""
      8: ""
      9: ""
      10: ""
```

### Local Overrides

Create `config/local.yaml` to override defaults:

```yaml
vending:
  qr_urls:
    base_url: "https://www.monitoni.zhdk.ch/purchase"
    level_urls:
      1: "https://www.monitoni.zhdk.ch/premium-level-1"
      2: "https://www.monitoni.zhdk.ch/premium-level-2"
```

### URL Format

- **Base URL with auto parameters**: `https://example.com/purchase?level={level}&machine={machine_id}`
- **Custom URL with placeholders**: `https://example.com/level/{level}/machine/{machine_id}`
- **Static URL (no placeholders)**: `https://example.com/buy/premium-product-1`

Empty level URLs fall back to: `{base_url}?level={level}&machine={machine_id}`

## Update Methods

### 1. Web Dashboard (Telemetry Frontend)

**Access**: Navigate to `http://<pi-ip>:8000` in your browser

**Steps**:
1. Scroll to "QR Code Management" section
2. View current URLs
3. Enter new base URL (optional)
4. Click "Show Level URLs" to set per-level URLs (optional)
5. Enter your PIN
6. Click "Update URLs"

**Features**:
- Live preview of URLs for each level
- Copy URL to clipboard
- Regenerate QR codes button
- Real-time updates via WebSocket

### 2. Hardware Debug Screen (USB Stick)

**Access**: On the vending machine touchscreen

**Steps**:
1. Create a JSON or YAML file with QR URLs (see format below)
2. Copy file to USB stick
3. Insert USB stick into Raspberry Pi
4. Enter debug mode (5 taps in top-right corner, enter PIN)
5. Scroll to "QR Code URL Management" section
6. Tap "Load from USB"
7. Browse to `/media/<usb-name>/` and select your file
8. Tap "Load"

**File Format (JSON)**:
```json
{
  "base_url": "https://www.monitoni.zhdk.ch/purchase",
  "level_urls": {
    "1": "https://www.monitoni.zhdk.ch/buy/level1",
    "2": "https://www.monitoni.zhdk.ch/buy/level2",
    "3": "",
    "4": "",
    "5": "",
    "6": "",
    "7": "",
    "8": "",
    "9": "",
    "10": ""
  }
}
```

**File Format (YAML)**:
```yaml
base_url: https://www.monitoni.zhdk.ch/purchase
level_urls:
  1: https://www.monitoni.zhdk.ch/buy/level1
  2: https://www.monitoni.zhdk.ch/buy/level2
  3: ""
  4: ""
  5: ""
  6: ""
  7: ""
  8: ""
  9: ""
  10: ""
```

**Example files**: See `docs/qr_urls_example.json` and `docs/qr_urls_example.yaml`

### 3. REST API

**Endpoint**: `POST /api/qr-urls`

**Request**:
```bash
curl -X POST http://<pi-ip>:8000/api/qr-urls \
  -H "Content-Type: application/json" \
  -d '{
    "pin": "1234",
    "base_url": "https://www.monitoni.zhdk.ch/purchase",
    "level_urls": {
      "1": "https://www.monitoni.zhdk.ch/buy/level1"
    }
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "QR URLs updated successfully",
  "base_url": "https://www.monitoni.zhdk.ch/purchase",
  "level_urls": {
    "1": "https://www.monitoni.zhdk.ch/buy/level1"
  }
}
```

**Get Current URLs**:
```bash
curl http://<pi-ip>:8000/api/qr-urls
```

**Regenerate QR Codes**:
```bash
curl -X POST "http://<pi-ip>:8000/api/qr-urls/regenerate?pin=1234"
```

### 4. Direct Config File Edit

**NOT RECOMMENDED** for production, but useful for initial setup:

```bash
# SSH into Pi
ssh pi@<pi-ip>

# Edit local config
cd ~/MoniToniVending
nano config/local.yaml

# Add or update QR URLs section
# Save and exit

# Restart service for changes to take effect
sudo systemctl restart monitoni
```

## QR Code Generation

### How It Works

1. **Customer selects a level** → QR code view is displayed
2. **System checks for cached QR code** at `assets/qr_codes/level_{level}.png`
3. **If not found or invalidated** → Generate new QR code
4. **URL is generated** using `config.vending.qr_urls.get_url_for_level(level, machine_id)`
5. **QR code is created** and cached for future use

### Cache Invalidation

QR codes are automatically invalidated when:
- URLs are updated via telemetry API
- "Regenerate QR Codes" button is clicked
- QR cache files are manually deleted

### Manual Regeneration

```bash
# On the Pi
rm -rf ~/MoniToniVending/assets/qr_codes/level_*.png

# QR codes will be regenerated next time they're displayed
```

## Security

- **PIN Protection**: All URL updates require PIN authentication
- **Local Storage**: URLs are stored in local config file
- **No Remote Updates**: Updates must be initiated locally (dashboard, debug screen, or API)
- **Audit Trail**: All updates are logged in system logs

## Troubleshooting

### QR Codes Not Updating

1. Check that QR cache was cleared:
   ```bash
   ls ~/MoniToniVending/assets/qr_codes/
   # Should be empty or not contain level_*.png files
   ```

2. Verify config was updated:
   ```bash
   cat ~/MoniToniVending/config/local.yaml | grep -A 15 "qr_urls"
   ```

3. Reload config in debug screen (tap "Reload Config" button)

### USB File Not Loading

1. **Check mount point**:
   ```bash
   ls /media/
   # USB should appear here
   ```

2. **Check file format**:
   - Must be valid JSON or YAML
   - Must have `.json`, `.yaml`, or `.yml` extension
   - Check syntax with: `cat /media/<usb>/yourfile.json | python -m json.tool`

3. **Check file permissions**:
   ```bash
   ls -l /media/<usb>/yourfile.json
   # Should be readable
   ```

### Web Dashboard Not Working

1. **Check telemetry server is running**:
   ```bash
   sudo systemctl status monitoni
   # Or check if port 8000 is open:
   netstat -tulpn | grep 8000
   ```

2. **Check browser console** for JavaScript errors

3. **Verify PIN** is correct (set in `config/local.yaml` → `telemetry.debug_pin`)

## API Reference

### Get QR URLs

```
GET /api/qr-urls
```

**Response**:
```json
{
  "base_url": "https://example.com/purchase",
  "level_urls": {
    "1": "https://example.com/custom1",
    "2": ""
  }
}
```

### Update QR URLs

```
POST /api/qr-urls
Content-Type: application/json

{
  "pin": "1234",
  "base_url": "https://example.com/purchase",  // optional
  "level_urls": {                                // optional
    "1": "https://example.com/custom1",
    "2": "https://example.com/custom2"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "QR URLs updated successfully",
  "base_url": "https://example.com/purchase",
  "level_urls": {
    "1": "https://example.com/custom1",
    "2": "https://example.com/custom2"
  }
}
```

### Regenerate QR Codes

```
POST /api/qr-urls/regenerate?pin=1234
```

**Response**:
```json
{
  "success": true,
  "message": "QR code regeneration triggered"
}
```

## Best Practices

1. **Test URLs before deployment**: Verify all URLs are accessible
2. **Use placeholders**: Makes URLs dynamic and maintainable
3. **Document custom URLs**: Keep a record of what each custom URL is for
4. **Regular backups**: Backup `config/local.yaml` regularly
5. **Version control**: Track URL changes in your deployment documentation

## Future Enhancements

- **Remote URL fetch**: Fetch URLs from a remote endpoint (mentioned by user as future feature)
- **QR code styling**: Customize QR code colors and logos
- **URL validation**: Validate URLs before saving
- **Preview before save**: Show QR code preview before applying changes
- **Bulk upload**: Upload multiple configurations at once
- **URL analytics**: Track which URLs are used most often
