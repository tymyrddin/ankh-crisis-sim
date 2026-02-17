"""Centralized theme — paper & ink steampunk aesthetic with IM Fell English."""

from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

PAPER = "#eddab9"          # main background — warm parchment
PAPER_DARK = "#ddc8a0"     # slightly darker for card/frame backgrounds
PAPER_LIGHT = "#f5e8d0"    # lighter variant for hover highlights
INK = "#1a1a1a"            # primary text colour
INK_MUTED = "#5a4a3a"      # secondary / subdued text
ACCENT_BROWN = "#8b6914"   # warm accent for headers, dividers
BORDER = "#c4a86a"         # subtle frame borders

# Status colours (kept vivid for readability on paper)
STATUS_GREEN = "#2e7d32"
STATUS_YELLOW = "#f9a825"
STATUS_RED = "#c62828"
STATUS_RESPONDING = "#e68a00"  # amber — remedy in progress

# Metric colours (warm-shifted to suit paper)
METRIC_COLOURS = {
    "public_trust": "#2e7d32",
    "budget": "#1565c0",
    "regulatory_pressure": "#e65100",
    "political_stability": "#6a1b9a",
    "legitimacy": "#ad1457",
}

# Trust thresholds
TRUST_GOOD = "#2e7d32"
TRUST_WARN = "#e65100"
TRUST_BAD = "#c62828"


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

_FONT_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "fonts"
_FONT_FAMILY = "IM Fell English"
_FONT_LOADED = False


def _register_fonts() -> bool:
    """Register bundled fonts via fontconfig (Linux) so Tk can find them."""
    global _FONT_LOADED
    if _FONT_LOADED:
        return True

    font_dir = str(_FONT_DIR)
    if not os.path.isdir(font_dir):
        return False

    # Linux: Tk uses fontconfig under the hood
    lib_name = ctypes.util.find_library("fontconfig")
    if lib_name:
        try:
            fc = ctypes.cdll.LoadLibrary(lib_name)
            fc.FcConfigAppFontAddDir.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            fc.FcConfigAppFontAddDir.restype = ctypes.c_bool
            fc.FcConfigAppFontAddDir(None, font_dir.encode())
            _FONT_LOADED = True
            return True
        except OSError:
            pass

    return False


def load_fonts() -> str:
    """Load bundled fonts and return the family name to use.

    Falls back to a sensible serif if loading fails.
    """
    if _register_fonts():
        return _FONT_FAMILY
    # Fallback: common serif fonts
    return "Georgia"


# ---------------------------------------------------------------------------
# Font tuples (call after load_fonts())
# ---------------------------------------------------------------------------

def fonts(family: str | None = None) -> _Fonts:
    """Return a namespace of font tuples for the given family."""
    return _Fonts(family or load_fonts())


class _Fonts:
    """Convenience holder for font tuples used across the GUI."""

    def __init__(self, family: str):
        self.family = family
        self.title = (family, 24, "bold")
        self.subtitle = (family, 13)
        self.heading = (family, 15, "bold")
        self.body = (family, 13)
        self.body_bold = (family, 13, "bold")
        self.small = (family, 11)
        self.small_bold = (family, 11, "bold")
        self.clock = (family, 15, "bold")