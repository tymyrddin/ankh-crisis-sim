"""Post-game reflection screen — shown when the game ends."""

from __future__ import annotations

import customtkinter as ctk

from src.engine.end_check import EndResult
from src.models.city import City


class PostgameScreen:
    """Overlay shown when an end condition triggers."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._overlay: ctk.CTkToplevel | None = None

    def show(self, city: City, end_result: EndResult) -> None:
        if self._overlay:
            return

        self._overlay = ctk.CTkToplevel(self.root)
        self._overlay.title("Game Over")
        self._overlay.geometry("700x500")
        self._overlay.attributes("-topmost", True)
        self._overlay.grab_set()

        # Header
        ctk.CTkLabel(
            self._overlay,
            text=end_result.label,
            font=("Arial", 28, "bold"),
        ).pack(pady=(30, 10))

        # Narrative
        ctk.CTkLabel(
            self._overlay,
            text=end_result.narrative,
            font=("Arial", 14),
            wraplength=600,
        ).pack(padx=30, pady=10)

        # Final metrics
        metrics_frame = ctk.CTkFrame(self._overlay)
        metrics_frame.pack(padx=30, pady=15, fill="x")

        ctk.CTkLabel(metrics_frame, text="Final State", font=("Arial", 16, "bold")).pack(pady=5)

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
            ctk.CTkLabel(row, text=label, font=("Arial", 12)).pack(side="left")
            ctk.CTkLabel(row, text=value, font=("Arial", 12, "bold")).pack(side="right")

        # District outcomes
        district_frame = ctk.CTkScrollableFrame(self._overlay, height=120)
        district_frame.pack(padx=30, pady=10, fill="x")

        ctk.CTkLabel(district_frame, text="Who paid the price?", font=("Arial", 14, "bold")).pack(pady=5)

        for district in city.districts.values():
            if not district.is_residential:
                continue
            trust = district.local_trust.value
            colour = "#4CAF50" if trust > 50 else ("#FF9800" if trust > 25 else "#ff3333")
            row = ctk.CTkFrame(district_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(row, text=district.name, font=("Arial", 11)).pack(side="left")
            ctk.CTkLabel(
                row, text=f"Trust: {trust:.0f}",
                font=("Arial", 11, "bold"), text_color=colour,
            ).pack(side="right")

        # Close button
        ctk.CTkButton(
            self._overlay, text="Reflect and Close",
            command=self._close,
            width=200,
        ).pack(pady=20)

    def _close(self) -> None:
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None