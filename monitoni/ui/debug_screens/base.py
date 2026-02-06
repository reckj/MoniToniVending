"""
Base class for debug sub-screens.

Provides consistent header with back button and scrollable content area.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton

from monitoni.ui.debug_screens.widgets import CORAL_ACCENT


class BaseDebugSubScreen(Screen):
    """
    Base class for all debug sub-screens.

    Provides:
    - Consistent header with back button and title
    - Scrollable content area
    - navigate_back callback for returning to menu

    Subclasses should use add_content() to add their widgets.
    """

    title = StringProperty("Sub-Screen")

    def __init__(self, navigate_back=None, **kwargs):
        """
        Initialize the debug sub-screen.

        Args:
            navigate_back: Callback to invoke when back button is pressed
            **kwargs: Additional arguments passed to Screen
        """
        super().__init__(**kwargs)

        self.navigate_back = navigate_back
        self._build_ui()

    def _build_ui(self):
        """Build the sub-screen UI with header and scrollable content."""
        # Root layout
        root = BoxLayout(
            orientation='vertical',
            padding="10dp"
        )

        # Header row with back button and title
        header = BoxLayout(
            size_hint=(1, None),
            height="60dp",
            spacing="10dp"
        )

        back_btn = MDRaisedButton(
            text="< Back",
            size_hint=(None, None),
            size=("80dp", "50dp"),
            md_bg_color=CORAL_ACCENT,
            on_release=self._on_back_pressed
        )
        header.add_widget(back_btn)

        title_label = MDLabel(
            text=self.title,
            font_style='H5',
            halign='center',
            valign='center',
            size_hint_y=None,
            height="50dp"
        )
        title_label.bind(size=title_label.setter('text_size'))
        # Bind title property to label text for dynamic updates
        self.bind(title=title_label.setter('text'))
        header.add_widget(title_label)

        root.add_widget(header)

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

        self.add_widget(root)

    def _on_back_pressed(self, instance):
        """Handle back button press."""
        if self.navigate_back:
            self.navigate_back()

    def add_content(self, widget):
        """
        Add a widget to the content area.

        Args:
            widget: The widget to add to the scrollable content
        """
        self.content.add_widget(widget)
