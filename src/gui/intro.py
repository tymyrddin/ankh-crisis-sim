from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.gui.theme import (
    ACCENT_BROWN, INK, INK_MUTED, PAPER, PAPER_DARK,
    STATUS_GREEN, STATUS_YELLOW, STATUS_RED, STATUS_RESPONDING, fonts,
)


# in the voice of the Patrician's Office
_SECTIONS: list[tuple[str, str]] = [
    (
        "The City",
        "The map to your left is Ankh-Morpork. Every lamp represents a building. "
        "Their colour tells you everything you need to know at a glance:\n\n"
        "  ●  Green: operational. For now.\n"
        "  ●  Yellow: degraded. Attention recommended.\n"
        "  ●  Red: failed. This is already someone's fault.\n"
        "  ●  Amber: a response is in progress.\n\n"
        "Click any lamp to open a full briefing on that building: what it depends on, "
        "what depends on it, and what you can do about the current situation. "
        "Hover for a quick summary.",
    ),
    (
        "Incidents",
        "When something fails and the Watch (or someone) notices, the game pauses "
        "and presents you with a report. Read it. The building description tells you "
        "what is at stake. The dependency list tells you what else will suffer.\n\n"
        "You are not required to act immediately. You are, however, required to "
        "accept the consequences of not acting. These tend to arrive punctually.",
    ),
    (
        "Responding",
        "With an incident open, you will find a list of responses at the bottom. "
        "Each has a cost, a resolution time, and a different relationship with "
        "the concept of 'actually fixing the problem'.\n\n"
        "  Emergency Repair: fast, cheap, recurs.\n"
        "  Structural Upgrade: slow, expensive, lasting.\n"
        "  Workaround: maintains appearances at someone else's expense.\n"
        "  Compensation: buys goodwill, changes nothing.\n"
        "  Inquiry: assigns blame, generates paperwork, fixes nothing.\n"
        "  Press Statement: narrative management. Best paired with action.\n"
        "  Do Nothing: a legitimate policy. Not a popular one.\n\n"
        "The budget is real. When it runs out, your options narrow considerably.",
    ),
    (
        "The Dashboard",
        "The panel on the right tracks the city's vital signs. Colours shift from "
        "green through yellow and orange to red as conditions deteriorate. "
        "Click any metric or district for a detailed briefing.\n\n"
        "Public Trust is the most important number you are not directly in control of. "
        "Regulatory Pressure rises when problems go unaddressed and falls, slowly, "
        "when they do not. Political Stability will hold until it does not.\n\n"
        "Crime Level and Public Health respond to what you do or fail to do. "
        "Legitimacy moves slowly in both directions and is considerably easier to lose "
        "than to recover.",
    ),
    (
        "The News",
        "The ticker at the bottom carries headlines as events occur. "
        "Headlines shown in gold are clickable, they open the full story as "
        "reported by The Ankh-Morpork Times.\n\n"
        "The Times is not always accurate. It is, however, always read.",
    ),
    (
        "Time",
        "The controls at the bottom right manage the clock. The game starts paused. "
        "Press Play when you are ready. Press Pause when you need to think. "
        "Incidents pause the clock automatically, you are not expected to react "
        "in real time to a collapsing sewer network.\n\n"
        "Speed controls are available for the quieter periods. "
        "There will be quieter periods.",
    ),
    (
        "Finally",
        "Ankh-Morpork has survived floods, fires, dragons, wizards, and at least "
        "one attempted revolution per decade. It will probably survive you.\n\n"
        "Probably.",
    ),
]


class IntroScreen:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self._overlay: ctk.CTkToplevel | None = None
        self.on_begin: Callable[[], None] | None = None

    def show(self) -> None:
        if self._overlay:
            return

        f = fonts()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 660, 640
        px = (sw - w) // 2
        py = (sh - h) // 2

        win = ctk.CTkToplevel(self.root)
        win.title("Briefing")
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", self._begin)
        self._overlay = win

        masthead = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        masthead.pack(fill="x")

        ctk.CTkLabel(
            masthead,
            text="LORD VETINARI'S OPERATIONAL BRIEF",
            font=(f.family, 17, "bold"), text_color=INK,
        ).pack(side="left", padx=24, pady=14)

        ctk.CTkLabel(
            masthead,
            text="CONFIDENTIAL",
            font=f.small_bold, text_color=ACCENT_BROWN,
        ).pack(side="right", padx=24, pady=14)

        ctk.CTkLabel(
            win,
            text="For the attention of the incoming Patrician. Not to be distributed.",
            font=f.small, text_color=INK_MUTED,
        ).pack(anchor="w", padx=24, pady=(10, 4))

        ctk.CTkFrame(win, fg_color=ACCENT_BROWN, height=2).pack(fill="x", padx=24, pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        for title, body in _SECTIONS:
            ctk.CTkLabel(
                scroll, text=title.upper(),
                font=f.small_bold, text_color=ACCENT_BROWN,
            ).pack(anchor="w", padx=24, pady=(16, 4))

            ctk.CTkLabel(
                scroll, text=body,
                font=f.body, text_color=INK,
                wraplength=590, justify="left",
            ).pack(anchor="w", padx=24, pady=(0, 4))

        legend = ctk.CTkFrame(scroll, fg_color=PAPER_DARK, corner_radius=6)
        legend.pack(fill="x", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            legend, text="BUILDING STATUS REFERENCE",
            font=f.small_bold, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=16, pady=(10, 6))

        _legend_row(legend, f, STATUS_GREEN, "Operational: no action required")
        _legend_row(legend, f, STATUS_YELLOW, "Degraded: monitor; may worsen")
        _legend_row(legend, f, STATUS_RED, "Failed: incident in progress")
        _legend_row(legend, f, STATUS_RESPONDING, "Responding: remedy applied, awaiting resolution")

        ctk.CTkFrame(legend, fg_color="transparent", height=8).pack()

        ctk.CTkFrame(scroll, fg_color="transparent", height=12).pack()

        ctk.CTkButton(
            win,
            text="Assume Office",
            command=self._begin,
            width=200, font=(f.family, 14, "bold"),
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=14)

    def _begin(self) -> None:
        if self._overlay:
            self._overlay.grab_release()
            self._overlay.destroy()
            self._overlay = None
        if self.on_begin:
            self.on_begin()


def _legend_row(parent: ctk.CTkFrame, f, colour: str, text: str) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=2)
    ctk.CTkLabel(
        row, text="●", font=f.body_bold, text_color=colour, width=20,
    ).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(
        row, text=text, font=f.small, text_color=INK,
    ).pack(side="left")