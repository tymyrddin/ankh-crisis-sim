"""Dashboard panel — global metrics, district summary, and active events."""

from __future__ import annotations

import customtkinter as ctk

from src.models.city import City


METRIC_COLOURS = {
    "public_trust": "#4CAF50",
    "budget": "#2196F3",
    "regulatory_pressure": "#FF9800",
    "political_stability": "#9C27B0",
    "legitimacy": "#E91E63",
}


class Dashboard:
    """Right-side panel showing metrics and district status."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._district_frames: dict[str, ctk.CTkFrame] = {}

        # Title
        ctk.CTkLabel(
            parent, text="ANKH-MORPORK",
            font=("Arial", 22, "bold"),
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            parent, text="Lord Vetinari's Dilemma",
            font=("Arial", 12), text_color="gray",
        ).pack(pady=(0, 15))

        # Global metrics section
        metrics_header = ctk.CTkLabel(parent, text="CITY METRICS", font=("Arial", 14, "bold"))
        metrics_header.pack(anchor="w", padx=15, pady=(5, 2))

        self._metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._metrics_frame.pack(fill="x", padx=10, pady=5)

        # District section
        districts_header = ctk.CTkLabel(parent, text="DISTRICTS", font=("Arial", 14, "bold"))
        districts_header.pack(anchor="w", padx=15, pady=(10, 2))

        self._districts_frame = ctk.CTkScrollableFrame(parent, height=200)
        self._districts_frame.pack(fill="x", padx=10, pady=5)

        # Events section
        events_header = ctk.CTkLabel(parent, text="ACTIVE EVENTS", font=("Arial", 14, "bold"))
        events_header.pack(anchor="w", padx=15, pady=(10, 2))

        self._events_frame = ctk.CTkScrollableFrame(parent, height=150)
        self._events_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def build_metrics(self, city: City) -> None:
        """Create metric display rows."""
        metrics = [
            ("Public Trust", "public_trust", city.public_trust),
            ("Budget", "budget", city.budget),
            ("Regulatory Pressure", "regulatory_pressure", city.regulatory_pressure),
            ("Political Stability", "political_stability", city.political_stability),
            ("Legitimacy", "legitimacy", city.legitimacy),
        ]

        for label, key, metric in metrics:
            row = ctk.CTkFrame(self._metrics_frame)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=label, font=("Arial", 12)).pack(side="left", padx=8, pady=4)

            fmt = f"{metric.value:.0f}" if key != "budget" else f"{metric.value:,.0f} AM$"
            colour = METRIC_COLOURS.get(key, "#FFFFFF")
            value_label = ctk.CTkLabel(
                row, text=fmt,
                font=("Arial", 12, "bold"),
                text_color=colour,
            )
            value_label.pack(side="right", padx=8, pady=4)
            self._metric_labels[key] = value_label

    def build_districts(self, city: City) -> None:
        """Create district summary rows."""
        for district in city.districts.values():
            if not district.is_residential:
                continue
            row = ctk.CTkFrame(self._districts_frame)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=district.name,
                font=("Arial", 11),
            ).pack(side="left", padx=8, pady=3)

            trust_colour = "#4CAF50" if district.local_trust.value > 50 else (
                "#FF9800" if district.local_trust.value > 25 else "#ff3333"
            )
            trust_label = ctk.CTkLabel(
                row,
                text=f"Trust: {district.local_trust.value:.0f}",
                font=("Arial", 10),
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

        for event in city.visible_events:
            row = ctk.CTkFrame(self._events_frame)
            row.pack(fill="x", pady=2)

            phase_icon = {
                "detected": "!",
                "responding": "~",
            }.get(event.phase.value, "?")

            ctk.CTkLabel(
                row,
                text=f"[{phase_icon}] {event.headline or event.name}",
                font=("Arial", 10),
                wraplength=250,
            ).pack(side="left", padx=5, pady=3)