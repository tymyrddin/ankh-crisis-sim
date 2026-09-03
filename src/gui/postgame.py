from __future__ import annotations

import customtkinter as ctk

from src.config.loader import GameConfig
from src.engine.end_check import EndResult
from src.gui.theme import (
    ACCENT_BROWN,
    INK,
    PAPER,
    PAPER_DARK,
    TRUST_BAD,
    TRUST_GOOD,
    TRUST_WARN,
    fonts,
)
from src.models.city import City


class PostgameScreen:
    def __init__(self, root: ctk.CTk, cfg: GameConfig):
        self.root = root
        self.cfg = cfg
        self._overlay: ctk.CTkToplevel | None = None

    def show(self, city: City, end_result: EndResult) -> None:
        if self._overlay:
            return

        f = fonts()
        self._overlay = ctk.CTkToplevel(self.root)
        self._overlay.title("Game Over")
        self._overlay.geometry("700x640")
        self._overlay.attributes("-topmost", True)
        self._overlay.grab_set()
        self._overlay.configure(fg_color=PAPER)

        ctk.CTkLabel(
            self._overlay,
            text=end_result.label,
            font=(f.family, 28, "bold"), text_color=INK,
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            self._overlay,
            text=end_result.narrative,
            font=f.body, text_color=INK,
            wraplength=600,
        ).pack(padx=30, pady=10)

        body = ctk.CTkScrollableFrame(self._overlay, fg_color=PAPER, label_text="")
        body.pack(fill="both", expand=True, padx=0, pady=0)

        metrics_frame = ctk.CTkFrame(body, fg_color=PAPER_DARK)
        metrics_frame.pack(padx=30, pady=15, fill="x")

        ctk.CTkLabel(
            metrics_frame, text="Final State",
            font=f.heading, text_color=ACCENT_BROWN,
        ).pack(pady=5)

        metrics = [
            ("Public Trust", f"{city.public_trust.value:.0f}"),
            ("Budget", f"{city.budget.value:,.0f} AM$"),
            ("Regulatory Pressure", f"{city.regulatory_pressure.value:.0f}"),
            ("Political Stability", f"{city.political_stability.value:.0f}"),
            ("Legitimacy", f"{city.legitimacy.value:.0f}"),
        ]

        for label, value in metrics:
            row = ctk.CTkFrame(metrics_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=label, font=f.body, text_color=INK).pack(side="left")
            ctk.CTkLabel(row, text=value, font=f.body_bold, text_color=INK).pack(side="right")

        if self.cfg.postgame.get("show_inequality_record", True):
            row = ctk.CTkFrame(metrics_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text="Social inequality", font=f.body, text_color=INK).pack(side="left")
            ctk.CTkLabel(
                row, text=f"{city.stressors.get('social_inequality', 0.0):.0%}",
                font=f.body_bold, text_color=INK,
            ).pack(side="right")

        if self.cfg.postgame.get("show_district_outcomes", True):
            district_frame = ctk.CTkFrame(body, fg_color="transparent")
            district_frame.pack(padx=30, pady=10, fill="x")

            ctk.CTkLabel(
                district_frame, text="Who paid the price?",
                font=f.heading, text_color=ACCENT_BROWN,
            ).pack(pady=5)

            for district in city.districts.values():
                if not district.is_residential:
                    continue
                trust = district.local_trust.value
                colour = TRUST_GOOD if trust > 50 else (TRUST_WARN if trust > 25 else TRUST_BAD)
                row = ctk.CTkFrame(district_frame, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=1)
                ctk.CTkLabel(row, text=district.name, font=f.small, text_color=INK).pack(side="left")
                ctk.CTkLabel(
                    row, text=f"Trust: {trust:.0f}",
                    font=f.small_bold, text_color=colour,
                ).pack(side="right")

        questions = self.cfg.postgame.get("reflection_questions", [])
        if questions:
            ctk.CTkLabel(
                body, text="Before you close this",
                font=f.heading, text_color=ACCENT_BROWN,
            ).pack(pady=(6, 2))
            for question in questions:
                ctk.CTkLabel(
                    body, text=question, font=f.small, text_color=INK,
                    wraplength=600, justify="left",
                ).pack(anchor="w", padx=40, pady=1)

        ctk.CTkButton(
            self._overlay, text="Reflect and Close",
            command=self._close, width=200,
            font=f.body_bold, fg_color=ACCENT_BROWN,
            hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=20)

    def _close(self) -> None:
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
