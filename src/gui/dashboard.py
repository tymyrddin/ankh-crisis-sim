"""Dashboard panel — global metrics, city status, district summary, and active events."""

from __future__ import annotations

import customtkinter as ctk

from src.gui.theme import (
    INK, INK_MUTED, METRIC_COLOURS, PAPER, PAPER_DARK,
    TRUST_BAD, TRUST_GOOD, TRUST_WARN, ACCENT_BROWN, fonts,
)
from src.models.city import City


# Metrics where a higher value is worse (trend arrows and colours invert)
_LOWER_IS_BETTER = {"regulatory_pressure", "crime_level"}


def _trend_arrow(trend: float, lower_is_better: bool) -> tuple[str, str]:
    """Return (arrow_character, colour) for a metric trend."""
    improving = trend > 0.05 if not lower_is_better else trend < -0.05
    declining = trend < -0.05 if not lower_is_better else trend > 0.05
    if improving:
        return "↑", TRUST_GOOD
    if declining:
        return "↓", TRUST_BAD
    return "–", INK_MUTED


def _status_colour(pct: float, invert: bool = False) -> str:
    """Green/amber/red based on percentage, optionally inverted (higher = worse)."""
    good = pct >= 80 if not invert else pct <= 30
    warn = pct >= 50 if not invert else pct <= 60
    if good:
        return TRUST_GOOD
    if warn:
        return TRUST_WARN
    return TRUST_BAD


class Dashboard:
    """Right-side panel showing metrics and district status."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._trend_labels: dict[str, ctk.CTkLabel] = {}
        self._district_rows: dict[str, dict[str, ctk.CTkLabel]] = {}
        self._event_widgets: dict[str, tuple[ctk.CTkFrame, str]] = {}
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

        # --- City Metrics ---
        ctk.CTkLabel(
            parent, text="CITY METRICS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(5, 2))

        self._metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._metrics_frame.pack(fill="x", padx=10, pady=5)

        # --- City Status ---
        ctk.CTkLabel(
            parent, text="CITY STATUS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        self._status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._status_frame.pack(fill="x", padx=10, pady=(0, 5))

        self._infra_label: ctk.CTkLabel | None = None
        self._incidents_label: ctk.CTkLabel | None = None
        self._watch_label: ctk.CTkLabel | None = None

        # --- Districts ---
        ctk.CTkLabel(
            parent, text="DISTRICTS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        self._districts_frame = ctk.CTkScrollableFrame(
            parent, height=200, fg_color=PAPER, label_text="",
        )
        self._districts_frame.pack(fill="x", padx=10, pady=5)

        # --- Active Events ---
        ctk.CTkLabel(
            parent, text="ACTIVE EVENTS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        self._events_frame = ctk.CTkScrollableFrame(
            parent, height=150, fg_color=PAPER, label_text="",
        )
        self._events_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # ------------------------------------------------------------------
    # Build (called once on game start)
    # ------------------------------------------------------------------

    def build_metrics(self, city: City) -> None:
        """Create metric display rows with trend arrows."""
        f = fonts()
        metrics = [
            ("Public Trust",        "public_trust",        city.public_trust),
            ("Budget",              "budget",               city.budget),
            ("Reg. Pressure",       "regulatory_pressure",  city.regulatory_pressure),
            ("Pol. Stability",      "political_stability",  city.political_stability),
            ("Legitimacy",          "legitimacy",           city.legitimacy),
            ("Public Health",       "public_health",        city.public_health),
            ("Crime Level",         "crime_level",          city.crime_level),
        ]

        for label, key, metric in metrics:
            row = ctk.CTkFrame(self._metrics_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row, text=label, font=f.body, text_color=INK,
            ).pack(side="left", padx=8, pady=3)

            trend_label = ctk.CTkLabel(
                row, text="–", font=f.small, text_color=INK_MUTED,
                width=14, anchor="e",
            )
            trend_label.pack(side="right", padx=(0, 2), pady=3)
            self._trend_labels[key] = trend_label

            fmt = self._fmt(key, metric.value)
            value_label = ctk.CTkLabel(
                row, text=fmt,
                font=f.body_bold,
                text_color=METRIC_COLOURS.get(key, INK),
                width=110, anchor="e",
            )
            value_label.pack(side="right", padx=4, pady=3)
            self._metric_labels[key] = value_label

    def build_status(self, city: City) -> None:
        """Create city status indicator rows."""
        f = fonts()

        def _status_row(label: str, value_text: str, colour: str) -> ctk.CTkLabel:
            row = ctk.CTkFrame(self._status_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=f.small, text_color=INK).pack(
                side="left", padx=8, pady=2,
            )
            lbl = ctk.CTkLabel(
                row, text=value_text, font=f.small_bold,
                text_color=colour, width=70, anchor="e",
            )
            lbl.pack(side="right", padx=8, pady=2)
            return lbl

        infra_pct = city.infrastructure_health_pct
        self._infra_label = _status_row(
            "Infrastructure",
            f"{infra_pct:.0f}%",
            _status_colour(infra_pct),
        )

        incident_count = len(city.visible_events)
        self._incidents_label = _status_row(
            "Active Incidents",
            str(incident_count),
            TRUST_BAD if incident_count > 3 else (TRUST_WARN if incident_count > 0 else TRUST_GOOD),
        )

        watch_pct = city.watch_coverage_pct
        self._watch_label = _status_row(
            "Watch Coverage",
            f"{watch_pct:.0f}%",
            _status_colour(watch_pct),
        )

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

            trust_colour = _trust_colour(district.local_trust.value)
            trust_lbl = ctk.CTkLabel(
                row,
                text=f"Trust: {district.local_trust.value:.0f}",
                font=f.small, text_color=trust_colour,
                width=70, anchor="e",
            )
            trust_lbl.pack(side="right", padx=4, pady=3)

            events_lbl = ctk.CTkLabel(
                row, text="", font=f.small, text_color=TRUST_WARN,
                width=55, anchor="e",
            )
            events_lbl.pack(side="right", padx=2, pady=3)

            self._district_rows[district.id] = {
                "trust": trust_lbl,
                "events": events_lbl,
            }

    # ------------------------------------------------------------------
    # Update (called every tick)
    # ------------------------------------------------------------------

    def update(self, city: City) -> None:
        """Refresh all metric values and trend arrows."""
        metrics_map = {
            "public_trust":        city.public_trust,
            "budget":              city.budget,
            "regulatory_pressure": city.regulatory_pressure,
            "political_stability": city.political_stability,
            "legitimacy":          city.legitimacy,
            "public_health":       city.public_health,
            "crime_level":         city.crime_level,
        }

        for key, metric in metrics_map.items():
            lbl = self._metric_labels.get(key)
            if lbl:
                lbl.configure(text=self._fmt(key, metric.value))

            tlbl = self._trend_labels.get(key)
            if tlbl:
                arrow, colour = _trend_arrow(
                    metric.recent_trend,
                    lower_is_better=(key in _LOWER_IS_BETTER),
                )
                tlbl.configure(text=arrow, text_color=colour)

        # Status indicators
        if self._infra_label:
            pct = city.infrastructure_health_pct
            self._infra_label.configure(
                text=f"{pct:.0f}%", text_color=_status_colour(pct),
            )
        if self._incidents_label:
            n = len(city.visible_events)
            self._incidents_label.configure(
                text=str(n),
                text_color=TRUST_BAD if n > 3 else (TRUST_WARN if n > 0 else TRUST_GOOD),
            )
        if self._watch_label:
            pct = city.watch_coverage_pct
            self._watch_label.configure(
                text=f"{pct:.0f}%", text_color=_status_colour(pct),
            )

        # District rows
        for district in city.districts.values():
            row_labels = self._district_rows.get(district.id)
            if not row_labels:
                continue

            trust = district.local_trust.value
            row_labels["trust"].configure(
                text=f"Trust: {trust:.0f}",
                text_color=_trust_colour(trust),
            )

            failed = district.failed_building_count
            active = district.active_event_count
            if failed > 0:
                row_labels["events"].configure(
                    text=f"{failed} down", text_color=TRUST_BAD,
                )
            elif active > 0:
                row_labels["events"].configure(
                    text=f"{active} event{'s' if active > 1 else ''}",
                    text_color=TRUST_WARN,
                )
            else:
                row_labels["events"].configure(text="")

    def update_events(self, city: City) -> None:
        """Refresh the active events list — only rebuilds when events change."""
        current_ids = set()
        snapshots: dict[str, str] = {}

        for event in city.visible_events:
            phase_icon = {
                "detected": "!",
                "responding": "~",
            }.get(event.phase.value, "?")
            snap = f"[{phase_icon}] {event.headline or event.name}"
            current_ids.add(event.id)
            snapshots[event.id] = snap

        old_ids = set(self._event_widgets.keys())
        changed = current_ids != old_ids or any(
            snapshots.get(eid) != self._event_widgets[eid][1]
            for eid in current_ids & old_ids
        )
        if not changed:
            return

        for widget, _ in self._event_widgets.values():
            widget.destroy()
        self._event_widgets.clear()

        f = fonts()
        for event in city.visible_events:
            row = ctk.CTkFrame(self._events_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=snapshots[event.id],
                font=f.small, text_color=INK,
                wraplength=250,
            ).pack(side="left", padx=5, pady=3)

            self._event_widgets[event.id] = (row, snapshots[event.id])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(key: str, value: float) -> str:
        if key == "budget":
            return f"{value:,.0f} AM$"
        return f"{value:.0f}"


def _trust_colour(value: float) -> str:
    if value > 50:
        return TRUST_GOOD
    if value > 25:
        return TRUST_WARN
    return TRUST_BAD