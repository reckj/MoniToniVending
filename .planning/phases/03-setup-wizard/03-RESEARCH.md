# Phase 3: Setup Wizard - Research

**Researched:** 2026-02-06
**Domain:** Multi-step wizard UI in Kivy/KivyMD with first-run detection and in-memory configuration
**Confidence:** HIGH

## Summary

Phase 3 implements a guided first-time setup wizard for vending machine deployment. The wizard detects first run (missing `config/local.yaml`), walks operators through essential configuration in 5 steps (Hardware → LED → Relay → Sensors → Server), and writes all changes atomically on completion. The implementation reuses Phase 2's widget library but creates custom wizard-specific screens optimized for the 400px-wide vertical touchscreen. All configuration is held in memory during the wizard flow to prevent partial configuration on abandonment.

This research established that:
1. Kivy/KivyMD has no built-in wizard/stepper component—custom implementation required
2. Progress dots can be built with BoxLayout + colored Label/MDIcon widgets
3. In-memory state management via dict merging aligns with ConfigManager's existing pattern
4. Atomic YAML writes prevent corruption from crashes or power loss
5. Show/hide pattern for essential vs advanced settings is standard progressive disclosure

**Primary recommendation:** Build custom wizard screens inheriting from Kivy `Screen` (not `BaseDebugSubScreen`) with shared wizard navigation header component. Use dict-based in-memory state merged with defaults, write atomically via tempfile pattern on wizard completion.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Wizard flow & steps:**
- Step order matches roadmap: Hardware (motor/relay) → LED → Relay mapping → Sensors → Server
- Every step is skippable — "Skip" button available on all steps
- Back button on every step for free back-and-forth navigation
- Skipped steps use defaults from default.yaml — machine works with sensible defaults out of the box

**First-run detection:**
- Detection method: check if `config/local.yaml` exists — if missing, it's a first run
- On first-run detection: show prompt dialog "First time setup detected" with two options: "Run Wizard" / "Skip"
- Skip goes straight to customer screen with defaults
- Wizard re-runnable from debug/settings menu ("Run Setup Wizard" button)
- Individual sub-screens also remain accessible separately (both options available)

**Step presentation:**
- Custom wizard screens (not direct reuse of Phase 2 sub-screens, but can pull widgets from Phase 2)
- Step dots progress indicator at top (e.g., filled/unfilled dots)
- Header: step dots + step title + 1-line description + skip and back buttons
- Essential fields shown by default, "Show advanced" toggle to expand additional options per step
- Designed for 400px wide portrait screen

**Completion & testing:**
- Simple "Setup complete!" message, then navigate to customer screen
- No hardware testing in wizard — operator uses debug sub-screens for that
- All config held in memory during wizard, written to local.yaml only when "Finish Setup" is pressed
- If wizard is abandoned (crash, navigate away), nothing is saved — next launch re-detects first-run and re-prompts

### Claude's Discretion

- Exact essential vs advanced field classification per step
- Widget layout within each wizard step
- Step dot styling and positioning
- "Setup complete" screen design
- How wizard re-run from debug menu handles existing config (pre-fill current values)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

The wizard implementation uses the existing project stack plus standard Python patterns for atomic file writes.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | 2.3.0 | Screen management, layouts | Project standard, handles multi-screen navigation |
| KivyMD | 1.2.0 | Material Design widgets | Project standard, provides MDDialog, buttons, labels |
| PyYAML | 6.0+ | YAML parsing/writing | Project standard, used by ConfigManager |
| tempfile | stdlib | Atomic writes | Python standard library, prevents corruption on crash |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os | stdlib | File operations | Atomic rename via `os.replace()` |
| pathlib | stdlib | Path handling | Portable path operations |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom wizard screens | Reuse BaseDebugSubScreen | BaseDebugSubScreen has back button bound to menu navigation, wizard needs different flow |
| Dict-based in-memory state | Pydantic Config object | Dict simpler for partial state, easier to merge with defaults |
| tempfile + os.replace | Direct yaml.dump | Atomic write prevents corruption if power loss during save |

**Installation:**

No new dependencies—all components already in project.

## Architecture Patterns

### Recommended Project Structure

```
monitoni/ui/
├── wizard/
│   ├── __init__.py              # Exports WizardCoordinator
│   ├── coordinator.py           # Manages wizard state and navigation
│   ├── first_run_dialog.py      # "First time setup" prompt dialog
│   ├── wizard_header.py         # Shared header with dots + title + buttons
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── hardware_step.py     # Step 1: Motor/relay timings
│   │   ├── led_step.py          # Step 2: LED config
│   │   ├── relay_map_step.py    # Step 3: Relay channel mapping
│   │   ├── sensor_step.py       # Step 4: GPIO configuration
│   │   ├── server_step.py       # Step 5: Server endpoints
│   │   └── completion_step.py   # Final "Setup complete" screen
│   └── utils.py                 # Atomic YAML write helper
```

### Pattern 1: Wizard Coordinator

**What:** Central class managing wizard state, step navigation, and final save operation.

**When to use:** Multi-step flows where state must accumulate across steps and be committed atomically.

**Example:**
```python
class WizardCoordinator:
    """Manages wizard flow and in-memory configuration state."""

    def __init__(self, config_manager, hardware, on_complete):
        self.config_manager = config_manager
        self.hardware = hardware
        self.on_complete = on_complete

        # In-memory state: dict matching YAML structure
        self.wizard_state = {}

        # Current step index (0-based)
        self.current_step = 0

        # Step screen instances
        self.steps = [
            HardwareStepScreen(self),
            LEDStepScreen(self),
            RelayMapStepScreen(self),
            SensorStepScreen(self),
            ServerStepScreen(self),
        ]

    def update_state(self, path, value):
        """Update wizard state at dot-notation path."""
        # Build nested dict from path (e.g., "hardware.motor.relay_channel")
        parts = path.split('.')
        current = self.wizard_state
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = value
            else:
                current.setdefault(part, {})
                current = current[part]

    def get_state(self, path, default=None):
        """Get wizard state at dot-notation path."""
        parts = path.split('.')
        current = self.wizard_state
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def next_step(self):
        """Navigate to next step or complete wizard."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            return self.steps[self.current_step]
        else:
            return self._complete_wizard()

    def prev_step(self):
        """Navigate to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            return self.steps[self.current_step]
        return None

    def skip_to_completion(self):
        """Skip remaining steps and complete with current state."""
        return self._complete_wizard()

    def _complete_wizard(self):
        """Write wizard state to local.yaml atomically."""
        from monitoni.ui.wizard.utils import atomic_yaml_write

        # Merge wizard state with existing local config (if re-running wizard)
        existing = {}
        if self.config_manager.local_config_path.exists():
            with open(self.config_manager.local_config_path, 'r') as f:
                existing = yaml.safe_load(f) or {}

        merged = self.config_manager._deep_merge(existing, self.wizard_state)

        # Atomic write
        yaml_content = yaml.dump(merged, default_flow_style=False, sort_keys=False)
        atomic_yaml_write(yaml_content, str(self.config_manager.local_config_path))

        # Reload config
        self.config_manager.load()

        # Invoke completion callback
        self.on_complete()
```

### Pattern 2: Wizard Step Screen

**What:** Individual wizard step screen with shared header and step-specific content.

**When to use:** Each wizard step needs consistent navigation UI but custom content.

**Example:**
```python
from kivy.uix.screen import Screen
from kivy.uix.boxlayout import BoxLayout
from monitoni.ui.wizard.wizard_header import WizardHeader

class BaseWizardStep(Screen):
    """Base class for wizard step screens."""

    def __init__(self, coordinator, step_number, step_title, step_description, **kwargs):
        super().__init__(**kwargs)
        self.coordinator = coordinator
        self.step_number = step_number
        self.step_title = step_title
        self.step_description = step_description

        self._build_ui()

    def _build_ui(self):
        """Build wizard step UI with header and content."""
        root = BoxLayout(orientation='vertical', padding="10dp")

        # Shared wizard header
        self.header = WizardHeader(
            total_steps=5,
            current_step=self.step_number,
            title=self.step_title,
            description=self.step_description,
            on_back=self._on_back,
            on_skip=self._on_skip,
            on_next=self._on_next
        )
        root.add_widget(self.header)

        # Scrollable content area
        scroll = ScrollView(size_hint=(1, 1))
        self.content = BoxLayout(
            orientation='vertical',
            spacing="10dp",
            size_hint_y=None,
            padding=("5dp", "10dp")
        )
        self.content.bind(minimum_height=self.content.setter('height'))
        scroll.add_widget(self.content)
        root.add_widget(scroll)

        # Subclass populates content
        self._build_step_content()

        self.add_widget(root)

    def _build_step_content(self):
        """Subclass implements to add step-specific widgets."""
        raise NotImplementedError

    def _on_back(self):
        """Navigate to previous step."""
        prev_screen = self.coordinator.prev_step()
        if prev_screen:
            self.manager.current = prev_screen.name

    def _on_skip(self):
        """Skip to wizard completion."""
        completion_screen = self.coordinator.skip_to_completion()
        self.manager.current = completion_screen.name

    def _on_next(self):
        """Navigate to next step."""
        next_screen = self.coordinator.next_step()
        if next_screen:
            self.manager.current = next_screen.name
```

### Pattern 3: Progress Dots Indicator

**What:** Visual indicator showing current position in multi-step flow.

**When to use:** Wizard or multi-step process needs visual progress feedback.

**Example:**
```python
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.label import MDLabel

class ProgressDots(BoxLayout):
    """Progress indicator with filled/unfilled dots."""

    def __init__(self, total_steps, current_step, **kwargs):
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('height', "30dp")
        kwargs.setdefault('spacing', "5dp")
        super().__init__(**kwargs)

        self.total_steps = total_steps
        self.current_step = current_step

        self._build_dots()
        self.bind(width=self._update_width)

    def _build_dots(self):
        """Build dot indicators."""
        self.clear_widgets()

        for i in range(self.total_steps):
            # Filled dot for current/completed steps, outline for future
            if i < self.current_step:
                # Completed: coral filled circle
                dot = MDLabel(
                    text="●",
                    theme_text_color='Custom',
                    text_color=CORAL_ACCENT,
                    font_style='H6',
                    size_hint=(None, None),
                    size=("30dp", "30dp"),
                    halign='center'
                )
            elif i == self.current_step:
                # Current: larger coral dot
                dot = MDLabel(
                    text="●",
                    theme_text_color='Custom',
                    text_color=CORAL_ACCENT,
                    font_style='H5',  # Larger
                    size_hint=(None, None),
                    size=("30dp", "30dp"),
                    halign='center'
                )
            else:
                # Future: gray outline circle
                dot = MDLabel(
                    text="○",
                    theme_text_color='Custom',
                    text_color=(0.5, 0.5, 0.5, 1),
                    font_style='H6',
                    size_hint=(None, None),
                    size=("30dp", "30dp"),
                    halign='center'
                )

            self.add_widget(dot)

    def _update_width(self, *args):
        """Update total width based on number of dots."""
        self.width = self.total_steps * dp(30) + (self.total_steps - 1) * dp(5)

    def update_step(self, current_step):
        """Update which step is current."""
        self.current_step = current_step
        self._build_dots()
```

### Pattern 4: Expand/Collapse Advanced Settings

**What:** Progressive disclosure pattern showing essential fields by default, advanced on toggle.

**When to use:** Settings screen has core vs power-user options.

**Example:**
```python
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel

class ExpandableSection(BoxLayout):
    """Section that can be expanded/collapsed."""

    def __init__(self, title, **kwargs):
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('spacing', "5dp")
        super().__init__(**kwargs)

        self.is_expanded = False

        # Toggle button
        self.toggle_btn = MDFlatButton(
            text=f"▸ {title}",  # ▸ collapsed, ▾ expanded
            size_hint=(1, None),
            height="40dp",
            on_release=lambda x: self.toggle()
        )
        self.add_widget(self.toggle_btn)

        # Content container (initially hidden)
        self.content_box = BoxLayout(
            orientation='vertical',
            spacing="10dp",
            size_hint_y=None,
            height=0  # Collapsed
        )
        self.content_box.bind(minimum_height=self.content_box.setter('height'))
        self.add_widget(self.content_box)

        self.bind(minimum_height=self.setter('height'))

    def toggle(self):
        """Toggle expanded/collapsed state."""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.toggle_btn.text = self.toggle_btn.text.replace("▸", "▾")
            # Show content
            self.content_box.height = self.content_box.minimum_height
        else:
            self.toggle_btn.text = self.toggle_btn.text.replace("▾", "▸")
            # Hide content
            self.content_box.height = 0

    def add_content(self, widget):
        """Add widget to collapsible content area."""
        self.content_box.add_widget(widget)
```

### Pattern 5: First-Run Detection

**What:** Check for missing `local.yaml` and prompt user to run wizard or skip.

**When to use:** Application start, before main UI loads.

**Example:**
```python
# In VendingApp.build() or on_start()

def check_first_run(self):
    """Check if this is first run and prompt for wizard."""
    config_manager = get_config_manager()

    if not config_manager.local_config_path.exists():
        # First run detected
        self._show_first_run_dialog()
    else:
        # Normal startup
        self.screen_manager.current = 'customer'

def _show_first_run_dialog(self):
    """Show first-run setup prompt."""
    from monitoni.ui.wizard.first_run_dialog import FirstRunDialog

    dialog = FirstRunDialog(
        on_run_wizard=self._start_wizard,
        on_skip=self._skip_wizard
    )
    dialog.open()

def _start_wizard(self):
    """Launch setup wizard."""
    self.screen_manager.current = 'wizard_hardware'  # First step

def _skip_wizard(self):
    """Skip wizard, use defaults."""
    # local.yaml doesn't exist, ConfigManager already loaded defaults
    self.screen_manager.current = 'customer'
```

### Anti-Patterns to Avoid

- **Saving config on each step change:** Breaks atomic write requirement. Hold all changes in memory until "Finish Setup" pressed.
- **Reusing BaseDebugSubScreen for wizard steps:** Navigation flow is different (back = previous step, not menu). Build custom wizard screens.
- **Direct yaml.dump to local.yaml:** Risk corruption on crash/power loss. Always use tempfile + os.replace pattern.
- **Blocking UI during save:** Atomic write is fast (<100ms), but schedule via Clock if needed for large configs.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Manual flush/sync patterns | tempfile + os.replace | Prevents corruption from crash, power loss, or filesystem issues |
| Nested dict updates | Recursive setter functions | ConfigManager's existing `_deep_merge` | Already handles deep merging, tested |
| Step validation | Per-field validators in steps | Skip validation entirely | User decisions: wizard is skippable, defaults work |
| Progress animation | Custom Kivy Animation | Static dots update | Simpler, less code, meets requirement |

**Key insight:** Wizard is about collecting config, not validating hardware. Testing happens in debug sub-screens. Keep wizard lightweight and fast.

## Common Pitfalls

### Pitfall 1: Partial Configuration State on Crash

**What goes wrong:** Writing config incrementally (on each step) leaves machine in inconsistent state if wizard crashes midway.

**Why it happens:** Natural instinct to save progress as user navigates, but wizard must be all-or-nothing.

**How to avoid:** Hold all changes in dict (`wizard_state`) during flow. Only write to `local.yaml` on explicit "Finish Setup" action. If wizard abandoned (crash, navigate away), dict discarded and next launch re-detects first-run.

**Warning signs:** Config file grows or changes during wizard navigation, before completion screen.

### Pitfall 2: File Corruption from Non-Atomic Writes

**What goes wrong:** Direct `yaml.dump()` to `local.yaml` can leave partial/corrupted file if process killed mid-write (power loss, OS kill, crash).

**Why it happens:** Writing directly to target file is not atomic—file is modified in-place over time.

**How to avoid:** Write to temp file first, flush/sync, then `os.replace()` atomically swaps temp file with target. If crash happens before replace, original file unchanged. If crash during replace, OS guarantees atomicity.

**Warning signs:** Corrupted or empty `local.yaml` after power loss during wizard completion.

### Pitfall 3: Wizard State Leaking Between Sessions

**What goes wrong:** Wizard state persists between runs, pre-filling old values when user re-runs wizard.

**Why it happens:** Storing wizard state as class attribute or global without reset.

**How to avoid:** For first-run wizard, start with empty dict. For re-run from debug menu, pre-fill from current `local.yaml` (ConfigManager already loaded). Make distinction clear in coordinator initialization.

**Warning signs:** User skips wizard, then re-runs later and sees previous session's incomplete values.

### Pitfall 4: KivyMD 1.2.0 MDSwitch Active State Crash

**What goes wrong:** Setting `active=True` in MDSwitch constructor crashes with `'super' object has no attribute '__getattr__'`.

**Why it happens:** KivyMD 1.2.0 quirk—`on_active` fires before KV layout exists, accessing `self.ids.thumb` too early.

**How to avoid:** Defer active state with `Clock.schedule_once(lambda dt: setattr(toggle, 'active', value))` (see `kivymd-quirks.md`).

**Warning signs:** Wizard crashes when building step with toggle switches set to True.

### Pitfall 5: Hardcoding Step Count

**What goes wrong:** Step dots, navigation logic, and completion check all hardcode "5 steps"—fragile if steps added/removed.

**Why it happens:** Wizard flow seems fixed, but requirements change.

**How to avoid:** Coordinator's `self.steps` list is source of truth. Derive step count from `len(self.steps)`. Pass to progress dots as `total_steps=len(coordinator.steps)`.

**Warning signs:** Adding a step requires editing multiple files (coordinator, header, dots widget).

## Code Examples

Verified patterns from research and codebase analysis:

### Atomic YAML Write

```python
# Source: https://gist.github.com/therightstuff/cbdcbef4010c20acc70d2175a91a321f
# Adapted for monitoni wizard

import tempfile
import os
import yaml

def atomic_yaml_write(yaml_content: str, target_path: str):
    """
    Write YAML content to file atomically.

    Args:
        yaml_content: YAML string to write
        target_path: Target file path (e.g., "config/local.yaml")
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (avoid cross-filesystem issues)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=target_path.parent,
        prefix='.tmp_',
        suffix='.yaml'
    )

    try:
        # Write content to temp file
        with os.fdopen(temp_fd, 'w') as f:
            f.write(yaml_content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomically replace target with temp
        os.replace(temp_path, target_path)

    finally:
        # Clean up temp file if replace failed
        if os.path.exists(temp_path):
            os.unlink(temp_path)
```

### Reusing Phase 2 Widgets in Wizard

```python
# Wizard step can use NumpadField, SettingsCard, etc.

from monitoni.ui.debug_screens.widgets import (
    NumpadField,
    SettingsCard,
    CORAL_ACCENT,
    NEAR_BLACK
)

class HardwareStepScreen(BaseWizardStep):
    """Step 1: Hardware configuration (motor/relay timings)."""

    def __init__(self, coordinator, **kwargs):
        super().__init__(
            coordinator=coordinator,
            step_number=0,  # 0-indexed
            step_title="Hardware Setup",
            step_description="Configure motor and relay timings",
            **kwargs
        )

    def _build_step_content(self):
        """Build hardware config fields."""
        # Essential settings card
        essential_card = SettingsCard(title="Essential Settings")

        # Motor relay channel (essential)
        motor_channel = NumpadField(
            label="Motor Relay Channel",
            config_path="vending.motor.relay_channel",
            config_manager=self.coordinator.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=16,
            on_value_changed=lambda v: self.coordinator.update_state(
                "vending.motor.relay_channel", int(v)
            )
        )
        essential_card.add_content(motor_channel)

        # Spindle lock relay (essential)
        spindle_lock = NumpadField(
            label="Spindle Lock Relay",
            config_path="vending.motor.spindle_lock_relay",
            config_manager=self.coordinator.config_manager,
            allow_decimal=False,
            min_value=1,
            max_value=16,
            on_value_changed=lambda v: self.coordinator.update_state(
                "vending.motor.spindle_lock_relay", int(v)
            )
        )
        essential_card.add_content(spindle_lock)

        self.content.add_widget(essential_card)

        # Advanced settings (collapsible)
        advanced_section = ExpandableSection(title="Show Advanced Settings")

        # Timing fields in advanced
        spin_delay = NumpadField(
            label="Spin Delay (ms)",
            config_path="vending.motor.spin_delay_ms",
            config_manager=self.coordinator.config_manager,
            allow_decimal=False,
            min_value=0,
            max_value=5000,
            on_value_changed=lambda v: self.coordinator.update_state(
                "vending.motor.spin_delay_ms", int(v)
            )
        )
        advanced_section.add_content(spin_delay)

        self.content.add_widget(advanced_section)
```

### First-Run Dialog

```python
# Source: widgets.py show_confirm_dialog pattern, adapted for wizard

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton

class FirstRunDialog:
    """Dialog prompting user to run wizard or skip."""

    def __init__(self, on_run_wizard, on_skip):
        self.on_run_wizard = on_run_wizard
        self.on_skip = on_skip

        self.dialog = MDDialog(
            title="First Time Setup Detected",
            text="This appears to be the first time this vending machine has been started.\n\n"
                 "Would you like to run the setup wizard to configure hardware and server settings?",
            buttons=[
                MDFlatButton(
                    text="SKIP",
                    on_release=lambda x: self._on_skip()
                ),
                MDRaisedButton(
                    text="RUN WIZARD",
                    md_bg_color=CORAL_ACCENT,
                    on_release=lambda x: self._on_run_wizard()
                ),
            ],
        )

    def open(self):
        """Open the dialog."""
        self.dialog.open()

    def _on_run_wizard(self):
        """Handle Run Wizard button."""
        self.dialog.dismiss()
        if self.on_run_wizard:
            self.on_run_wizard()

    def _on_skip(self):
        """Handle Skip button."""
        self.dialog.dismiss()
        if self.on_skip:
            self.on_skip()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual multi-page forms | Wizard with progress indicators | Modern UX (2010s+) | Users see progress, less anxiety about long flows |
| Save-as-you-go config | Atomic commit on completion | Transaction pattern | Prevents partial/corrupted state |
| Single long form | Essential + "Show advanced" toggle | Progressive disclosure | Reduces cognitive load, works on narrow screens |
| Direct file writes | Tempfile + atomic replace | UNIX best practice | Prevents corruption from crashes |

**Deprecated/outdated:**
- **Django-style session wizards:** For web apps, not applicable to Kivy desktop apps. Pattern still valid (in-memory state, commit on finish) but implementation differs.
- **KivyMD Stepper component:** Does not exist in KivyMD 1.2.0. Custom implementation required.

## Open Questions

Things that couldn't be fully resolved:

1. **Should wizard re-run from debug menu start with current config pre-filled, or empty state?**
   - What we know: User decisions specify wizard is re-runnable from debug menu. No specification whether to pre-fill.
   - What's unclear: UX preference—pre-filling shows current state but might confuse if user expects "fresh" wizard.
   - Recommendation: Pre-fill from current `local.yaml` when re-running. Allows editing existing config without re-entering all values. Mark in UI "Current: X" or similar to clarify.

2. **How to handle wizard abandonment detection?**
   - What we know: If wizard abandoned (crash, navigate away), nothing is saved. Next launch re-detects first-run.
   - What's unclear: Should there be explicit "Exit Wizard" button, or just rely on back button to menu?
   - Recommendation: No explicit exit—wizard screens can be navigated away from via back button to menu. State is in-memory dict, garbage collected. Simple and aligns with "skippable" philosophy.

3. **Should completion screen show config summary before final save?**
   - What we know: User decisions specify simple "Setup complete!" message, navigate to customer screen.
   - What's unclear: Whether to show "Configured: X channels, Y endpoints" summary.
   - Recommendation: Skip summary. User can review in debug sub-screens if needed. Keeps wizard fast and lightweight.

## Sources

### Primary (HIGH confidence)

- **Codebase analysis:**
  - `/home/admin/_DEV/MoniToniVending/config/default.yaml` - Configuration structure and defaults
  - `/home/admin/_DEV/MoniToniVending/monitoni/core/config.py` - ConfigManager implementation, `_deep_merge` pattern
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/debug_screens/widgets.py` - Phase 2 widget library (NumpadField, SettingsCard, etc.)
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/debug_screens/base.py` - BaseDebugSubScreen pattern
  - `/home/admin/_DEV/MoniToniVending/monitoni/ui/app.py` - Screen manager and navigation
  - `/home/admin/.claude/projects/-home-admin--DEV-MoniToniVending/memory/kivymd-quirks.md` - KivyMD 1.2.0 known issues

- **Atomic file writes:**
  - https://gist.github.com/therightstuff/cbdcbef4010c20acc70d2175a91a321f - Safe atomic file writes for JSON and YAML in Python 3

### Secondary (MEDIUM confidence)

- **Wizard UI best practices:**
  - https://lollypop.design/blog/2026/january/wizard-ui-design/ - High-conversion wizard UI design patterns (2026)
  - https://www.eleken.co/blog-posts/wizard-ui-pattern-explained - When to use wizard UI pattern
  - https://www.eleken.co/blog-posts/stepper-ui-examples - 32 stepper UI examples

- **Touchscreen UI:**
  - https://parachutedesign.ca/blog/touchscreen-interface-design-best-practices/ - Touchscreen interface design best practices
  - https://www.newvisiondisplay.com/ui-design-touch-screen-displays/ - UI design for touch screen displays

- **Progressive disclosure (expand/collapse):**
  - https://pixso.net/tips/expand-collapse-ui-design/ - Expand/collapse UI design patterns
  - https://uxpatterns.dev/patterns/content-management/accordion - Accordion pattern for settings

- **Configuration management:**
  - https://django-formtools.readthedocs.io/en/latest/wizard.html - Django form wizard (pattern applicable to Python)
  - https://ibm.github.io/data-science-best-practices/configuration_management.html - Configuration management best practices

### Tertiary (LOW confidence)

- **KivyMD progress indicators:**
  - https://kivymd.readthedocs.io/en/latest/components/progressindicator/ - KivyMD progress indicator docs (no stepper component found)
  - https://github.com/kivymd/KivyMD/wiki/Components-Progress-indicator - KivyMD wiki on progress indicators

- **PyYAML:**
  - https://python.land/data-processing/python-yaml - Python YAML guide
  - https://realpython.com/python-yaml/ - YAML: The Missing Battery in Python

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components already in project, no new dependencies
- Architecture: HIGH - Patterns verified against codebase (Phase 1/2), atomic write researched with authoritative source
- Pitfalls: HIGH - Derived from user decisions (atomic commit, no incremental save) and KivyMD quirks doc
- UI patterns: MEDIUM - General UX best practices verified, but Kivy-specific stepper examples scarce (custom implementation required)

**Research date:** 2026-02-06
**Valid until:** 60 days (stable domain—wizard UX patterns and file I/O don't change rapidly)
