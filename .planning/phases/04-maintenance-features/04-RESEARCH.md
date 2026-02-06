# Phase 4: Maintenance Features - Research

**Researched:** 2026-02-06
**Domain:** QR code management, USB file handling, maintenance mode state management, Kivy/KivyMD UI
**Confidence:** HIGH

## Summary

Phase 4 focuses on enabling operators to manage the vending machine entirely through the touchscreen interface without requiring a web frontend. The phase covers three main areas: QR code management (generation from URLs and upload from USB), out-of-order maintenance mode toggle, and machine status display.

The standard stack already exists in this codebase: `qrcode` library for QR generation (needs installation), `pathlib` for file system operations, KivyMD's `MDFileManager` for USB file browsing with image preview, and the existing `ConfigManager` with dot-notation config persistence. The codebase already has patterns for BaseDebugSubScreen, NumpadField/TextInputDialog for input, MDSwitch for toggles, and LiveStatusCard for status display.

Key insights: QR code generation is already implemented in `customer_screen.py` but needs to be made operator-accessible; USB drives auto-mount to `/media/username/` on Raspberry Pi OS Desktop with proper permissions; maintenance mode is a simple boolean toggle that affects purchase flow behavior; all existing Phase 2 patterns (SettingsCard, config helpers, color constants) apply here.

**Primary recommendation:** Build maintenance features as new debug sub-screens using established patterns. Use `qrcode[pil]` for generation, MDFileManager for USB file selection with image preview, and add `maintenance_mode` boolean to config. No new libraries needed beyond `qrcode` installation.

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qrcode | 8.2 (latest) | QR code generation from URLs | Industry standard Python QR library, pure Python with PIL support |
| Pillow | (via qrcode[pil]) | Image manipulation for QR codes | Required dependency for qrcode image output |
| pathlib | stdlib | File system operations, USB drive browsing | Modern Python standard for path operations |
| KivyMD MDFileManager | 1.2.0 | File picker with image preview | Built-in KivyMD component, supports filtering and preview |
| PyYAML | 6.0.1+ (existing) | Config persistence for maintenance_mode | Already used by ConfigManager |

### Supporting Patterns (Already in Codebase)

| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| BaseDebugSubScreen | debug_screens/base.py | Sub-screen base class | All maintenance screens |
| SettingsCard | debug_screens/widgets.py | Grouped settings sections | Card-based layout |
| NumpadField | debug_screens/widgets.py | Numeric input (for level selection) | QR assignment |
| TextInputDialog | debug_screens/widgets.py | String input (for URLs) | Payment link entry |
| MDSwitch | kivymd.uix.selectioncontrol | Toggle switches | Maintenance mode toggle |
| LiveStatusCard | debug_screens/widgets.py | Real-time status display | Machine status screen |
| update_config_value() | debug_screens/widgets.py | Config persistence helper | Save maintenance_mode |
| CORAL_ACCENT, NEAR_BLACK | debug_screens/widgets.py | Color constants | UI consistency |

### Installation Required

```bash
# QR code library not yet installed (checked requirements.txt)
pip install qrcode[pil]

# Add to requirements.txt:
qrcode>=8.2
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| qrcode | segno | Segno has more customization options (Micro QR, SVG output) but qrcode is simpler and already partially used in customer_screen.py |
| MDFileManager | Kivy FileChooserIconView | FileChooserIconView is more basic, MDFileManager has built-in preview mode for images |
| Config-based toggle | Database flag | Config file is simpler, already established pattern, survives reinstalls |

## Architecture Patterns

### Recommended Screen Structure

```
monitoni/ui/debug_screens/
├── qr_management_screen.py    # QR code generation and assignment
├── maintenance_screen.py       # Out-of-order toggle and status
└── (existing screens remain)
```

Config structure addition:
```yaml
# config/default.yaml
system:
  maintenance_mode: false  # New: disables purchase flow when true
  maintenance_message: "Maschine wird gewartet"  # German maintenance message

# QR codes stored as files, not config
# assets/qr_codes/level_N.png (generated)
# assets/qr_codes/custom_level_N.png (uploaded)
```

### Pattern 1: QR Code Generation from URL

**What:** Generate QR code PNG from payment link URL and save to assets folder
**When to use:** Operator enters payment URL via TextInputDialog
**Example:**
```python
# Source: https://pypi.org/project/qrcode/ and existing customer_screen.py
import qrcode
from pathlib import Path

def generate_qr_code(payment_url: str, level: int, output_dir: Path):
    """Generate QR code for payment URL and save to level slot."""
    # Create QR code with medium error correction
    qr = qrcode.QRCode(
        version=1,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% correction
        box_size=10,
        border=4,  # Standard minimum border
    )
    qr.add_data(payment_url)
    qr.make(fit=True)

    # Generate black/white image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to level slot
    output_path = output_dir / f"level_{level}.png"
    img.save(str(output_path))

    return output_path
```

**Key parameters:**
- `error_correction`: Use `ERROR_CORRECT_M` (15%) for balance of size and reliability
- `version=1`: Auto-sizing, QR adjusts to data length
- `box_size=10`: Good balance for touchscreen display
- `border=4`: Minimum per QR spec, ensures scannability

### Pattern 2: USB File Upload with Preview

**What:** Browse USB drive files, preview images, copy to QR code slot
**When to use:** Operator has pre-generated QR codes on USB drive
**Example:**
```python
# Source: https://kivymd.readthedocs.io/en/latest/components/filemanager/
from kivymd.uix.filemanager import MDFileManager
from pathlib import Path
import shutil

class QRManagementScreen(BaseDebugSubScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "QR Code Verwaltung"

        # File manager for USB browsing
        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.select_qr_file,
            preview=True,  # Show image previews
            ext=['.png', '.jpg', '.jpeg'],  # QR images only
        )

    def open_usb_browser(self, instance):
        """Open file browser starting at /media (USB auto-mount location)."""
        # Raspberry Pi OS Desktop auto-mounts USB to /media/username/
        usb_path = Path("/media") / os.getenv("USER", "admin")
        if usb_path.exists():
            self.file_manager.show(str(usb_path))
        else:
            # Fallback to /media root
            self.file_manager.show("/media")

    def select_qr_file(self, path):
        """Handle file selection - copy to QR code directory."""
        src = Path(path)
        if src.is_file() and src.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            # Copy to custom slot (will be shown instead of generated QR)
            dst = Path("assets/qr_codes") / f"custom_level_{self.selected_level}.png"
            shutil.copy2(src, dst)

            # Show success feedback
            self.show_status(f"QR code für Level {self.selected_level} hochgeladen")

        self.file_manager.close()

    def exit_file_manager(self, *args):
        """Called when navigating to root directory."""
        self.file_manager.close()
```

**USB mount locations on Raspberry Pi:**
- Desktop environment: `/media/username/DRIVE_NAME/`
- Lite (if configured): `/media/usb0/` or similar
- Check both locations for compatibility

### Pattern 3: Maintenance Mode Toggle

**What:** Boolean flag in config that disables purchase flow and shows maintenance message
**When to use:** Operator needs to service machine or adjust inventory
**Example:**
```python
# Source: Existing state_machine.py and widgets.py patterns
from kivymd.uix.selectioncontrol import MDSwitch
from kivy.clock import Clock

class MaintenanceScreen(BaseDebugSubScreen):
    def __init__(self, config_manager, hardware, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.hardware = hardware
        self.title = "Wartungsmodus"

        # Build UI
        card = SettingsCard(title="Betriebsmodus")

        # Maintenance mode toggle
        toggle_row = BoxLayout(orientation='horizontal', spacing="10dp",
                               size_hint_y=None, height="60dp")
        toggle_row.add_widget(MDLabel(text="Wartungsmodus:"))

        self.maintenance_toggle = MDSwitch()
        # Get current state from config
        current_state = self.config_manager.config.system.maintenance_mode
        # Use Clock to set active state after widget is fully built (KivyMD 1.2.0 quirk)
        Clock.schedule_once(
            lambda dt: setattr(self.maintenance_toggle, 'active', current_state)
        )
        self.maintenance_toggle.bind(on_active=self.on_maintenance_toggle)
        toggle_row.add_widget(self.maintenance_toggle)

        card.add_content(toggle_row)
        self.add_content(card)

    def on_maintenance_toggle(self, switch, value):
        """Handle maintenance mode toggle."""
        # Save to config
        update_config_value(
            self.config_manager,
            "system.maintenance_mode",
            value
        )

        # Show feedback
        if value:
            self.show_status("Wartungsmodus AKTIVIERT - Verkauf gesperrt", ERROR_RED)
        else:
            self.show_status("Wartungsmodus deaktiviert - Verkauf aktiv", (0, 1, 0, 1))
```

**Integration with purchase flow:**
```python
# In customer_screen.py or state_machine.py
def can_start_purchase(self) -> bool:
    """Check if purchases are allowed."""
    if self.config.system.maintenance_mode:
        self.show_maintenance_message()
        return False
    return True
```

### Pattern 4: Machine Status Display

**What:** LiveStatusCard showing key machine metrics and hardware status
**When to use:** Operator needs quick overview of machine health
**Example:**
```python
# Using existing LiveStatusCard pattern from widgets.py
async def get_machine_status(self) -> List[Tuple[str, str, Tuple]]:
    """Get machine status items for LiveStatusCard."""
    items = []

    # Maintenance mode
    if self.config_manager.config.system.maintenance_mode:
        items.append(("Modus:", "WARTUNG", ERROR_RED))
    else:
        items.append(("Modus:", "Betrieb", (0, 1, 0, 1)))

    # Hardware status
    relay_ok = await self.hardware.relay.is_connected()
    items.append(("Relais:", "OK" if relay_ok else "FEHLER",
                  (0, 1, 0, 1) if relay_ok else ERROR_RED))

    led_ok = await self.hardware.led.is_connected()
    items.append(("LEDs:", "OK" if led_ok else "OFFLINE",
                  (0, 1, 0, 1) if led_ok else (1, 1, 0, 1)))

    # Door sensor
    door_open = await self.hardware.sensor.is_door_open()
    items.append(("Tür:", "OFFEN" if door_open else "Geschlossen",
                  (1, 1, 0, 1) if door_open else (0.5, 0.5, 0.5, 1)))

    # Purchase server
    server_ok = self.app.purchase_flow.server_reachable
    items.append(("Server:", "Online" if server_ok else "Offline",
                  (0, 1, 0, 1) if server_ok else ERROR_RED))

    return items

# Create status card
status_card = LiveStatusCard(
    title="Maschinenstatus",
    get_status_callback=self.get_machine_status,
    update_interval=1.0  # Update every second
)
```

### Anti-Patterns to Avoid

- **Setting MDSwitch.active in __init__**: Use `Clock.schedule_once` to defer (KivyMD 1.2.0 quirk - see kivymd-quirks.md)
- **Hardcoding USB mount path**: Check both `/media/username/` and `/media/` for compatibility
- **Using ERROR_CORRECT_L for QR codes**: Too low for reliable scanning, use ERROR_CORRECT_M or higher
- **Forgetting to reload customer_screen QR codes**: After generation/upload, customer screen needs to reload images
- **Blocking operations on main thread**: Use async for hardware status checks in LiveStatusCard

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QR code generation | Custom QR encoder | `qrcode[pil]` library | QR spec is complex, error correction requires lookup tables |
| Image file preview | Custom image viewer | MDFileManager with `preview=True` | Built into KivyMD, handles loading/thumbnails |
| USB drive detection | Custom udev monitoring | Check `/media/username/` with pathlib | Desktop environment handles auto-mount reliably |
| File copying | Manual read/write loops | `shutil.copy2()` | Preserves metadata, handles errors, tested |
| Config persistence | Manual YAML writing | Existing `update_config_value()` | Handles dot-notation, deep merge, atomic writes |
| Text input dialogs | Custom popup | Existing `TextInputDialog` | Already styled, validated, consistent with app |

**Key insight:** This phase requires almost no new code patterns. The codebase already has all the UI components and config management needed. Main work is composing existing patterns into new screens.

## Common Pitfalls

### Pitfall 1: QR Code Installation Missing

**What goes wrong:** Import `qrcode` fails because library not installed
**Why it happens:** `qrcode` is used in `customer_screen.py` but not in `requirements.txt`
**How to avoid:** Add `qrcode>=8.2` to requirements.txt with `[pil]` extra
**Warning signs:** `ModuleNotFoundError: No module named 'qrcode'` on startup

**Fix:**
```bash
pip install qrcode[pil]
# Add to requirements.txt:
qrcode>=8.2
```

### Pitfall 2: QR Code Error Correction Too Low

**What goes wrong:** Generated QR codes don't scan reliably, especially in poor lighting
**Why it happens:** Using `ERROR_CORRECT_L` (7% correction) saves space but reduces reliability
**How to avoid:** Use `ERROR_CORRECT_M` (15%) as default, `ERROR_CORRECT_H` (30%) if adding logos
**Warning signs:** Customer complaints about scanning failures, works in good conditions but fails in practice

**Recommended settings:**
```python
# For payment URLs (no logo)
error_correction=qrcode.constants.ERROR_CORRECT_M  # 15% correction

# If adding branding logo later
error_correction=qrcode.constants.ERROR_CORRECT_H  # 30% correction
# Logo must be <30% of QR code area
```

Sources: [QR Code Error Correction Explained](https://scanova.io/blog/qr-code-error-correction/), [Python QRCode Guide](https://coderivers.org/blog/python-qrcode/)

### Pitfall 3: MDSwitch Active State Crash

**What goes wrong:** Setting `MDSwitch.active=True` in constructor crashes with `'super' object has no attribute '__getattr__'`
**Why it happens:** KivyMD 1.2.0 bug - `on_active` event fires before KV layout builds `self.ids.thumb`
**How to avoid:** Use `Clock.schedule_once` to defer setting active state
**Warning signs:** App crashes when loading maintenance screen if maintenance mode was enabled

**Fix (from kivymd-quirks.md):**
```python
# BAD - crashes
self.toggle = MDSwitch(active=True)

# GOOD - deferred
self.toggle = MDSwitch()
Clock.schedule_once(lambda dt: setattr(self.toggle, 'active', True))
```

### Pitfall 4: USB Drive Permission Denied

**What goes wrong:** MDFileManager opens but can't read files from USB drive
**Why it happens:** USB mounted with root ownership or wrong filesystem permissions
**How to avoid:** Use Raspberry Pi OS Desktop (auto-mounts with user ownership); for FAT drives, mount with `uid=pi,gid=pi`
**Warning signs:** File manager shows drive but clicking files does nothing or shows errors

**Solution:**
- Raspberry Pi OS Desktop: Auto-mounts to `/media/username/` with correct permissions
- If manual mount needed: `mount -o uid=1000,gid=1000 /dev/sda1 /media/usb`
- FAT/NTFS drives don't support Linux permissions - ownership set at mount time

Sources: [Raspberry Pi USB Auto-mount](https://forums.raspberrypi.com/viewtopic.php?t=276494), [Mount File Systems Without Root](https://www.baeldung.com/linux/mount-file-systems-without-root-privileges)

### Pitfall 5: Maintenance Mode Not Blocking Purchases

**What goes wrong:** Setting maintenance_mode=true in config but purchases still work
**Why it happens:** Customer screen doesn't check maintenance mode flag before starting purchase flow
**How to avoid:** Add maintenance mode check in `customer_screen.py` before QR code display and in `state_machine.py` before accepting purchases
**Warning signs:** Maintenance mode toggle changes config but customers can still buy

**Integration points:**
```python
# customer_screen.py - before showing QR code
if self.app_config.system.maintenance_mode:
    self.show_maintenance_message()
    return  # Don't show QR code

# state_machine.py - before checking purchase
async def handle_event(self, event: Event, **kwargs):
    if event == Event.PURCHASE_SELECTED:
        if self.config.system.maintenance_mode:
            return False  # Reject purchase
    # ... rest of logic
```

### Pitfall 6: Image Path Confusion (Generated vs Uploaded)

**What goes wrong:** Uploaded QR codes not showing, or generated codes overwriting uploads
**Why it happens:** Customer screen checks `custom_level_N.png` first but QR management overwrites `level_N.png`
**How to avoid:** Follow existing pattern in `customer_screen.py`: custom files take precedence, generated files are fallback
**Warning signs:** Operator uploads QR but customer screen shows old generated version

**Existing pattern (already correct):**
```python
# customer_screen.py:_load_qr_code()
custom_qr_path = self.qr_cache_dir / f"custom_level_{level}.png"
if custom_qr_path.exists():
    self.qr_image.source = str(custom_qr_path)
    return  # Custom takes precedence

# Fallback to generated
qr_path = self.qr_cache_dir / f"level_{level}.png"
```

**Action for QR management screen:**
- Generate: Write to `level_N.png`
- Upload: Write to `custom_level_N.png`
- Delete custom: Remove `custom_level_N.png` file

## Code Examples

Verified patterns from codebase and official sources:

### Complete QR Management Screen Structure

```python
# monitoni/ui/debug_screens/qr_management_screen.py
"""
QR code management screen for operator maintenance.

Allows operators to:
- Generate QR codes from payment URLs
- Upload QR codes from USB drive
- Preview QR codes before assignment
- Assign QR codes to product levels
- Delete custom QR codes (revert to generated)
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
import qrcode

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    NumpadField,
    TextInputDialog,
    CORAL_ACCENT,
    NEAR_BLACK,
    ERROR_RED,
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class QRManagementScreen(BaseDebugSubScreen):
    """QR code generation and assignment for product levels."""

    def __init__(self, config_manager: ConfigManager, hardware: HardwareManager,
                 navigate_back=None, **kwargs):
        super().__init__(navigate_back=navigate_back, **kwargs)
        self.config_manager = config_manager
        self.hardware = hardware
        self.title = "QR Code Verwaltung"

        self.qr_dir = Path("assets/qr_codes")
        self.qr_dir.mkdir(parents=True, exist_ok=True)

        self.selected_level: Optional[int] = None
        self.text_input_dialog: Optional[TextInputDialog] = None

        # File manager for USB browsing
        self.file_manager = MDFileManager(
            exit_manager=self.exit_file_manager,
            select_path=self.select_qr_file,
            preview=True,  # Show image previews
            ext=['.png', '.jpg', '.jpeg'],
        )

        self._build_ui()

    def _build_ui(self):
        """Build QR management UI."""
        # Level selection card
        level_card = SettingsCard(title="Level auswählen")

        self.level_field = NumpadField(
            label="Product Level:",
            initial_value=1,
            min_value=1,
            max_value=self.config_manager.config.vending.levels,
            on_value_changed=self.on_level_changed
        )
        level_card.add_content(self.level_field)
        self.add_content(level_card)

        # QR preview card
        preview_card = SettingsCard(title="Aktuelle QR Code")

        self.qr_preview = Image(
            size_hint=(1, None),
            height="300dp",
            allow_stretch=True,
            keep_ratio=True
        )
        preview_card.add_content(self.qr_preview)

        # Status label
        self.status_label = MDLabel(
            text="Level 1 (Generiert)",
            halign='center',
            size_hint_y=None,
            height="30dp"
        )
        preview_card.add_content(self.status_label)

        self.add_content(preview_card)

        # Actions card
        actions_card = SettingsCard(title="Aktionen")

        # Generate button
        generate_btn = MDRaisedButton(
            text="QR Code generieren",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=CORAL_ACCENT,
            on_release=self.show_generate_dialog
        )
        actions_card.add_content(generate_btn)

        # Upload button
        upload_btn = MDRaisedButton(
            text="Von USB hochladen",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=NEAR_BLACK,
            on_release=self.open_usb_browser
        )
        actions_card.add_content(upload_btn)

        # Delete custom button
        delete_btn = MDRaisedButton(
            text="Custom QR löschen",
            size_hint=(1, None),
            height="60dp",
            md_bg_color=ERROR_RED,
            on_release=self.delete_custom_qr
        )
        actions_card.add_content(delete_btn)

        self.add_content(actions_card)

        # Initial preview
        self.on_level_changed(1)

    def on_level_changed(self, level: int):
        """Handle level selection change."""
        self.selected_level = level
        self.update_preview()

    def update_preview(self):
        """Update QR code preview for selected level."""
        if self.selected_level is None:
            return

        # Check for custom QR first
        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"
        if custom_path.exists():
            self.qr_preview.source = str(custom_path)
            self.status_label.text = f"Level {self.selected_level} (Custom hochgeladen)"
            return

        # Check for generated QR
        generated_path = self.qr_dir / f"level_{self.selected_level}.png"
        if generated_path.exists():
            self.qr_preview.source = str(generated_path)
            self.status_label.text = f"Level {self.selected_level} (Generiert)"
            return

        # No QR code exists
        self.qr_preview.source = ""
        self.status_label.text = f"Level {self.selected_level} (Kein QR Code)"

    def show_generate_dialog(self, instance):
        """Show dialog to enter payment URL."""
        if self.selected_level is None:
            return

        self.text_input_dialog = TextInputDialog(
            title=f"QR Code für Level {self.selected_level} generieren",
            label="Zahlungslink URL:",
            initial_value=f"https://www.monitoni.zhdk.ch?level={self.selected_level}",
            on_submit=self.generate_qr_from_url
        )
        self.text_input_dialog.open()

    def generate_qr_from_url(self, url: str):
        """Generate QR code from payment URL."""
        if not url or self.selected_level is None:
            return

        try:
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,  # Auto-size
                error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15%
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Save to generated slot
            output_path = self.qr_dir / f"level_{self.selected_level}.png"
            img.save(str(output_path))

            # Update preview
            self.update_preview()

            # Show success
            self.show_success_dialog(f"QR Code für Level {self.selected_level} generiert!")

        except Exception as e:
            self.show_error_dialog(f"Fehler beim Generieren: {str(e)}")

    def open_usb_browser(self, instance):
        """Open file browser for USB drive."""
        if self.selected_level is None:
            return

        # Try user-specific mount point first (Raspberry Pi OS Desktop)
        usb_path = Path("/media") / os.getenv("USER", "admin")
        if usb_path.exists():
            self.file_manager.show(str(usb_path))
        else:
            # Fallback to /media root
            self.file_manager.show("/media")

    def exit_file_manager(self, *args):
        """Called when file manager reaches root."""
        self.file_manager.close()

    def select_qr_file(self, path):
        """Handle file selection from USB."""
        src = Path(path)

        if not src.is_file():
            return

        if src.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
            self.show_error_dialog("Nur PNG/JPG Dateien unterstützt")
            self.file_manager.close()
            return

        try:
            # Copy to custom slot
            dst = self.qr_dir / f"custom_level_{self.selected_level}.png"
            shutil.copy2(src, dst)

            # Update preview
            self.update_preview()

            # Show success
            self.show_success_dialog(f"QR Code für Level {self.selected_level} hochgeladen!")

        except Exception as e:
            self.show_error_dialog(f"Fehler beim Hochladen: {str(e)}")

        self.file_manager.close()

    def delete_custom_qr(self, instance):
        """Delete custom QR code for selected level."""
        if self.selected_level is None:
            return

        custom_path = self.qr_dir / f"custom_level_{self.selected_level}.png"

        if not custom_path.exists():
            self.show_error_dialog("Kein custom QR Code vorhanden")
            return

        # Show confirmation
        dialog = MDDialog(
            title="QR Code löschen?",
            text=f"Custom QR Code für Level {self.selected_level} wirklich löschen?",
            buttons=[
                MDRaisedButton(
                    text="Abbrechen",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDRaisedButton(
                    text="Löschen",
                    md_bg_color=ERROR_RED,
                    on_release=lambda x: self._confirm_delete(dialog, custom_path)
                ),
            ],
        )
        dialog.open()

    def _confirm_delete(self, dialog, path: Path):
        """Confirm deletion and remove file."""
        try:
            path.unlink()
            self.update_preview()
            self.show_success_dialog("Custom QR Code gelöscht")
        except Exception as e:
            self.show_error_dialog(f"Fehler beim Löschen: {str(e)}")
        finally:
            dialog.dismiss()

    def show_success_dialog(self, message: str):
        """Show success message."""
        dialog = MDDialog(
            title="Erfolg",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()

    def show_error_dialog(self, message: str):
        """Show error message."""
        dialog = MDDialog(
            title="Fehler",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    md_bg_color=ERROR_RED,
                    on_release=lambda x: dialog.dismiss()
                ),
            ],
        )
        dialog.open()
```

### Maintenance Mode Screen with Status Display

```python
# monitoni/ui/debug_screens/maintenance_screen.py
"""
Maintenance mode toggle and machine status display.

Allows operators to:
- Enable/disable maintenance mode (blocks purchases)
- View real-time machine status
- See error indicators for hardware issues
"""

from typing import List, Tuple

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDSwitch

from monitoni.ui.debug_screens.base import BaseDebugSubScreen
from monitoni.ui.debug_screens.widgets import (
    SettingsCard,
    LiveStatusCard,
    update_config_value,
    CORAL_ACCENT,
    NEAR_BLACK,
    ERROR_RED,
)
from monitoni.core.config import ConfigManager
from monitoni.hardware.manager import HardwareManager


class MaintenanceScreen(BaseDebugSubScreen):
    """Maintenance mode and machine status screen."""

    def __init__(self, config_manager: ConfigManager, hardware: HardwareManager,
                 navigate_back=None, **kwargs):
        super().__init__(navigate_back=navigate_back, **kwargs)
        self.config_manager = config_manager
        self.hardware = hardware
        self.title = "Wartung & Status"

        self._build_ui()

    def _build_ui(self):
        """Build maintenance screen UI."""
        # Maintenance mode toggle card
        mode_card = SettingsCard(title="Betriebsmodus")

        toggle_row = BoxLayout(
            orientation='horizontal',
            spacing="10dp",
            size_hint_y=None,
            height="60dp"
        )

        toggle_row.add_widget(MDLabel(
            text="Wartungsmodus:",
            size_hint_x=0.7
        ))

        self.maintenance_toggle = MDSwitch()
        # Defer setting active state (KivyMD 1.2.0 quirk)
        current_state = self.config_manager.config.system.maintenance_mode
        Clock.schedule_once(
            lambda dt: setattr(self.maintenance_toggle, 'active', current_state)
        )
        self.maintenance_toggle.bind(on_active=self.on_maintenance_toggle)
        toggle_row.add_widget(self.maintenance_toggle)

        mode_card.add_content(toggle_row)

        # Info label
        info_label = MDLabel(
            text="Im Wartungsmodus ist der Verkauf gesperrt.",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height="30dp"
        )
        mode_card.add_content(info_label)

        self.add_content(mode_card)

        # Machine status card with live updates
        status_card = LiveStatusCard(
            title="Maschinenstatus",
            get_status_callback=self.get_machine_status,
            update_interval=1.0  # Update every second
        )
        self.add_content(status_card)

    def on_maintenance_toggle(self, switch, value):
        """Handle maintenance mode toggle."""
        # Save to config
        success, needs_confirm = update_config_value(
            self.config_manager,
            "system.maintenance_mode",
            value
        )

        if not success:
            # Revert toggle if save failed
            Clock.schedule_once(
                lambda dt: setattr(switch, 'active', not value)
            )
            return

        # Visual feedback
        if value:
            self.show_status("⚠ WARTUNGSMODUS AKTIV - Verkauf gesperrt", ERROR_RED)
        else:
            self.show_status("✓ Wartungsmodus deaktiviert", (0, 1, 0, 1))

    async def get_machine_status(self) -> List[Tuple[str, str, Tuple]]:
        """Get current machine status for LiveStatusCard."""
        items = []

        # Operating mode
        if self.config_manager.config.system.maintenance_mode:
            items.append(("Modus:", "WARTUNG", ERROR_RED))
        else:
            items.append(("Modus:", "Betrieb", (0, 1, 0, 1)))

        # Relay controller
        try:
            relay_connected = await self.hardware.relay.is_connected()
            items.append(("Relais:", "OK" if relay_connected else "FEHLER",
                         (0, 1, 0, 1) if relay_connected else ERROR_RED))
        except Exception:
            items.append(("Relais:", "FEHLER", ERROR_RED))

        # LED controller
        try:
            led_connected = await self.hardware.led.is_connected()
            items.append(("LEDs:", "OK" if led_connected else "OFFLINE",
                         (0, 1, 0, 1) if led_connected else (1, 1, 0, 1)))
        except Exception:
            items.append(("LEDs:", "OFFLINE", (1, 1, 0, 1)))

        # Door sensor
        try:
            door_open = await self.hardware.sensor.is_door_open()
            items.append(("Tür:", "OFFEN" if door_open else "Geschlossen",
                         (1, 1, 0, 1) if door_open else (0.5, 0.5, 0.5, 1)))
        except Exception:
            items.append(("Tür:", "FEHLER", ERROR_RED))

        # Audio
        audio_enabled = self.config_manager.config.hardware.audio.enabled
        items.append(("Audio:", "Aktiv" if audio_enabled else "Deaktiviert",
                     (0, 1, 0, 1) if audio_enabled else (0.5, 0.5, 0.5, 1)))

        return items

    def show_status(self, message: str, color: Tuple):
        """Show temporary status message."""
        # Could add a status label at bottom of screen
        pass  # Implement if needed
```

### Config Schema Addition

```yaml
# config/default.yaml - add to system section
system:
  name: "MoniToni Vending Machine"
  version: "1.0.0"
  machine_id: "VM001"
  maintenance_mode: false  # NEW: Blocks purchases when true
  maintenance_message: "Maschine wird gewartet"  # NEW: German message
```

### Customer Screen Integration (Show Maintenance Message)

```python
# In monitoni/ui/customer_screen.py

def on_enter(self):
    """Called when customer screen becomes active."""
    # Check maintenance mode before showing products
    if self.app_config.system.maintenance_mode:
        self.show_maintenance_message()
        return  # Don't show product selection

    # Normal flow...
    self.show_product_selection()

def show_maintenance_message(self):
    """Display maintenance mode message to customer."""
    # Clear existing content
    self.root_layout.clear_widgets()

    # Show maintenance message
    message_box = BoxLayout(
        orientation='vertical',
        padding="40dp",
        spacing="20dp"
    )

    icon_label = MDLabel(
        text="⚠",
        font_style='H1',
        halign='center',
        theme_text_color='Custom',
        text_color=(1, 1, 0, 1)  # Yellow
    )
    message_box.add_widget(icon_label)

    message_label = MDLabel(
        text=self.app_config.system.maintenance_message,
        font_style='H5',
        halign='center',
        theme_text_color='Primary'
    )
    message_box.add_widget(message_label)

    self.root_layout.add_widget(message_box)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual QR generation offline | Generate in-app from payment URLs | Phase 4 | Operators can update prices without re-printing QR codes |
| Web frontend for config | Touchscreen-only configuration | v0.2 | Machine fully self-sufficient, no laptop needed |
| Manually unplugging machine | Software maintenance mode toggle | Phase 4 | Safer, preserves state, cleaner for customers |
| Static QR codes in customer flow | Dynamic QR loading with custom override | Phase 1 (customer_screen.py) | Supports both generated and uploaded QR codes |

**Deprecated/outdated:**
- N/A - This is new functionality, no deprecated patterns

## Open Questions

Questions that need validation during implementation:

1. **Default QR base URL**
   - What we know: customer_screen.py uses `https://www.monitoni.zhdk.ch`
   - What's unclear: Should this be configurable in settings?
   - Recommendation: Start with hardcoded, add to config in Phase 5 if needed

2. **QR Code Size for Touchscreen**
   - What we know: `box_size=10` is common default
   - What's unclear: Optimal size for 400x1280 vertical touchscreen at typical viewing distance
   - Recommendation: Start with `box_size=10`, add size adjustment slider if too small/large

3. **USB Drive Hot-Plug Detection**
   - What we know: Desktop environment auto-mounts to `/media/username/`
   - What's unclear: Should app detect new USB drives and notify operator?
   - Recommendation: Passive approach - operator opens file manager when ready, simpler and reliable

4. **Maintenance Mode Persistence Across Reboots**
   - What we know: ConfigManager saves to local.yaml which persists across reboots
   - What's unclear: Should maintenance mode auto-disable on reboot for safety?
   - Recommendation: Keep current value across reboots - operator explicitly enables/disables

5. **QR Code Preview Size in File Manager**
   - What we know: MDFileManager has `preview=True` for thumbnails
   - What's unclear: Preview size might be too small to verify QR content
   - Recommendation: After upload, show full-size preview in QR management screen

## Sources

### Primary (HIGH confidence)

- [qrcode · PyPI](https://pypi.org/project/qrcode/) - Official package page with version and parameters
- [Kivy FileChooser Documentation](https://kivy.org/doc/stable/api-kivy.uix.filechooser.html) - Official FileChooser API
- [KivyMD FileManager Documentation](https://kivymd.readthedocs.io/en/latest/components/filemanager/) - Official MDFileManager API
- [KivyMD SelectionControls Documentation](https://kivymd.readthedocs.io/en/latest/components/selectioncontrols/) - MDSwitch usage
- Existing codebase patterns:
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/debug_screens/base.py` - BaseDebugSubScreen
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/debug_screens/widgets.py` - Shared widgets and config helpers
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/customer_screen.py` - Existing QR generation pattern
  - `/home/admin/_DEV/MoniToniVending/monitoni/core/config.py` - ConfigManager with dot-notation
  - `/home/admin/_DEV/MoniToniVending/.claude/projects/-home-admin--DEV-MoniToniVending/memory/kivymd-quirks.md` - KivyMD 1.2.0 gotchas

### Secondary (MEDIUM confidence)

- [Comparison of Python QR Code libraries](https://segno.readthedocs.io/en/stable/comparison-qrcode-libs.html) - Library comparison, verified qrcode as standard
- [Real Python: Generate QR Codes in Python](https://realpython.com/python-generate-qr-code/) - Best practices verified with official docs
- [QR Code Error Correction Explained](https://scanova.io/blog/qr-code-error-correction/) - Error correction levels
- [Raspberry Pi USB Auto-mount Forums](https://forums.raspberrypi.com/viewtopic.php?t=276494) - Community-verified USB mount behavior
- [Mount File Systems Without Root Privileges](https://www.baeldung.com/linux/mount-file-systems-without-root-privileges) - Linux mount permissions

### Tertiary (LOW confidence - community sources)

- [Raspberry Pi USB Drive Mounting Forums](https://forums.raspberrypi.com/viewtopic.php?t=332681) - USB detection patterns
- [Python State Machine Patterns](https://auth0.com/blog/state-pattern-in-python/) - General state pattern info
- [Python pathlib Tips](https://www.inspiredpython.com/tip/python-pathlib-tips-recursively-listing-files-and-directories) - File listing patterns

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - qrcode is proven, KivyMD components already in use, pathlib is stdlib
- Architecture: **HIGH** - Patterns already established in Phase 2, direct reuse
- Pitfalls: **HIGH** - KivyMD quirks documented in project memory, QR pitfalls from official sources
- USB handling: **MEDIUM** - Desktop auto-mount is standard but not tested on this specific Pi setup

**Research date:** 2026-02-06
**Valid until:** 60 days (stable domain - QR generation, file handling, and UI patterns are mature)

**Key dependencies:**
- Phase 2 completion: Requires SettingsCard, NumpadField, update_config_value() helpers
- qrcode library installation: Must add to requirements.txt and install before implementation
- Raspberry Pi OS Desktop: Required for USB auto-mount (or manual mount config if using Lite)

**Implementation readiness:** Ready to plan. All patterns exist, no research gaps, clear integration points identified.
