"""Settings popup: lets the player adjust game options at any time."""

from __future__ import annotations

import customtkinter as ctk

from src.config.loader import GameSettings
from src.gui.theme import (
    ACCENT_BROWN, INK, INK_MUTED, PAPER, PAPER_DARK, fonts,
)


# ---------------------------------------------------------------------------
# Option maps: display label → value
# ---------------------------------------------------------------------------

_DURATION_OPTIONS: list[tuple[str, int]] = [
    ("1 Year",   365),
    ("2 Years",  730),
    ("4 Years", 1460),
]

_EVENT_RATE_OPTIONS: list[tuple[str, float]] = [
    ("Quiet",   0.15),
    ("Normal",  0.30),
    ("Active",  0.50),
    ("Frantic", 0.80),
]

_DISCOVERY_OPTIONS: list[tuple[str, float]] = [
    ("Immediate", 0.5),
    ("Normal",    1.0),
    ("Delayed",   1.5),
    ("Buried",    2.5),
]

_CASCADE_OPTIONS: list[tuple[str, float]] = [
    ("Low",    0.5),
    ("Normal", 1.0),
    ("High",   1.5),
    ("Severe", 2.5),
]


def _labels(opts) -> list[str]:
    return [label for label, _ in opts]


def _closest_label(opts, current_value) -> str:
    return min(opts, key=lambda x: abs(x[1] - current_value))[0]


def _value_for_label(opts, label):
    for lbl, val in opts:
        if lbl == label:
            return val
    return opts[0][1]


# ---------------------------------------------------------------------------
# SettingsPopup
# ---------------------------------------------------------------------------

class SettingsPopup:
    """Modal panel for adjusting runtime game settings."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._overlay: ctk.CTkToplevel | None = None

    def show(self, settings: GameSettings) -> None:
        if self._overlay and self._overlay.winfo_exists():
            self._overlay.lift()
            return

        f = fonts()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 500, 480
        px = (sw - w) // 2
        py = (sh - h) // 2

        win = ctk.CTkToplevel(self.root)
        win.title("Game Settings")
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.resizable(False, False)
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._close)
        win.after(50, win.grab_set)
        self._overlay = win

        # --- Masthead ---
        masthead = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        masthead.pack(fill="x")
        ctk.CTkLabel(
            masthead,
            text="GAME SETTINGS",
            font=(f.family, 17, "bold"), text_color=INK,
        ).pack(side="left", padx=24, pady=14)
        ctk.CTkLabel(
            masthead,
            text="PATRICIAN'S OFFICE",
            font=f.small_bold, text_color=ACCENT_BROWN,
        ).pack(side="right", padx=24, pady=14)

        ctk.CTkLabel(
            win,
            text="Changes take effect immediately. The city does not wait.",
            font=f.small, text_color=INK_MUTED,
        ).pack(anchor="w", padx=24, pady=(10, 4))

        ctk.CTkFrame(win, fg_color=ACCENT_BROWN, height=2).pack(
            fill="x", padx=24, pady=(0, 0)
        )

        # --- Scrollable settings area ---
        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        _row(scroll, f, "GAME DURATION",
             "How long the Patrician's term lasts before the verdict.",
             _labels(_DURATION_OPTIONS),
             _closest_label(_DURATION_OPTIONS, settings.game_duration_days),
             lambda v: setattr(settings, "game_duration_days",
                               _value_for_label(_DURATION_OPTIONS, v)))

        _row(scroll, f, "EVENT FREQUENCY",
             "How often infrastructure decides to have a crisis.",
             _labels(_EVENT_RATE_OPTIONS),
             _closest_label(_EVENT_RATE_OPTIONS, settings.event_rate_multiplier),
             lambda v: setattr(settings, "event_rate_multiplier",
                               _value_for_label(_EVENT_RATE_OPTIONS, v)))

        _row(scroll, f, "DISCOVERY SPEED",
             "How quickly failures become known to the authorities.",
             _labels(_DISCOVERY_OPTIONS),
             _closest_label(_DISCOVERY_OPTIONS, settings.discovery_speed_multiplier),
             lambda v: setattr(settings, "discovery_speed_multiplier",
                               _value_for_label(_DISCOVERY_OPTIONS, v)))

        _row(scroll, f, "CASCADE RISK",
             "How likely one failure is to drag others down with it.",
             _labels(_CASCADE_OPTIONS),
             _closest_label(_CASCADE_OPTIONS, settings.cascade_multiplier),
             lambda v: setattr(settings, "cascade_multiplier",
                               _value_for_label(_CASCADE_OPTIONS, v)))

        ctk.CTkFrame(scroll, fg_color="transparent", height=8).pack()

        # --- Close (outside scroll, always visible) ---
        ctk.CTkButton(
            win,
            text="Close",
            command=self._close,
            width=160, font=(f.family, 13, "bold"),
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=12)

    def _close(self) -> None:
        if self._overlay:
            self._overlay.grab_release()
            self._overlay.destroy()
            self._overlay = None


# ---------------------------------------------------------------------------
# Row helper: title + hint + option menu
# ---------------------------------------------------------------------------

def _row(parent, f, title: str, hint: str,
         options: list[str], current: str, command) -> None:
    """One setting: label + hint text + dropdown menu."""
    ctk.CTkLabel(
        parent, text=title,
        font=f.small_bold, text_color=ACCENT_BROWN,
    ).pack(anchor="w", padx=24, pady=(8, 0))

    ctk.CTkLabel(
        parent, text=hint,
        font=f.small, text_color=INK_MUTED,
        wraplength=450, justify="left",
    ).pack(anchor="w", padx=24, pady=(1, 4))

    var = ctk.StringVar(value=current)
    ctk.CTkOptionMenu(
        parent,
        variable=var,
        values=options,
        command=command,
        width=200,
        font=f.small_bold,
        fg_color=PAPER_DARK,
        button_color=ACCENT_BROWN,
        button_hover_color="#a07a1a",
        text_color=INK,
        dropdown_fg_color=PAPER,
        dropdown_text_color=INK,
        dropdown_hover_color=PAPER_DARK,
    ).pack(anchor="w", padx=24, pady=(0, 4))