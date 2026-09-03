from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path


PAPER = "#eddab9"  # parchment
PAPER_DARK = "#ddc8a0"  # cards and frames
PAPER_LIGHT = "#f5e8d0"  # hover
INK = "#1a1a1a"
INK_MUTED = "#5a4a3a"
ACCENT_BROWN = "#8b6914"  # headers and dividers
BORDER = "#c4a86a"

# kept vivid so they read on paper
STATUS_GREEN = "#2e7d32"
STATUS_YELLOW = "#f9a825"
STATUS_RED = "#c62828"
STATUS_RESPONDING = "#e68a00"  # amber

METRIC_COLOURS = {
    "public_trust": "#2e7d32",
    "budget": "#1565c0",
    "regulatory_pressure": "#e65100",
    "political_stability": "#6a1b9a",
    "legitimacy": "#ad1457",
    "public_health": "#00695c",
    "crime_level": "#b71c1c",
}

TRUST_GOOD = "#2e7d32"
TRUST_WARN = "#e65100"
TRUST_BAD = "#c62828"


_FONT_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "fonts"
_FONT_FAMILY = "IM Fell English"
_FONT_LOADED = False


def _register_fonts() -> bool:
    """Point fontconfig at the bundled fonts so Tk can see them. Linux only."""
    global _FONT_LOADED
    if _FONT_LOADED:
        return True

    font_dir = str(_FONT_DIR)
    if not os.path.isdir(font_dir):
        return False

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
    if _register_fonts():
        return _FONT_FAMILY
    return "Georgia"


def fonts(family: str | None = None) -> _Fonts:
    return _Fonts(family or load_fonts())


class _Fonts:
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