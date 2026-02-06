"""
Debug menu screen - navigation hub for debug sub-screens.

Displays a list of component categories with icons for easy navigation.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList, TwoLineIconListItem, IconLeftWidget


class DebugMenuScreen(Screen):
    """
    Main navigation menu for debug sub-screens.

    Displays a list of 7 component categories, each tappable to navigate
    to its dedicated sub-screen.
    """

    # Menu items: (screen_name, icon, title, subtitle)
    MENU_ITEMS = [
        ('led', 'led-strip', 'LED Control', 'Brightness, colors, animations, zones'),
        ('relay', 'toggle-switch', 'Relay Control', 'Test relays, channel mapping'),
        ('sensor', 'door-sensor', 'Sensors', 'Door status, GPIO configuration'),
        ('audio', 'volume-high', 'Audio', 'Volume, test sounds'),
        ('motor', 'engine', 'Motor Settings', 'Timings, delays, test functions'),
        ('network', 'server-network', 'Network/Server', 'Endpoints, connection status'),
        ('stats', 'chart-bar', 'Statistics & Logs', 'View stats, export logs'),
    ]

    def __init__(self, navigate_callback=None, back_to_customer_callback=None, **kwargs):
        """
        Initialize the debug menu screen.

        Args:
            navigate_callback: Callback invoked with screen_name when menu item tapped
            back_to_customer_callback: Callback invoked when Exit button pressed
            **kwargs: Additional arguments passed to Screen
        """
        super().__init__(**kwargs)

        self.navigate_callback = navigate_callback
        self.back_to_customer_callback = back_to_customer_callback
        self._build_ui()

    def _build_ui(self):
        """Build the menu screen UI."""
        # Root layout
        root = BoxLayout(
            orientation='vertical',
            padding="10dp",
            spacing="10dp"
        )

        # Header with Exit button and title
        header = BoxLayout(
            size_hint=(1, None),
            height="60dp",
            spacing="10dp"
        )

        exit_btn = MDRaisedButton(
            text="< Exit",
            size_hint=(None, None),
            size=("100dp", "50dp"),
            on_release=self._on_exit_pressed
        )
        header.add_widget(exit_btn)

        title_label = MDLabel(
            text="Debug & Settings",
            font_style='H5',
            valign='center'
        )
        header.add_widget(title_label)

        root.add_widget(header)

        # Scrollable menu list
        scroll = ScrollView(size_hint=(1, 1))

        menu_list = MDList()

        for screen_name, icon, title, subtitle in self.MENU_ITEMS:
            item = TwoLineIconListItem(
                text=title,
                secondary_text=subtitle,
                on_release=lambda x, name=screen_name: self._on_item_pressed(name)
            )

            icon_widget = IconLeftWidget(icon=icon)
            item.add_widget(icon_widget)

            menu_list.add_widget(item)

        scroll.add_widget(menu_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def _on_exit_pressed(self, instance):
        """Handle Exit button press."""
        if self.back_to_customer_callback:
            self.back_to_customer_callback()

    def _on_item_pressed(self, screen_name):
        """Handle menu item press."""
        if self.navigate_callback:
            self.navigate_callback(screen_name)
