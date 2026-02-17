"""Dashboard panel — global metrics, district summary, and active events."""

from __future__ import annotations

import customtkinter as ctk

from src.gui.theme import (
    INK, INK_MUTED, METRIC_COLOURS, PAPER, PAPER_DARK,
    TRUST_BAD, TRUST_GOOD, TRUST_WARN, ACCENT_BROWN, fonts,
)
from src.models.city import City


class Dashboard:
    """Right-side panel showing metrics and district status."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._district_frames: dict[str, ctk.CTkFrame] = {}
        f = fonts()

        # Title
        ctk.CTkLabel(
            parent, text="ANKH-MORPORK",
            font=f.title, text_color=INK,
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            parent, text="Lord Vetinari's Dilemma",
            font=f.subtitle, text_color=INK_MUTED,
        ).pack(pady=(0, 15))

        # Global metrics section
        metrics_header = ctk.CTkLabel(
            parent, text="CITY METRICS", font=f.heading, text_color=ACCENT_BROWN,
        )
        metrics_header.pack(anchor="w", padx=15, pady=(5, 2))

        self._metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._metrics_frame.pack(fill="x", padx=10, pady=5)

        # District section
        districts_header = ctk.CTkLabel(
            parent, text="DISTRICTS", font=f.heading, text_color=ACCENT_BROWN,
        )
        districts_header.pack(anchor="w", padx=15, pady=(10, 2))

        self._districts_frame = ctk.CTkScrollableFrame(
            parent, height=200, fg_color=PAPER, label_text="",
        )
        self._districts_frame.pack(fill="x", padx=10, pady=5)

        # Events section
        events_header = ctk.CTkLabel(
            parent, text="ACTIVE EVENTS", font=f.heading, text_color=ACCENT_BROWN,
        )
        events_header.pack(anchor="w", padx=15, pady=(10, 2))

        self._events_frame = ctk.CTkScrollableFrame(
            parent, height=150, fg_color=PAPER, label_text="",
        )
        self._events_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def build_metrics(self, city: City) -> None:
        """Create metric display rows."""
        f = fonts()
        metrics = [
            ("Public Trust", "public_trust", city.public_trust),
            ("Budget", "budget", city.budget),
            ("Regulatory Pressure", "regulatory_pressure", city.regulatory_pressure),
            ("Political Stability", "political_stability", city.political_stability),
            ("Legitimacy", "legitimacy", city.legitimacy),
        ]

        for label, key, metric in metrics:
            row = ctk.CTkFrame(self._metrics_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=label, font=f.body, text_color=INK).pack(side="left", padx=8, pady=4)

            fmt = f"{metric.value:.0f}" if key != "budget" else f"{metric.value:,.0f} AM$"
            colour = METRIC_COLOURS.get(key, INK)
            value_label = ctk.CTkLabel(
                row, text=fmt,
                font=f.body_bold,
                text_color=colour,
            )
            value_label.pack(side="right", padx=8, pady=4)
            self._metric_labels[key] = value_label

    def build_districts(self, city: City) -> None:
        """Create district summary rows."""
        f = fonts()
        for district in city.districts.values():
            if not district.is_residential:
                continue
            row = ctk.CTkFrame(self._districts_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=district.name,
                font=f.small, text_color=INK,
            ).pack(side="left", padx=8, pady=3)

            trust_colour = TRUST_GOOD if district.local_trust.value > 50 else (
                TRUST_WARN if district.local_trust.value > 25 else TRUST_BAD
            )
            trust_label = ctk.CTkLabel(
                row,
                text=f"Trust: {district.local_trust.value:.0f}",
                font=f.small,
                text_color=trust_colour,
            )
            trust_label.pack(side="right", padx=8, pady=3)
            self._district_frames[district.id] = row

    def update(self, city: City) -> None:
        """Refresh all displayed values."""
        metrics_map = {
            "public_trust": city.public_trust,
            "budget": city.budget,
            "regulatory_pressure": city.regulatory_pressure,
            "political_stability": city.political_stability,
            "legitimacy": city.legitimacy,
        }

        for key, metric in metrics_map.items():
            label = self._metric_labels.get(key)
            if label:
                fmt = f"{metric.value:.0f}" if key != "budget" else f"{metric.value:,.0f} AM$"
                label.configure(text=fmt)

    def update_events(self, city: City) -> None:
        """Refresh the active events list."""
        for widget in self._events_frame.winfo_children():
            widget.destroy()

        f = fonts()
        for event in city.visible_events:
            row = ctk.CTkFrame(self._events_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            phase_icon = {
                "detected": "!",
                "responding": "~",
            }.get(event.phase.value, "?")

            ctk.CTkLabel(
                row,
                text=f"[{phase_icon}] {event.headline or event.name}",
                font=f.small, text_color=INK,
                wraplength=250,
            ).pack(side="left", padx=5, pady=3)