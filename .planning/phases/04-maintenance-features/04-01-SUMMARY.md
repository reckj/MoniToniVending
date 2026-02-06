# Phase 04 Plan 01: QR Code Management Summary

**One-liner:** QR code generation from URLs and USB upload with custom precedence using qrcode library and MDFileManager

---

## Performance

- **Duration:** 3 minutes
- **Completed:** 2026-02-06
- **Tasks:** 2/2 (100%)
- **Deviations:** 1 (see below)

---

## What Was Accomplished

### Objective
Built the QR Code Management screen that allows operators to generate QR codes from payment URLs, upload custom QR images from USB drives, preview QR codes per level, and delete custom QR codes.

### Delivered
1. **QR Code Dependency** - Added `qrcode[pil]>=8.0` to requirements.txt (fixing missing dependency for customer_screen.py)
2. **QR Management Screen** - Full-featured screen with:
   - Level selection (1-N) via NumpadDialog
   - QR code preview (300dp image with status label)
   - Generate QR from URL (TextInputDialog with default URL pattern)
   - Upload QR from USB (MDFileManager with image preview)
   - Delete custom QR (confirmation dialog with ERROR_RED styling)
   - Custom QR precedence pattern (custom_level_N.png > level_N.png)

### Key Features
- **ERROR_CORRECT_M** - 15% error correction for reliable scanning (not ERROR_CORRECT_L)
- **German UI** - All labels in German ("QR Code Verwaltung", "Von USB hochladen", etc.)
- **USB Auto-mount Detection** - Tries `/media/$USER/` first, fallback to `/media/`
- **Image Reload Pattern** - Clears source then sets it via Clock.schedule_once for reliable preview updates
- **File Precedence** - Custom files (`custom_level_N.png`) take precedence over generated (`level_N.png`)

---

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add qrcode dependency | 351865e | requirements.txt |
| 2 | Create QR Management Screen | b34d5a9 | monitoni/ui/debug_screens/qr_management_screen.py |

---

## Files Created

- `monitoni/ui/debug_screens/qr_management_screen.py` - QR management screen (442 lines)

---

## Files Modified

- `requirements.txt` - Added qrcode[pil]>=8.0 dependency

---

## Decisions Made

1. **NumpadDialog over NumpadField for level selection** - NumpadField requires config_path and auto-saves to config, which is inappropriate for transient level selection. Used NumpadDialog directly with manual button update.

2. **ERROR_CORRECT_M (15%) over ERROR_CORRECT_L (7%)** - Higher error correction for better scanning reliability, per research recommendations. Customer_screen.py uses ERROR_CORRECT_L but this is a bug that should be fixed separately.

3. **Image reload via Clock.schedule_once** - Kivy Image widget requires source="", delay, then source=path pattern to force reload when file content changes.

4. **Constructor parameter order** - Followed existing codebase pattern `(hardware, config_manager, navigate_back, **kwargs)` despite plan suggesting reversed order. Consistency with audio_screen.py, relay_screen.py, etc.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] NumpadField requires config_path**
- **Found during:** Task 2 - building level selection card
- **Issue:** Plan specified using NumpadField for level selection, but NumpadField is designed for config persistence and requires a config_path parameter. Level selection is transient UI state that shouldn't be saved to config.
- **Fix:** Used NumpadDialog directly with a manual button that opens the dialog and updates its own text on submission. This follows the same pattern as NumpadField's internal implementation but without config persistence.
- **Files modified:** qr_management_screen.py
- **Commit:** b34d5a9 (same commit as Task 2, inline fix)

---

## Issues Encountered

None - plan executed smoothly with one inline deviation.

---

## Next Phase Readiness

### Ready for Phase 04-02
- QR management screen is complete and importable
- qrcode dependency properly declared in requirements.txt
- Pattern established for standalone screens that don't require hardware
- Custom QR precedence pattern validated against customer_screen.py

### Integration Notes
- QR management screen needs to be added to debug screen menu navigation
- customer_screen.py could benefit from upgrading ERROR_CORRECT_L to ERROR_CORRECT_M (but out of scope for this plan)
- USB mount detection tested on development environment but should be verified on actual Raspberry Pi hardware

### Blockers
None identified.

---

## Metadata

**Phase:** 04-maintenance-features
**Plan:** 01
**Subsystem:** ui-maintenance
**Tags:** qr-code, usb-upload, kivy, kivymd, maintenance, touchscreen

**Requires:**
- Phase 01: BaseDebugSubScreen, SettingsCard, NumpadDialog, TextInputDialog
- Phase 02: Widget library patterns (CORAL_ACCENT, NEAR_BLACK, ERROR_RED, INPUT_BUTTON)

**Provides:**
- QR code generation from payment URLs
- USB file upload for custom QR images
- QR preview per product level
- Custom QR deletion with confirmation

**Affects:**
- Phase 04-02: Menu integration for QR management screen
- Phase 05: Hardware testing of USB auto-mount on Raspberry Pi

**Tech Stack Added:**
- qrcode[pil]>=8.0 (QR code generation library)

**Tech Stack Patterns:**
- MDFileManager for USB file browsing
- Image reload via Clock.schedule_once
- NumpadDialog for transient numeric input

**Key Files:**
- Created: monitoni/ui/debug_screens/qr_management_screen.py
- Modified: requirements.txt

**Key Decisions:**
- Use NumpadDialog directly instead of NumpadField for level selection
- ERROR_CORRECT_M for QR generation (15% correction)
- Custom QR precedence pattern (custom_level_N.png > level_N.png)
- Image reload pattern via source clearing and Clock scheduling

---

## Self-Check: PASSED

All files verified:
- monitoni/ui/debug_screens/qr_management_screen.py

All commits verified:
- 351865e
- b34d5a9
