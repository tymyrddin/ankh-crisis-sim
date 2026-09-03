from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.gui.info_popups import InfoPopup
from src.gui.theme import (
    ACCENT_BROWN,
    INK,
    INK_MUTED,
    PAPER,
    PAPER_DARK,
    STATUS_YELLOW,
    TRUST_BAD,
    TRUST_GOOD,
    TRUST_WARN,
    fonts,
)
from src.models.city import City


def _bind_click(widget, callback) -> None:
    try:
        widget.configure(cursor="hand2")
    except Exception:
        pass  # not every CTk widget takes a cursor
    widget.bind("<Button-1>", lambda e: callback(), add="+")
    for child in widget.winfo_children():
        _bind_click(child, callback)


# higher is worse
_LOWER_IS_BETTER = {"regulatory_pressure", "crime_level"}

# (green_at, yellow_at, orange_at); lower-is-better metrics compare the other way
_METRIC_THRESHOLDS: dict[str, tuple[float, float, float]] = {
    "public_trust": (60, 40, 20),
    "budget": (3000, 1500, 500),
    "regulatory_pressure": (20, 40, 60),
    "political_stability": (70, 50, 30),
    "legitimacy": (70, 50, 30),
    "public_health": (70, 50, 30),
    "crime_level": (20, 40, 60),
}


def _metric_colour(key: str, value: float) -> str:
    thresholds = _METRIC_THRESHOLDS.get(key)
    if not thresholds:
        return INK
    green_t, yellow_t, orange_t = thresholds
    lower_is_better = key in _LOWER_IS_BETTER
    if not lower_is_better:
        if value >= green_t:
            return TRUST_GOOD
        if value >= yellow_t:
            return STATUS_YELLOW
        if value >= orange_t:
            return TRUST_WARN
        return TRUST_BAD
    else:
        if value <= green_t:
            return TRUST_GOOD
        if value <= yellow_t:
            return STATUS_YELLOW
        if value <= orange_t:
            return TRUST_WARN
        return TRUST_BAD


def _trend_arrow(trend: float, lower_is_better: bool) -> tuple[str, str]:
    improving = trend > 0.05 if not lower_is_better else trend < -0.05
    declining = trend < -0.05 if not lower_is_better else trend > 0.05
    if improving:
        return "↑", TRUST_GOOD
    if declining:
        return "↓", TRUST_BAD
    return "–", INK_MUTED


def _status_colour(pct: float, invert: bool = False) -> str:
    good = pct >= 80 if not invert else pct <= 30
    warn = pct >= 50 if not invert else pct <= 60
    if good:
        return TRUST_GOOD
    if warn:
        return TRUST_WARN
    return TRUST_BAD


class Dashboard:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._trend_labels: dict[str, ctk.CTkLabel] = {}
        self._district_rows: dict[str, dict[str, ctk.CTkLabel]] = {}
        self._metric_rows: dict[str, ctk.CTkFrame] = {}
        self._status_rows: dict[str, ctk.CTkFrame] = {}
        self._district_row_frames: dict[str, ctk.CTkFrame] = {}
        self.on_settings_click: Callable[[], None] | None = None
        f = fonts()

        title_row = ctk.CTkFrame(parent, fg_color="transparent")
        title_row.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            title_row, text="ANKH-MORPORK",
            font=f.title, text_color=INK,
        ).pack(side="left", padx=(0, 0), expand=True)

        ctk.CTkButton(
            title_row, text="⚙",
            command=self._settings_clicked,
            width=32, height=32,
            font=(f.family, 16),
            fg_color="transparent",
            hover_color=PAPER_DARK,
            text_color=INK_MUTED,
            border_width=0,
        ).pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            parent, text="Lord Vetinari's Dilemma",
            font=f.subtitle, text_color=INK_MUTED,
        ).pack(pady=(0, 15))

        ctk.CTkLabel(
            parent, text="CITY METRICS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(5, 2))

        self._metrics_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._metrics_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            parent, text="CITY STATUS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        self._status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._status_frame.pack(fill="x", padx=10, pady=(0, 5))

        self._infra_label: ctk.CTkLabel | None = None
        self._incidents_label: ctk.CTkLabel | None = None
        self._watch_label: ctk.CTkLabel | None = None

        ctk.CTkLabel(
            parent, text="DISTRICTS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=15, pady=(8, 2))

        self._districts_frame = ctk.CTkScrollableFrame(
            parent, fg_color=PAPER, label_text="",
        )
        self._districts_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def build_metrics(self, city: City) -> None:
        f = fonts()
        metrics = [
            ("Public Trust", "public_trust", city.public_trust),
            ("Budget", "budget", city.budget),
            ("Reg. Pressure", "regulatory_pressure", city.regulatory_pressure),
            ("Pol. Stability", "political_stability", city.political_stability),
            ("Legitimacy", "legitimacy", city.legitimacy),
            ("Public Health", "public_health", city.public_health),
            ("Crime Level", "crime_level", city.crime_level),
        ]

        for label, key, metric in metrics:
            row = ctk.CTkFrame(self._metrics_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            self._metric_rows[key] = row

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
                text_color=_metric_colour(key, metric.value),
                width=110, anchor="e",
            )
            value_label.pack(side="right", padx=4, pady=3)
            self._metric_labels[key] = value_label

    def build_status(self, city: City) -> None:
        f = fonts()

        def _status_row(key: str, label: str, value_text: str, colour: str) -> ctk.CTkLabel:
            row = ctk.CTkFrame(self._status_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            self._status_rows[key] = row
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
            "infrastructure", "Infrastructure",
            f"{infra_pct:.0f}%",
            _status_colour(infra_pct),
        )

        incident_count = len(city.visible_events)
        self._incidents_label = _status_row(
            "incidents", "Active Incidents",
            str(incident_count),
            TRUST_BAD if incident_count > 3 else (TRUST_WARN if incident_count > 0 else TRUST_GOOD),
        )

        watch_pct = city.watch_coverage_pct
        self._watch_label = _status_row(
            "watch_coverage", "Watch Coverage",
            f"{watch_pct:.0f}%",
            _status_colour(watch_pct),
        )

    def build_districts(self, city: City) -> None:
        f = fonts()
        for district in city.districts.values():
            if not district.is_residential:
                continue
            row = ctk.CTkFrame(self._districts_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            self._district_row_frames[district.id] = row

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

    def _settings_clicked(self) -> None:
        if self.on_settings_click:
            self.on_settings_click()

    def attach_popup(self, popup: InfoPopup, city: City) -> None:
        for key, frame in self._metric_rows.items():
            _bind_click(frame, lambda k=key: popup.show_metric(city, k))
        for key, frame in self._status_rows.items():
            _bind_click(frame, lambda k=key: popup.show_status(city, k))
        for district_id, frame in self._district_row_frames.items():
            _bind_click(frame, lambda d=district_id: popup.show_district(city, d))

    def update(self, city: City) -> None:
        metrics_map = {
            "public_trust": city.public_trust,
            "budget": city.budget,
            "regulatory_pressure": city.regulatory_pressure,
            "political_stability": city.political_stability,
            "legitimacy": city.legitimacy,
            "public_health": city.public_health,
            "crime_level": city.crime_level,
        }

        for key, metric in metrics_map.items():
            lbl = self._metric_labels.get(key)
            if lbl:
                lbl.configure(
                    text=self._fmt(key, metric.value),
                    text_color=_metric_colour(key, metric.value),
                )

            tlbl = self._trend_labels.get(key)
            if tlbl:
                arrow, colour = _trend_arrow(
                    metric.recent_trend,
                    lower_is_better=(key in _LOWER_IS_BETTER),
                )
                tlbl.configure(text=arrow, text_color=colour)

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
