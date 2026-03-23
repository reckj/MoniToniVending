"""
Full-screen maintenance display shown when machine is in maintenance mode.

Blocks all customer interaction. Provides same 5-tap debug access
in top-right corner so operators can reach settings to disable maintenance.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Triangle
from kivymd.uix.label import MDLabel

from monitoni.core.config import get_config_manager


class MaintenanceDisplayScreen(Screen):
    """
    Full-screen maintenance mode display.

    Shows maintenance message and provides hidden debug access.
    """

    def __init__(self, app, logger, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.logger = logger
        self._debug_tap_count = 0
        self._debug_tap_timeout = None
        self._build_ui()

    def _build_ui(self):
        outer = FloatLayout()

        # Centered message layout
        layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            padding=("30dp", "40dp", "30dp", "40dp"),
        )

        # Push content to center
        layout.add_widget(Widget(size_hint_y=1))

        # Maintenance icon text
        icon_label = MDLabel(
            text="!",
            halign='center',
            font_style='H1',
            size_hint_y=None,
            height="80dp",
            theme_text_color='Custom',
            text_color=(242 / 255, 64 / 255, 51 / 255, 1),
        )
        layout.add_widget(icon_label)

        # Main message
        self.message_label = MDLabel(
            text="Machine under maintenance",
            halign='center',
            font_style='H5',
            size_hint_y=None,
            height="60dp",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.9),
        )
        layout.add_widget(self.message_label)

        # Sub-message
        sub_label = MDLabel(
            text="Please try again later",
            halign='center',
            font_style='Body1',
            size_hint_y=None,
            height="40dp",
            theme_text_color='Custom',
            text_color=(1, 1, 1, 0.4),
        )
        layout.add_widget(sub_label)

        # Push content to center
        layout.add_widget(Widget(size_hint_y=1))

        outer.add_widget(layout)

        # Subtle debug indicator triangle in top-right corner
        indicator = _DebugIndicator()
        outer.add_widget(indicator)

        # Invisible touch area for debug access (same as customer screen)
        debug_touch = Button(
            background_color=(0, 0, 0, 0),
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'right': 1, 'top': 1},
        )
        debug_touch.bind(on_press=self._on_debug_tap)
        outer.add_widget(debug_touch)

        self.add_widget(outer)

    def on_enter(self):
        """Update message from config when screen is shown."""
        try:
            msg = get_config_manager().config.system.maintenance_message
            self.message_label.text = msg
        except Exception:
            pass

    def _on_debug_tap(self, instance):
        self._debug_tap_count += 1
        if self._debug_tap_timeout:
            self._debug_tap_timeout.cancel()
        self._debug_tap_timeout = Clock.schedule_once(
            lambda dt: setattr(self, '_debug_tap_count', 0), 2.0
        )
        if self._debug_tap_count >= 5:
            self.logger.info("Debug mode accessed from maintenance screen")
            self._debug_tap_count = 0
            self.app.switch_to_debug()


class _DebugIndicator(Widget):
    """Subtle triangle indicator in top-right corner."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (30, 30)
        self.pos_hint = {'right': 1, 'top': 1}
        with self.canvas:
            Color(1, 1, 1, 0.15)
            self.triangle = Triangle(points=[
                self.x + self.width, self.y + self.height,
                self.x + self.width, self.y,
                self.x, self.y + self.height,
            ])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.triangle.points = [
            self.x + self.width, self.y + self.height,
            self.x + self.width, self.y,
            self.x, self.y + self.height,
        ]
