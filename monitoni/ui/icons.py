"""
Icon font helper for Material Design Icons.

Provides icon character mappings and font registration for Kivy.
"""

from pathlib import Path
from kivy.core.text import LabelBase

# MDI icon code points (subset of commonly used icons)
# Full list: https://pictogrammers.com/library/mdi/
ICONS = {
    # Arrows
    'arrow-left': '\U000F0141',
    'arrow-right': '\U000F0142',
    'arrow-up': '\U000F0143',
    'arrow-down': '\U000F0140',
    'chevron-left': '\U000F0141',
    'chevron-right': '\U000F0142',
    'arrow-left-bold': '\U000F0731',
    'keyboard-backspace': '\U000F030D',
    
    # Actions
    'check': '\U000F012C',
    'close': '\U000F0156',
    'plus': '\U000F0415',
    'minus': '\U000F0374',
    'refresh': '\U000F0450',
    'delete': '\U000F01B4',
    'cancel': '\U000F0156',
    
    # Status
    'circle': '\U000F0765',
    'circle-outline': '\U000F0766',
    'checkbox-blank-circle': '\U000F0130',
    'checkbox-blank-circle-outline': '\U000F0131',
    'record-circle': '\U000F0EC2',
    
    # Settings
    'cog': '\U000F0493',
    'settings': '\U000F0493',
    'wrench': '\U000F0587',
    
    # Common
    'home': '\U000F02DC',
    'menu': '\U000F035C',
    'dots-vertical': '\U000F01D9',
    'information': '\U000F02FC',
    'alert': '\U000F0026',
    'help-circle': '\U000F02D7',
    
    # Media
    'play': '\U000F040A',
    'pause': '\U000F03E4',
    'stop': '\U000F04DB',
    'volume-high': '\U000F057E',
    'volume-low': '\U000F057F',
    
    # Shopping
    'cart': '\U000F0110',
    'qrcode': '\U000F0432',
    'barcode': '\U000F0070',
}

# Font registered flag
_font_registered = False


def register_icon_font():
    """Register the Material Design Icons font with Kivy."""
    global _font_registered
    
    if _font_registered:
        return True
    
    # Look for font in project root assets folder (not relative to this module)
    import os
    project_root = Path(os.getcwd())
    font_path = project_root / "assets" / "fonts" / "materialdesignicons-webfont.ttf"
    
    if not font_path.exists():
        # Fallback: try relative to module
        font_path = Path(__file__).parent.parent / "assets" / "fonts" / "materialdesignicons-webfont.ttf"
        
    if not font_path.exists():
        print(f"[WARNING] Icon font not found: {font_path}")
        return False
        
    try:
        LabelBase.register(
            name='Icons',
            fn_regular=str(font_path)
        )
        _font_registered = True
        print(f"[INFO] Icon font registered: {font_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to register icon font: {e}")
        return False


def get_icon(name: str) -> str:
    """
    Get icon character by name.
    
    Args:
        name: Icon name (e.g., 'arrow-left')
        
    Returns:
        Icon character or empty string if not found
    """
    return ICONS.get(name, '')


def icon_text(icon_name: str, text: str = '', spacing: int = 1) -> str:
    """
    Create text with icon prefix.
    
    Args:
        icon_name: Icon name
        text: Optional text after icon
        spacing: Number of spaces between icon and text
        
    Returns:
        Combined icon and text string
    """
    icon = get_icon(icon_name)
    if text:
        return f"{icon}{' ' * spacing}{text}"
    return icon
