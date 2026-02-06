# Phase 2: Settings Sub-screens - Research

**Researched:** 2026-02-06
**Domain:** Kivy/KivyMD UI for hardware configuration and testing
**Confidence:** HIGH

## Summary

Phase 2 builds 7 dedicated settings screens for hardware configuration and testing, replacing placeholder sub-screens from Phase 1. Each screen provides full configurability via touchscreen with immediate persistence to YAML config files. The implementation uses KivyMD's Material Design components within the existing Kivy framework, building on Phase 1's established architecture pattern.

The standard approach uses KivyMD cards for grouping related settings, custom numpad widgets for numeric input (avoiding unreliable system keyboards), hold-to-activate button patterns for hardware control, and Clock-based polling for live status displays. PyYAML's safe_dump() handles config persistence with the existing ConfigManager infrastructure.

**Primary recommendation:** Build reusable components (NumpadDialog, HoldButton, LiveStatusWidget, SettingsCard) in a shared widgets module, then compose each sub-screen from these primitives. This matches the BaseDebugSubScreen pattern from Phase 1 and ensures consistency across all 7 screens.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Screen layout & controls:**
- Number input via on-screen numpad (tap field to open numpad, type exact value). No sliders, no steppers.
- Related settings grouped in cards with section headers. Cards provide visual separation between parameter groups.
- Same contemporary/minimal aesthetic as customer screen: coral accent, near-black background, flat design.
- Fixed title bar at top of each screen showing screen name + back arrow. Content scrolls below.

**Test tool interaction:**
- Motor/relay tests: hold-to-activate pattern. Hardware runs only while button is held, releases immediately on finger lift. Safest approach.
- Live status area on each screen showing real-time hardware state (e.g., "Door: CLOSED", "Relay 3: ON").
- LED tests: color controls, zone selection, animation previews, and brightness adjustment. Full test coverage.
- Sensor testing: continuous live readout. Door state updates in real-time as operator opens/closes door.

**Config persistence:**
- Auto-save on change: each value writes to local.yaml immediately. No save button.
- Changes apply to hardware immediately/live as values change. Instant feedback.
- Reset-to-defaults button per screen, restoring factory values for that section only.
- Confirmation dialog for hardware pin changes (GPIO, relay channels, Modbus settings) that could affect communication. All other changes apply without confirmation.

**Screen priority & scope:**
- Build order (highest priority first): Relay > Motor > LED > Sensor > Audio > Network > Stats
- Relay: channel mapping, test individual relays (hold-to-activate), door lock config, cascade test
- Motor: timing parameters (spin_delay_ms, spindle_pre/post_delay_ms), relay channel, test spin (hold)
- LED: brightness, colors, zone mapping, animation previews (idle, purchase, alarm states)
- Sensor: GPIO pin config, pull mode, active state, live continuous door state readout
- Audio: volume control, test sound playback
- Network: server URL, machine ID, timeout values, WiFi status display, IP address display, test connection button
- Stats & Logs: full log viewer with scrollable output, filter by level, export to USB, basic counters (transactions, uptime, last error)

### Claude's Discretion

- Exact card grouping within each screen
- Numpad implementation details
- Loading/transition animations
- Error state presentation in live status area
- How reset-to-defaults confirmation works

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

## Standard Stack

The established libraries/tools for Kivy/KivyMD touchscreen settings interfaces:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| KivyMD | 1.1.1+ | Material Design components | Official Material Design implementation for Kivy, provides MDCard, MDTextField, MDDialog, MDList |
| Kivy | 2.3.1+ | UI framework | Required base framework, provides Clock, Screen, ScrollView, touch events |
| PyYAML | 6.0+ | YAML config read/write | Python standard for YAML, safe_load/safe_dump for config management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | Already in use | Config validation | Already integrated in ConfigManager, no new dependency |
| asyncio | Python stdlib | Hardware command execution | Already used throughout hardware layer |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom numpad widget | System VKeyboard | System keyboard unreliable on embedded Linux, custom widget gives full control |
| Clock.schedule_interval | Threading for updates | Clock is Kivy-native, thread-safe, preferred for UI updates |
| MDDialog | Kivy Popup | MDDialog is Material Design compliant, matches aesthetic |

**Installation:**
No new dependencies required. All components available in current stack.

---

## Architecture Patterns

### Recommended Project Structure
```
monitoni/ui/
├── debug_screens/
│   ├── __init__.py
│   ├── base.py                    # BaseDebugSubScreen (Phase 1)
│   ├── menu_screen.py             # DebugMenuScreen (Phase 1)
│   ├── widgets.py                 # NEW: Shared components
│   ├── relay_screen.py            # NEW: Relay settings & tests
│   ├── motor_screen.py            # NEW: Motor settings & tests
│   ├── led_screen.py              # NEW: LED settings & tests
│   ├── sensor_screen.py           # NEW: Sensor settings & tests
│   ├── audio_screen.py            # NEW: Audio settings & tests
│   ├── network_screen.py          # NEW: Network settings & tests
│   └── stats_screen.py            # NEW: Stats & logs viewer
```

### Pattern 1: Reusable Widget Components

**What:** Create shared components in `widgets.py` that all sub-screens use.

**When to use:** For any UI element that appears on multiple screens (numpad, hold button, status display, settings card).

**Example:**
```python
# Source: Derived from KivyMD best practices and Phase 1 patterns

class NumpadDialog:
    """
    On-screen numeric keypad for number input.
    Opens as modal dialog when text field is tapped.
    """
    def __init__(self, title, on_submit_callback):
        self.dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=self._build_numpad(),
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDRaisedButton(text="OK", on_release=self._on_submit)
            ]
        )

    def _build_numpad(self):
        """Build 3x4 numpad grid with digits 0-9, decimal, backspace."""
        # Grid of buttons: 1-9, 0, ., ← (backspace)
        # Updates display label on button press
        pass

class HoldButton(MDRaisedButton):
    """
    Button that activates on touch_down, deactivates on touch_up.
    Critical for motor/relay safety - hardware only runs while held.
    """
    def __init__(self, on_hold_callback, on_release_callback, **kwargs):
        super().__init__(**kwargs)
        self._holding = False
        self.bind(on_touch_down=self._on_press)
        self.bind(on_touch_up=self._on_release)

    def _on_press(self, instance, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._holding = True
        self.on_hold_callback()
        return True

    def _on_release(self, instance, touch):
        if self._holding:
            self._holding = False
            self.on_release_callback()
        return True

class LiveStatusCard(MDCard):
    """
    Card displaying live hardware status with Clock-based updates.
    Shows current state with colored indicators.
    """
    def __init__(self, get_status_callback, update_interval=0.5, **kwargs):
        super().__init__(**kwargs)
        self.get_status = get_status_callback
        Clock.schedule_interval(self._update, update_interval)

    def _update(self, dt):
        """Called by Clock to refresh status display."""
        status = self.get_status()  # e.g., ("CLOSED", "green")
        self.status_label.text = status[0]
        self.status_label.text_color = status[1]

class SettingsCard(MDCard):
    """
    Card grouping related settings with section header.
    Provides consistent styling and layout.
    """
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = "15dp"
        self.spacing = "10dp"
        self.md_bg_color = (0.15, 0.15, 0.15, 1)  # Near-black
        self.radius = [5, 5, 5, 5]

        # Section header
        header = MDLabel(text=title, font_style='H6')
        self.add_widget(header)
```

### Pattern 2: Screen Structure with BaseDebugSubScreen

**What:** All 7 sub-screens inherit from BaseDebugSubScreen and compose UI from shared widgets.

**When to use:** For every settings sub-screen.

**Example:**
```python
# Source: Phase 1 base.py pattern extended for Phase 2

class RelaySettingsScreen(BaseDebugSubScreen):
    """Relay configuration and testing screen."""

    def __init__(self, hardware, config_manager, **kwargs):
        super().__init__(
            navigate_back=kwargs.pop('navigate_back', None),
            **kwargs
        )
        self.title = "Relay Settings"
        self.hardware = hardware
        self.config = config_manager

        self._build_content()

    def _build_content(self):
        """Build screen content using shared widgets."""

        # Card 1: Hardware Connection
        hw_card = SettingsCard(title="Hardware Connection")
        hw_card.add_widget(self._build_connection_row("Modbus Port", "modbus.port"))
        hw_card.add_widget(self._build_connection_row("Slave Address", "modbus.slave_address"))
        self.add_content(hw_card)

        # Card 2: Individual Relay Tests
        test_card = SettingsCard(title="Test Relays")
        for channel in range(1, 33):
            hold_btn = HoldButton(
                text=f"Relay {channel}",
                on_hold_callback=lambda ch=channel: self._activate_relay(ch),
                on_release_callback=lambda ch=channel: self._deactivate_relay(ch)
            )
            test_card.add_widget(hold_btn)
        self.add_content(test_card)

        # Card 3: Live Status
        status_card = LiveStatusCard(
            get_status_callback=self._get_relay_status,
            update_interval=0.5
        )
        self.add_content(status_card)

    def _build_connection_row(self, label, config_path):
        """Build row with label and editable text field."""
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height="50dp")

        label_widget = MDLabel(text=label)
        row.add_widget(label_widget)

        # Text field that opens numpad on tap
        text_field = MDTextField(
            text=str(self._get_config_value(config_path)),
            readonly=True,  # Force numpad usage
            on_focus=lambda instance, focused: self._open_numpad(config_path) if focused else None
        )
        row.add_widget(text_field)

        return row
```

### Pattern 3: Config Persistence with Auto-Save

**What:** Write to local.yaml immediately when values change, using ConfigManager.save_local().

**When to use:** After every setting change, with optional confirmation for risky changes.

**Example:**
```python
# Source: Existing config.py ConfigManager.save_local() method

def _on_value_changed(self, config_path, new_value):
    """Handle setting change with auto-save."""

    # Check if risky change (GPIO pins, relay channels, Modbus settings)
    if self._is_risky_change(config_path):
        # Show confirmation dialog
        self._show_confirmation_dialog(
            title="Confirm Hardware Change",
            text=f"Changing {config_path} may affect hardware communication. Continue?",
            on_confirm=lambda: self._apply_and_save(config_path, new_value)
        )
    else:
        # Apply immediately
        self._apply_and_save(config_path, new_value)

def _apply_and_save(self, config_path, new_value):
    """Apply change to hardware and save to config."""

    # Build nested dict for config path (e.g., "hardware.modbus.port")
    keys = config_path.split('.')
    update_dict = self._build_nested_dict(keys, new_value)

    # Save to local.yaml (persists immediately)
    self.config.save_local(update_dict)

    # Apply to hardware if needed
    if config_path.startswith("hardware."):
        self._reconnect_hardware_component(config_path)
```

### Pattern 4: Hold-to-Activate for Hardware Control

**What:** Hardware (motors, relays) only runs while button is physically held down.

**When to use:** Any hardware test that could cause physical motion or electrical activation.

**Example:**
```python
# Source: customer_screen.py TurnButton pattern adapted for settings

class MotorTestButton(HoldButton):
    """Hold button for motor testing."""

    def __init__(self, hardware, config, **kwargs):
        super().__init__(
            text="Test Motor",
            on_hold_callback=self._start_motor,
            on_release_callback=self._stop_motor,
            **kwargs
        )
        self.hardware = hardware
        self.config = config

    def _start_motor(self):
        """Start motor sequence (spindle lock + motor)."""
        motor_cfg = self.config.config.vending.motor

        # Open spindle lock
        asyncio.create_task(
            self.hardware.relay.set_relay(motor_cfg.spindle_lock_relay, True)
        )

        # Wait for spindle pre-delay
        Clock.schedule_once(
            lambda dt: asyncio.create_task(
                self.hardware.relay.set_relay(motor_cfg.relay_channel, True)
            ),
            motor_cfg.spindle_pre_delay_ms / 1000.0
        )

    def _stop_motor(self):
        """Stop motor sequence with delays."""
        motor_cfg = self.config.config.vending.motor

        # Keep motor running for spin_delay_ms
        Clock.schedule_once(
            lambda dt: asyncio.create_task(
                self.hardware.relay.set_relay(motor_cfg.relay_channel, False)
            ),
            motor_cfg.spin_delay_ms / 1000.0
        )

        # Close spindle lock after post-delay
        Clock.schedule_once(
            lambda dt: asyncio.create_task(
                self.hardware.relay.set_relay(motor_cfg.spindle_lock_relay, False)
            ),
            (motor_cfg.spin_delay_ms + motor_cfg.spindle_post_delay_ms) / 1000.0
        )
```

### Pattern 5: Live Status with Clock Scheduling

**What:** Use Clock.schedule_interval() to poll hardware state and update UI.

**When to use:** For any real-time status display (door sensor, relay states, network connection).

**Example:**
```python
# Source: Kivy Clock official documentation

class SensorStatusWidget(BoxLayout):
    """Live sensor status display."""

    def __init__(self, hardware, **kwargs):
        super().__init__(**kwargs)
        self.hardware = hardware

        # Status label
        self.status_label = MDLabel(
            text="Door: ---",
            font_style='H5',
            halign='center'
        )
        self.add_widget(self.status_label)

        # Schedule updates every 0.2 seconds
        Clock.schedule_interval(self._update_status, 0.2)

    def _update_status(self, dt):
        """Called by Clock to refresh sensor state."""
        if not self.hardware.sensors or not self.hardware.sensors.is_connected():
            self.status_label.text = "Door: DISCONNECTED"
            self.status_label.text_color = (1, 0, 0, 1)  # Red
            return

        # Get current door state (async call in sync context)
        # Note: Use asyncio.create_task or run_in_executor for async hardware calls
        door_open = asyncio.run_coroutine_threadsafe(
            self.hardware.sensors.get_door_state(),
            asyncio.get_event_loop()
        ).result(timeout=0.1)

        if door_open is None:
            self.status_label.text = "Door: ERROR"
            self.status_label.text_color = (1, 0.5, 0, 1)  # Orange
        elif door_open:
            self.status_label.text = "Door: OPEN"
            self.status_label.text_color = (1, 0.5, 0, 1)  # Orange
        else:
            self.status_label.text = "Door: CLOSED"
            self.status_label.text_color = (0, 1, 0, 1)  # Green
```

### Anti-Patterns to Avoid

- **Using system VKeyboard for numeric input:** Unreliable on embedded Linux, inconsistent layout, can fail to appear. Always use custom numpad dialog.
- **Polling hardware in main thread:** Blocks UI. Use Clock.schedule_interval() with async calls or thread pool.
- **Saving config only on "Save" button:** Goes against user decision for auto-save. Write to local.yaml immediately on change.
- **Testing hardware without hold-to-activate:** Unsafe for motors/relays. Operator must physically hold button to keep hardware active.
- **Hardcoded config values in UI:** Always read from ConfigManager, never duplicate default values in UI code.

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color picker for LED | Custom RGB sliders | Kivy ColorPicker widget | Built-in widget with wheel, sliders, hex input. Full RGBA/HSV support. |
| Log file viewer | Custom text display | MDList with ScrollView or RecycleView | MDList handles dynamic content efficiently. RecycleView for 1000+ lines. |
| Modal confirmation | Custom overlay widget | MDDialog with type="alert" | Material Design compliant, handles backdrop, focus, animations. |
| Async hardware calls from UI | Threading manually | asyncio.create_task() + Clock | Kivy-safe async execution, no race conditions. |
| YAML updates | String manipulation | PyYAML safe_dump with deep merge | Preserves formatting, handles types, prevents injection. |
| Touch event debouncing | Manual timing logic | Clock.schedule_once() cancellation | Built-in Kivy pattern, prevents double-triggers. |

**Key insight:** Kivy/KivyMD provides mature widgets for common UI patterns. Custom solutions for modals, pickers, and lists introduce bugs (memory leaks, touch conflicts, layout issues) that the framework already solved.

---

## Common Pitfalls

### Pitfall 1: Clock Callbacks with Weak References

**What goes wrong:** Clock.schedule_interval() callbacks stop firing after screen is removed from widget tree.

**Why it happens:** Clock uses weak references. If no strong reference exists to callback target, it gets garbage collected.

**How to avoid:** Keep strong reference to callback or use lambda/functools.partial:
```python
# BAD: Method reference may be collected
Clock.schedule_interval(self._update_status, 0.5)

# GOOD: Lambda creates strong reference
self._update_event = Clock.schedule_interval(lambda dt: self._update_status(dt), 0.5)

# Remember to unschedule in cleanup
def on_pre_leave(self):
    if self._update_event:
        self._update_event.cancel()
```

**Warning signs:** Status displays that work initially but stop updating after navigating away and back.

### Pitfall 2: Async Calls from Clock Callbacks

**What goes wrong:** Calling async hardware methods from Clock callbacks causes "no running event loop" errors.

**Why it happens:** Clock callbacks run in main thread. Async calls need event loop.

**How to avoid:** Use asyncio.create_task() if loop exists, or schedule async with asyncio.ensure_future():
```python
# BAD: Direct await in sync callback
def _update_status(self, dt):
    state = await self.hardware.sensors.get_door_state()  # ERROR

# GOOD: Create task for async call
def _update_status(self, dt):
    task = asyncio.create_task(self._async_update())

async def _async_update(self):
    state = await self.hardware.sensors.get_door_state()
    # Update UI with Clock.schedule_once to ensure main thread
    Clock.schedule_once(lambda dt: self._update_ui(state), 0)
```

**Warning signs:** RuntimeError about event loop not running, or status updates that never complete.

### Pitfall 3: MDTextField with readonly=True Still Editable

**What goes wrong:** Setting readonly=True on MDTextField doesn't prevent keyboard input on some platforms.

**Why it happens:** KivyMD's readonly implementation is incomplete for touch events.

**How to avoid:** Use disabled=True or catch on_focus and immediately blur:
```python
# BAD: Assumes readonly prevents input
field = MDTextField(text="123", readonly=True)

# GOOD: Disable or handle focus
field = MDTextField(
    text="123",
    disabled=True,  # Fully prevents input
    hint_text="Tap to edit"
)
# OR catch focus to open custom numpad
field.bind(on_focus=lambda inst, val: self._open_numpad() if val else None)
field.bind(on_focus=lambda inst, val: inst.focus = False)  # Immediate blur
```

**Warning signs:** Users able to type in fields meant to only accept numpad input.

### Pitfall 4: PyYAML safe_dump Loses Comments and Formatting

**What goes wrong:** Calling safe_dump() on config removes all comments and reorders keys.

**Why it happens:** PyYAML doesn't preserve comments or key order by default.

**How to avoid:** Use ruamel.yaml for comment preservation, OR accept that local.yaml is machine-generated:
```python
# Current approach: Accept formatting loss (acceptable for local.yaml)
with open(local_config_path, 'w') as f:
    yaml.dump(local_config, f, default_flow_style=False, sort_keys=False)

# Alternative: Use ruamel.yaml to preserve formatting (adds dependency)
from ruamel.yaml import YAML
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=2, offset=0)
```

**Warning signs:** Local.yaml becomes unreadable, keys in random order, all comments deleted.

### Pitfall 5: Touch Events Not Colliding Correctly with Transparent Widgets

**What goes wrong:** Hold buttons trigger even when touched outside their bounds.

**Why it happens:** Touch events propagate to all widgets unless explicitly checked.

**How to avoid:** Always check collide_point() in on_touch_down/up:
```python
# BAD: Assumes touch is on widget
def on_touch_down(self, touch):
    self.activate_hardware()
    return True

# GOOD: Check collision first
def on_touch_down(self, touch):
    if not self.collide_point(*touch.pos):
        return super().on_touch_down(touch)  # Propagate to parent
    self.activate_hardware()
    return True  # Consume event
```

**Warning signs:** Buttons activating when user touches nearby widgets, or scrolling not working in areas with buttons.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Numpad Dialog Implementation
```python
# Source: KivyMD Dialog patterns + custom numpad logic

class NumpadDialog:
    """
    Modal dialog with numeric keypad for number entry.
    Supports integers and floats with configurable limits.
    """

    def __init__(
        self,
        title: str,
        initial_value: float = 0,
        min_value: float = None,
        max_value: float = None,
        allow_decimal: bool = False,
        on_submit: callable = None
    ):
        self.title = title
        self.value = str(initial_value)
        self.min_value = min_value
        self.max_value = max_value
        self.allow_decimal = allow_decimal
        self.on_submit = on_submit

        # Display label
        self.display = MDLabel(
            text=self.value,
            font_style='H4',
            halign='center',
            size_hint_y=None,
            height='50dp'
        )

        # Numpad grid (3x4)
        numpad = GridLayout(cols=3, spacing='5dp', padding='10dp')

        # Buttons 1-9
        for i in range(1, 10):
            btn = MDRaisedButton(
                text=str(i),
                on_release=lambda x, digit=i: self._append_digit(str(digit))
            )
            numpad.add_widget(btn)

        # Bottom row: decimal, 0, backspace
        if allow_decimal:
            decimal_btn = MDRaisedButton(text=".", on_release=lambda x: self._append_digit("."))
            numpad.add_widget(decimal_btn)
        else:
            numpad.add_widget(Widget())  # Spacer

        zero_btn = MDRaisedButton(text="0", on_release=lambda x: self._append_digit("0"))
        numpad.add_widget(zero_btn)

        back_btn = MDRaisedButton(text="←", on_release=lambda x: self._backspace())
        numpad.add_widget(back_btn)

        # Content container
        content = BoxLayout(orientation='vertical', spacing='10dp')
        content.add_widget(self.display)
        content.add_widget(numpad)

        # Dialog
        self.dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="OK", on_release=lambda x: self._submit())
            ]
        )

    def _append_digit(self, digit: str):
        """Append digit to display."""
        if digit == "." and "." in self.value:
            return  # Only one decimal point

        if self.value == "0" and digit != ".":
            self.value = digit
        else:
            self.value += digit

        self.display.text = self.value

    def _backspace(self):
        """Remove last digit."""
        if len(self.value) > 1:
            self.value = self.value[:-1]
        else:
            self.value = "0"

        self.display.text = self.value

    def _submit(self):
        """Validate and submit value."""
        try:
            num_value = float(self.value)

            # Check bounds
            if self.min_value is not None and num_value < self.min_value:
                # Show error
                return
            if self.max_value is not None and num_value > self.max_value:
                # Show error
                return

            if self.on_submit:
                self.on_submit(num_value)

            self.dialog.dismiss()
        except ValueError:
            # Invalid number - show error
            pass

    def open(self):
        """Show dialog."""
        self.dialog.open()
```

### Config Save with Confirmation
```python
# Source: Existing ConfigManager.save_local() + MDDialog confirmation pattern

def _update_config_value(self, config_path: str, new_value: any):
    """
    Update config value with auto-save and optional confirmation.

    Args:
        config_path: Dot-notation path (e.g., "hardware.modbus.port")
        new_value: New value to set
    """

    # Risky changes that need confirmation
    RISKY_PATHS = [
        "hardware.modbus.port",
        "hardware.modbus.slave_address",
        "hardware.gpio.door_sensor_pin",
        "vending.motor.relay_channel",
        "vending.motor.spindle_lock_relay",
    ]

    def apply_change():
        # Build nested dict from dot-notation path
        keys = config_path.split('.')
        update_dict = {}
        current = update_dict
        for key in keys[:-1]:
            current[key] = {}
            current = current[key]
        current[keys[-1]] = new_value

        # Save to local.yaml (auto-save)
        self.config_manager.save_local(update_dict)

        # Apply to hardware if component is affected
        if config_path.startswith("hardware."):
            self._schedule_hardware_reconnect(config_path)

    # Check if risky change
    if config_path in RISKY_PATHS:
        self._show_confirmation(
            title="Confirm Hardware Change",
            text=f"Changing {config_path} may affect hardware communication.\n\nContinue?",
            on_confirm=apply_change
        )
    else:
        apply_change()

def _show_confirmation(self, title: str, text: str, on_confirm: callable):
    """Show confirmation dialog."""
    dialog = MDDialog(
        title=title,
        text=text,
        buttons=[
            MDFlatButton(text="CANCEL", on_release=lambda x: dialog.dismiss()),
            MDRaisedButton(text="OK", on_release=lambda x: (on_confirm(), dialog.dismiss()))
        ]
    )
    dialog.open()

def _schedule_hardware_reconnect(self, config_path: str):
    """Reconnect hardware component after config change."""
    # Determine which component needs reconnect
    if "modbus" in config_path:
        asyncio.create_task(self.hardware.reconnect_relay())
    elif "wled" in config_path:
        asyncio.create_task(self.hardware.reconnect_led())
    elif "gpio" in config_path:
        asyncio.create_task(self.hardware.reconnect_sensors())
```

### Log Viewer with Scrollable List
```python
# Source: KivyMD MDList patterns + file I/O

class LogViewerWidget(BoxLayout):
    """
    Scrollable log viewer with level filtering.
    Displays logs from monitoni.log file.
    """

    def __init__(self, log_file_path: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.log_file_path = Path(log_file_path)

        # Filter controls
        filter_bar = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')

        self.level_filter = MDRaisedButton(
            text="Filter: ALL",
            on_release=self._show_filter_menu
        )
        filter_bar.add_widget(self.level_filter)

        refresh_btn = MDRaisedButton(
            text="Refresh",
            on_release=lambda x: self._load_logs()
        )
        filter_bar.add_widget(refresh_btn)

        self.add_widget(filter_bar)

        # Scrollable log list
        scroll = ScrollView()

        self.log_list = MDList()
        scroll.add_widget(self.log_list)

        self.add_widget(scroll)

        # Initial load
        self.current_filter = "ALL"
        self._load_logs()

    def _load_logs(self):
        """Load and display log entries."""
        self.log_list.clear_widgets()

        if not self.log_file_path.exists():
            self.log_list.add_widget(
                OneLineListItem(text="Log file not found")
            )
            return

        # Read last 1000 lines
        with open(self.log_file_path, 'r') as f:
            lines = f.readlines()[-1000:]

        # Parse and filter logs
        for line in lines:
            # Parse log line: "2026-02-06 10:30:45 - INFO - Message"
            try:
                parts = line.split(' - ', 2)
                timestamp = parts[0]
                level = parts[1]
                message = parts[2].strip()

                # Apply filter
                if self.current_filter != "ALL" and level != self.current_filter:
                    continue

                # Color based on level
                if level == "ERROR":
                    color = (1, 0, 0, 1)  # Red
                elif level == "WARNING":
                    color = (1, 0.5, 0, 1)  # Orange
                elif level == "INFO":
                    color = (0, 1, 0, 1)  # Green
                else:
                    color = (1, 1, 1, 1)  # White

                # Add to list
                item = TwoLineListItem(
                    text=f"{level}: {message}",
                    secondary_text=timestamp,
                    theme_text_color='Custom',
                    text_color=color
                )
                self.log_list.add_widget(item)

            except Exception:
                continue  # Skip malformed lines

    def _show_filter_menu(self, instance):
        """Show level filter menu."""
        menu_items = [
            {"text": "ALL", "on_release": lambda: self._set_filter("ALL")},
            {"text": "DEBUG", "on_release": lambda: self._set_filter("DEBUG")},
            {"text": "INFO", "on_release": lambda: self._set_filter("INFO")},
            {"text": "WARNING", "on_release": lambda: self._set_filter("WARNING")},
            {"text": "ERROR", "on_release": lambda: self._set_filter("ERROR")},
        ]
        # Use MDDropdownMenu (requires KivyMD)
        # For simplicity, use dialog with buttons
        pass

    def _set_filter(self, level: str):
        """Set log level filter."""
        self.current_filter = level
        self.level_filter.text = f"Filter: {level}"
        self._load_logs()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| System VKeyboard | Custom numpad widgets | Kivy 1.9+ (2015) | Embedded systems have unreliable system keyboards. Custom widgets give full control. |
| Threading for async hardware | asyncio + Clock | Python 3.7+ (2018) | Native async/await is cleaner and safer than manual thread management. |
| Manual YAML parsing | PyYAML safe_load/dump | PyYAML 5.1+ (2019) | safe_load prevents code injection, safe_dump handles types correctly. |
| MDSpinner | MDCircularProgressIndicator | KivyMD 2.0.0 (2025) | Rename for clarity, same functionality. |
| Kivy ListView | RecycleView | Kivy 1.10+ (2017) | RecycleView is vastly more efficient for large lists (1000+ items). |

**Deprecated/outdated:**
- **VKeyboard with custom JSON layouts:** Still works but hard to maintain. Better to build custom numpad as widget composition.
- **Clock.unschedule(callback):** Deprecated in favor of `event.cancel()` where event is return value of schedule_interval.
- **MDSpinner:** Renamed to MDCircularProgressIndicator in KivyMD 2.0.0.

---

## Open Questions

Things that couldn't be fully resolved:

1. **Network status checking without blocking UI**
   - What we know: Can ping server endpoint with requests library, but HTTP requests block UI thread
   - What's unclear: Best pattern for async network checks in Kivy (asyncio with aiohttp? Thread pool?)
   - Recommendation: Use asyncio with aiohttp for async HTTP requests, display status with Clock-updated widget

2. **USB export for logs - device mounting detection**
   - What we know: Can write to /media/usb or /mnt, but need to detect when USB drive is inserted
   - What's unclear: Most reliable method for USB detection on Raspberry Pi (udev rules? polling /dev?)
   - Recommendation: Poll /media and /mnt directories, show available mount points in dialog. Low priority feature.

3. **Exact animation preview implementation for LED screen**
   - What we know: Can run LED animations and display them on hardware, but previewing on touchscreen is complex
   - What's unclear: Worth implementing canvas preview or just use actual hardware LEDs?
   - Recommendation: Skip preview, use actual hardware for animation testing. Add "Run Animation" button that plays on real LEDs.

---

## Sources

### Primary (HIGH confidence)
- [Kivy Clock object documentation](https://kivy.org/doc/stable/api-kivy.clock.html) - Clock.schedule_interval patterns
- [KivyMD Card component](https://kivymd.readthedocs.io/en/1.1.1/components/card/index.html) - MDCard usage for settings groups
- [KivyMD Dialog component](https://kivymd.readthedocs.io/en/1.1.1/components/dialog/index.html) - MDDialog for confirmations and numpad
- [Kivy Button Behavior](https://kivy.org/doc/stable/api-kivy.uix.behaviors.button.html) - Touch event handling for hold buttons
- [KivyMD ScrollView](https://kivymd.readthedocs.io/en/latest/components/scrollview/) - Scrollable content patterns
- [KivyMD List component](https://kivymd.readthedocs.io/en/1.1.1/components/list/index.html) - MDList for log viewer
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) - safe_load/safe_dump usage
- [Kivy ColorPicker](https://kivy.org/doc/stable/api-kivy.uix.colorpicker.html) - RGB color selection widget
- Phase 1 codebase - BaseDebugSubScreen, TurnButton hold-to-activate pattern, StatusCard

### Secondary (MEDIUM confidence)
- [Python YAML best practices](https://betterstack.com/community/guides/scaling-python/yaml-files-in-python/) - Config file management patterns
- [KivyMD Spinner/Progress](https://kivymd.readthedocs.io/en/latest/components/progressindicator/) - Loading indicators (renamed in 2.0)

### Tertiary (LOW confidence)
- Community discussions on numeric keyboard reliability - Consistently report system keyboard issues on embedded Linux

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components in current dependencies, verified in Phase 1
- Architecture: HIGH - Patterns established in Phase 1, extend naturally
- Pitfalls: HIGH - Derived from official docs and known Kivy gotchas
- Open questions: MEDIUM - Network/USB patterns need testing

**Research date:** 2026-02-06
**Valid until:** ~60 days (stable stack, minimal churn in Kivy/KivyMD)
