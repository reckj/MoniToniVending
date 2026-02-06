# Phase 1: Debug Screen Architecture - Research

**Researched:** 2026-02-06
**Domain:** Kivy/KivyMD Screen Navigation and Sub-screen Architecture
**Confidence:** HIGH

## Summary

This phase converts the existing single-scroll debug screen into a navigation hub with dedicated sub-screens for each component category (LED, Relay, Sensors, Audio, Motor, Network, Statistics/Logs). The research focused on Kivy ScreenManager patterns, KivyMD list-based navigation menus, back navigation implementation, and performance considerations for touchscreen devices.

The existing codebase already uses Kivy 2.3.1 and KivyMD 1.2.0 with a working ScreenManager setup in `app.py`. The debug screen (`debug_screen.py`) currently builds 7 sections as `SectionCard` widgets in a single `ScrollView`. The recommended approach is to use a nested ScreenManager within the debug screen space, with MDList-based menu items for navigation and explicit back navigation handling (since Kivy lacks built-in navigation stack).

**Primary recommendation:** Use a dedicated `DebugScreenManager` (nested ScreenManager) to manage sub-screens within the debug area, with `OneLineIconListItem` menu items on the hub screen and explicit "Back" buttons on each sub-screen that return to the menu.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| kivy | 2.3.1 | UI framework | Already in use, provides ScreenManager |
| kivymd | 1.2.0 | Material Design components | Already in use, provides MDList, list items, icons |

### Components to Use
| Component | From Package | Purpose | Why Use |
|-----------|--------------|---------|---------|
| ScreenManager | kivy.uix.screenmanager | Manage sub-screens | Built-in navigation, supports transitions |
| Screen | kivy.uix.screenmanager | Base class for sub-screens | Standard pattern for screen-based navigation |
| SlideTransition | kivy.uix.screenmanager | Screen transitions | Best performance on touchscreens (not shader-based) |
| MDList | kivymd.uix.list | Menu container | Material Design list, auto-sizing |
| OneLineIconListItem | kivymd.uix.list | Menu items | Icon + text, touch events built-in |
| IconLeftWidget | kivymd.uix.list | Menu item icons | Standard icon placement |
| ScrollView | kivy.uix.scrollview | Scrollable content | Works well with MDList |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ScreenManager | Widget swapping (add/remove) | ScreenManager provides transitions, screen lifecycle events |
| OneLineIconListItem | MDRaisedButton grid | List items more compact, better for narrow screen |
| SlideTransition | FadeTransition | Shader transitions cause performance issues on some hardware |
| Nested ScreenManager | Single shared ScreenManager | Nesting keeps debug sub-screens isolated from main app screens |

**Installation:** No additional packages needed - all required components are in kivy 2.3.1 and kivymd 1.2.0.

## Architecture Patterns

### Recommended Project Structure
```
monitoni/ui/
    app.py                    # Main app with top-level ScreenManager
    customer_screen.py        # Customer-facing screen (unchanged)
    debug_screen.py           # Debug hub screen with nested ScreenManager
    debug_screens/            # NEW: Sub-screen modules
        __init__.py
        base.py               # BaseDebugSubScreen class
        led_screen.py         # LED control sub-screen
        relay_screen.py       # Relay control sub-screen
        sensor_screen.py      # Sensor monitoring sub-screen
        audio_screen.py       # Audio control sub-screen
        motor_screen.py       # Motor settings sub-screen
        network_screen.py     # Network/Server sub-screen
        stats_screen.py       # Statistics & Logs sub-screen
```

### Pattern 1: Nested ScreenManager for Sub-screens
**What:** Use a ScreenManager within the DebugScreen to manage sub-screens independently from the main app's customer/debug switching.
**When to use:** When a screen needs internal navigation without affecting parent navigation.
**Example:**
```python
# Source: Kivy ScreenManager documentation pattern
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition

class DebugScreen(Screen):
    """Debug hub with nested screen management."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create nested screen manager for sub-screens
        self.sub_screen_manager = ScreenManager(
            transition=SlideTransition(direction='left')
        )

        # Add menu screen as default
        self.menu_screen = DebugMenuScreen(name='menu')
        self.sub_screen_manager.add_widget(self.menu_screen)

        # Add sub-screens
        self.sub_screen_manager.add_widget(LEDScreen(name='led'))
        self.sub_screen_manager.add_widget(RelayScreen(name='relay'))
        # ... more sub-screens

        self.add_widget(self.sub_screen_manager)

    def navigate_to(self, screen_name: str):
        """Navigate to a sub-screen."""
        self.sub_screen_manager.transition.direction = 'left'
        self.sub_screen_manager.current = screen_name

    def navigate_back(self):
        """Return to menu."""
        self.sub_screen_manager.transition.direction = 'right'
        self.sub_screen_manager.current = 'menu'
```

### Pattern 2: MDList-based Navigation Menu
**What:** Use KivyMD's MDList with clickable list items for the navigation hub.
**When to use:** For compact, touch-friendly menu interfaces on narrow screens.
**Example:**
```python
# Source: KivyMD 1.1.1 List documentation
from kivymd.uix.list import MDList, OneLineIconListItem, IconLeftWidget
from kivy.uix.scrollview import ScrollView

class DebugMenuScreen(Screen):
    """Menu hub listing all debug sub-screens."""

    def __init__(self, debug_manager, **kwargs):
        super().__init__(**kwargs)
        self.debug_manager = debug_manager

        layout = BoxLayout(orientation='vertical')

        # Header
        layout.add_widget(self._build_header())

        # Scrollable menu
        scroll = ScrollView()
        menu_list = MDList()

        # Menu items with icons
        menu_items = [
            ('led', 'led-strip', 'LED Control'),
            ('relay', 'toggle-switch', 'Relay Control'),
            ('sensor', 'door-sensor', 'Sensors'),
            ('audio', 'volume-high', 'Audio'),
            ('motor', 'engine', 'Motor Settings'),
            ('network', 'server-network', 'Network/Server'),
            ('stats', 'chart-bar', 'Statistics & Logs'),
        ]

        for screen_name, icon, title in menu_items:
            item = OneLineIconListItem(
                text=title,
                on_release=lambda x, s=screen_name: self.debug_manager.navigate_to(s)
            )
            item.add_widget(IconLeftWidget(icon=icon))
            menu_list.add_widget(item)

        scroll.add_widget(menu_list)
        layout.add_widget(scroll)
        self.add_widget(layout)
```

### Pattern 3: Base Sub-Screen with Back Navigation
**What:** Create a base class for sub-screens that provides consistent header with back button.
**When to use:** All sub-screens need consistent navigation UI.
**Example:**
```python
# Source: Custom pattern based on Kivy best practices
class BaseDebugSubScreen(Screen):
    """Base class for debug sub-screens with consistent header."""

    title = StringProperty("Sub-Screen")

    def __init__(self, debug_manager, **kwargs):
        super().__init__(**kwargs)
        self.debug_manager = debug_manager

        self.main_layout = BoxLayout(orientation='vertical', padding="10dp")

        # Header with back button
        header = BoxLayout(size_hint=(1, None), height="60dp", spacing="10dp")

        back_btn = MDRaisedButton(
            text="< Back",
            size_hint=(None, None),
            size=("100dp", "50dp"),
            on_release=lambda x: self.debug_manager.navigate_back()
        )
        header.add_widget(back_btn)

        title_label = MDLabel(
            text=self.title,
            font_style='H5',
            valign='center'
        )
        header.add_widget(title_label)

        self.main_layout.add_widget(header)

        # Content area (subclasses add to this)
        self.content = BoxLayout(orientation='vertical', spacing="10dp")
        self.main_layout.add_widget(self.content)

        self.add_widget(self.main_layout)
```

### Anti-Patterns to Avoid
- **Mixing switch_to() and current property:** Don't use both methods simultaneously - causes animation conflicts
- **Shader transitions on embedded devices:** FadeTransition, WipeTransition can cause performance issues and black screens on Raspberry Pi
- **Modifying current_screen directly:** Always use the `current` property, never set `current_screen`
- **Creating screens on navigation:** Pre-create all sub-screens at startup to avoid lag on touchscreen
- **Hardcoded back navigation targets:** Use a manager reference instead of hardcoding screen names

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screen management | Custom widget swapping | ScreenManager | Handles transitions, screen lifecycle, memory |
| Clickable list items | Custom touch handling | OneLineIconListItem | Built-in ripple effect, touch events, Material Design |
| Icon rendering | Custom icon loading | IconLeftWidget + md_icons | 5000+ Material Design icons built-in |
| Scroll containers | Custom scroll logic | ScrollView + MDList | Proper touch handling, momentum scrolling |
| Screen transitions | Manual animation | SlideTransition | Smooth, performant, configurable |

**Key insight:** KivyMD already provides Material Design components optimized for touch. Using built-in components ensures consistent behavior and avoids touch event handling bugs.

## Common Pitfalls

### Pitfall 1: Performance Lag on Screen Navigation
**What goes wrong:** Screen transitions feel sluggish on Raspberry Pi touchscreen.
**Why it happens:** Widget creation during navigation, shader-based transitions.
**How to avoid:**
1. Pre-create all sub-screens at debug screen initialization
2. Use SlideTransition (non-shader) instead of FadeTransition
3. Consider NoTransition if slide is still slow
**Warning signs:** Visible pause when tapping menu items, transition animations dropping frames.

### Pitfall 2: Navigation Stack Not Tracked
**What goes wrong:** Back button doesn't work correctly, or navigates to wrong screen.
**Why it happens:** Kivy ScreenManager has no built-in navigation history.
**How to avoid:**
1. Keep navigation simple: menu -> sub-screen -> menu (no deeper nesting)
2. All sub-screens navigate back to 'menu' explicitly
3. Don't rely on previous() method for back navigation in complex flows
**Warning signs:** Back button goes to unexpected screen, navigation feels unpredictable.

### Pitfall 3: PIN Protection Bypass on Sub-screens
**What goes wrong:** Sub-screens accessible after PIN timeout or app backgrounding.
**Why it happens:** PIN check only on DebugScreen.on_enter(), sub-screens don't re-check.
**How to avoid:**
1. Keep PIN check at DebugScreen level (already exists)
2. PIN dialog shows when entering debug area, not individual sub-screens
3. Exiting to customer screen and returning always re-prompts PIN
**Warning signs:** User can access debug functions without PIN after idle timeout.

### Pitfall 4: RelativeLayout Coordinate Issues
**What goes wrong:** Widgets positioned incorrectly on sub-screens.
**Why it happens:** Screen is a RelativeLayout; child coordinates are relative to screen, not parent widgets.
**How to avoid:**
1. Use BoxLayout as the root layout inside each Screen
2. Avoid absolute positioning within screens
3. Use size_hint and padding instead of pos
**Warning signs:** Widgets overlap, appear off-screen, or don't resize with window.

### Pitfall 5: Async Callbacks from Wrong Screen
**What goes wrong:** Hardware callbacks update UI after navigating away from sub-screen.
**Why it happens:** Async operations (sensor polling, relay tests) complete after screen transition.
**How to avoid:**
1. Check `self.manager.current == self.name` before UI updates in async callbacks
2. Cancel async tasks on screen exit (on_leave)
3. Use weak references for callbacks that might outlive the screen
**Warning signs:** UI updates appear on wrong screen, crashes when accessing removed widgets.

## Code Examples

Verified patterns from official sources:

### Creating Menu Screen with MDList
```python
# Source: KivyMD List documentation + Kivy ScreenManager docs
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.list import MDList, OneLineIconListItem, IconLeftWidget
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton

class DebugMenuScreen(Screen):
    """Navigation hub for debug sub-screens."""

    # Menu configuration: (screen_name, icon, display_text)
    MENU_ITEMS = [
        ('led', 'led-strip', 'LED Control', 'Brightness, colors, animations, zones'),
        ('relay', 'toggle-switch', 'Relay Control', 'Test relays, channel mapping'),
        ('sensor', 'door-sensor', 'Sensors', 'Door status, GPIO configuration'),
        ('audio', 'volume-high', 'Audio', 'Volume, test sounds'),
        ('motor', 'engine', 'Motor Settings', 'Timings, delays, test functions'),
        ('network', 'server-network', 'Network/Server', 'Endpoints, connection status'),
        ('stats', 'chart-bar', 'Statistics & Logs', 'View stats, export logs'),
    ]

    def __init__(self, navigate_callback, back_to_customer_callback, **kwargs):
        super().__init__(**kwargs)
        self.navigate_callback = navigate_callback
        self.back_to_customer = back_to_customer_callback
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding="10dp", spacing="10dp")

        # Header with back to customer button
        header = BoxLayout(size_hint=(1, None), height="60dp", spacing="10dp")

        back_btn = MDRaisedButton(
            text="< Exit",
            size_hint=(None, None),
            size=("100dp", "50dp"),
            on_release=lambda x: self.back_to_customer()
        )
        header.add_widget(back_btn)

        title = MDLabel(
            text="Debug & Settings",
            font_style='H5',
            valign='center'
        )
        header.add_widget(title)
        layout.add_widget(header)

        # Menu list
        scroll = ScrollView(size_hint=(1, 1))
        menu_list = MDList()

        for screen_name, icon, title, subtitle in self.MENU_ITEMS:
            # Use TwoLineIconListItem for subtitle
            from kivymd.uix.list import TwoLineIconListItem
            item = TwoLineIconListItem(
                text=title,
                secondary_text=subtitle,
                on_release=lambda x, s=screen_name: self.navigate_callback(s)
            )
            item.add_widget(IconLeftWidget(icon=icon))
            menu_list.add_widget(item)

        scroll.add_widget(menu_list)
        layout.add_widget(scroll)

        self.add_widget(layout)
```

### Migrating Existing Section to Sub-Screen
```python
# Source: Pattern based on existing debug_screen.py structure
class LEDScreen(BaseDebugSubScreen):
    """LED control sub-screen - migrated from SectionCard."""

    title = "LED Control"

    def __init__(self, hardware, app_config, logger, **kwargs):
        self.hardware = hardware
        self.app_config = app_config
        self.logger = logger
        self.current_brightness = 0.8
        super().__init__(**kwargs)
        self._build_content()

    def _build_content(self):
        """Build LED controls - adapted from _create_led_section."""
        # Brightness slider (reuse LargeSlider from existing code)
        self.brightness_slider = LargeSlider(
            label_text="Brightness",
            min_val=0,
            max_val=1,
            default_val=self.current_brightness,
            on_change=self._on_brightness_change
        )
        self.content.add_widget(self.brightness_slider)

        # Color buttons (same as existing)
        # Animation buttons (same as existing)
        # Zone mapping (same as existing)
```

### Handling Screen Lifecycle
```python
# Source: Kivy Screen documentation
class SensorScreen(BaseDebugSubScreen):
    """Sensor monitoring with proper lifecycle management."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_task = None

    def on_enter(self):
        """Start sensor updates when screen becomes visible."""
        self._update_task = asyncio.create_task(self._update_loop())

    def on_leave(self):
        """Stop sensor updates when leaving screen."""
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None

    async def _update_loop(self):
        """Periodic sensor status update."""
        while True:
            # Safety check - stop if we're no longer the current screen
            if self.manager and self.manager.current != self.name:
                break

            await self._update_sensor_display()
            await asyncio.sleep(1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single scroll debug view | Sub-screen navigation | This phase | Better usability on narrow touchscreen |
| FadeTransition default | SlideTransition for embedded | Kivy 2.x | Avoids shader issues on Pi |
| MDExpansionPanel sections | Dedicated sub-screens | This phase | Cleaner navigation, no overlap bugs |

**Deprecated/outdated:**
- MDExpansionPanel for settings: Current code mentions "overlap issues" - sub-screens are cleaner
- Shader-based transitions on embedded: FadeTransition/WipeTransition can cause black screens

## Open Questions

Things that couldn't be fully resolved:

1. **KivyMD 1.2.0 vs 2.0 API differences**
   - What we know: KivyMD 2.0 changed list item API significantly (MDListItem vs OneLineListItem)
   - What's unclear: Exact API surface for 1.2.0 (between 1.1.1 docs and 2.0 docs)
   - Recommendation: Use 1.1.1 patterns (OneLineIconListItem, TwoLineIconListItem) - confirmed working in existing codebase

2. **Optimal number of pre-loaded screens**
   - What we know: Pre-loading screens improves performance, but uses memory
   - What's unclear: Memory impact of 7+ sub-screens on Raspberry Pi 5
   - Recommendation: Pre-load all 7 sub-screens - Pi 5 has 4-8GB RAM, Kivy screens are lightweight

3. **Async task cleanup patterns**
   - What we know: Existing code uses `asyncio.create_task()` for hardware operations
   - What's unclear: Whether tasks are properly cancelled when leaving debug screen entirely
   - Recommendation: Add explicit cleanup in on_leave() for long-running tasks

## Sources

### Primary (HIGH confidence)
- [Kivy 2.3.1 ScreenManager Documentation](https://kivy.org/doc/stable/api-kivy.uix.screenmanager.html) - Screen management patterns, transitions
- [KivyMD 1.1.1 List Documentation](https://kivymd.readthedocs.io/en/1.1.1/components/list/index.html) - MDList, list item classes
- Existing codebase analysis (`debug_screen.py`, `app.py`, `customer_screen.py`) - Current patterns and constraints

### Secondary (MEDIUM confidence)
- [Kivy GitHub Issue #7964](https://github.com/kivy/kivy/issues/7964) - Back navigation discussion and patterns
- [Kivy Performance Optimization Guide](https://gist.github.com/Guhan-SenSam/9dfb11b7bfd8fd24561f4fcd9ff0d5de) - Widget creation, lazy loading strategies
- [Kivy Navigation Tutorial](https://www.techwithtim.net/tutorials/kivy-tutorial/multiple-screens) - Multi-screen patterns

### Tertiary (LOW confidence)
- Various web search results about KivyMD navigation patterns - Community patterns, may not match version 1.2.0 exactly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing dependencies, verified in requirements.txt
- Architecture: HIGH - Based on official Kivy ScreenManager docs and existing codebase patterns
- Pitfalls: MEDIUM - Based on GitHub issues and community reports, may need validation on target hardware

**Research date:** 2026-02-06
**Valid until:** 2026-03-06 (30 days - stable libraries, patterns well-established)
