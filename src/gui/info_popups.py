"""Info popups: clickable explanations for dashboard metrics, status, and districts."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import customtkinter as ctk

from src.config.loader import GameConfig
from src.gui.theme import (
    ACCENT_BROWN,
    INK,
    INK_MUTED,
    METRIC_COLOURS,
    PAPER,
    PAPER_DARK,
    TRUST_BAD,
    TRUST_GOOD,
    TRUST_WARN,
    fonts,
)
from src.models.city import City
from src.models.district import District

_METRIC_INFO: dict[str, dict] = {
    "public_trust": {
        "title": "Public Trust",
        "description": (
            "The population's pragmatic acceptance that Vetinari's system of organised stability "
            "is preferable to the alternative. This is not affection, it is the cold calculation "
            "of a city that knows what chaos looks like. Trust erodes with every visible, unresolved "
            "failure and recovers when things are seen to work."
        ),
        "drivers": [
            "Each detected incident hits its district's trust at once, then again every day it is left alone",
            "An incident ignored for more than a day becomes a scandal: daily damage scaled by the district's "
            "media attention, by organisational fragmentation, and by accumulated narrative pressure",
            "The city figure is a weighted average of district trust: density and political influence "
            "set the weights, so the Shades count for less than Nap Hill",
            "Below the tax threshold, collection falters and the budget follows trust down",
        ],
        "actions": [
            "Respond. A response in progress stops the daily penalty and the scandal; the completed "
            "structural upgrade pays a delayed trust dividend",
            "Compensation buys a visible boost that fades a month later; the problem stays",
            "A press statement halves scandal damage for 48 hours. Follow it with a real response or "
            "pay for the contradiction",
            "Do nothing, and citizens notice immediately",
        ],
    },

    "budget": {
        "title": "Budget",
        "description": (
            "The city treasury: the only constraint that is not political. Income arrives monthly from "
            "taxes, guild fees, trade tariffs, river duties, clacks licensing and UU's symbolic "
            "contribution. Spending can run into the red down to the credit the guilds tolerate. "
            "Stay below zero for a fortnight and the creditors stop tolerating."
        ),
        "drivers": [],  # filled from config at show time
        "actions": [
            "Borrow. Domestic credit costs regulatory pressure; foreign credit costs stability",
            "Keep public trust above the tax threshold: the most sustainable budget fix",
            "Keep transport, food supply and clacks towers standing: tariffs, river duties and "
            "licensing fees scale with what still works",
            "Choose the cheaper pathway where the threatmodel allows it, and accept the recurrence",
        ],
    },

    "regulatory_pressure": {
        "title": "Regulatory Pressure",
        "description": (
            "The combined force of guilds, nobility, press and concerned factions demanding that "
            "something be done. At low levels it is background noise every Patrician learns to ignore. "
            "It does not end the game on its own; it colours every story the Times prints."
        ),
        "drivers": [
            "Every visible incident adds a point a day; one with a response under way adds a fifth of that",
            "A full week with nothing visible releases two points",
            "An inquiry lifts pressure by the amount set in its remedy entry, at the price of stability",
            "A loan from the Royal Bank is noticed by the guilds",
        ],
        "actions": [
            "Respond to what is visible; responding incidents weigh five times less than ignored ones",
            "Launch an inquiry where the domain allows it: pressure falls, stability dips, "
            "and the scapegoat may fight back",
            "Earn quiet weeks; the city has a short memory",
            "Borrow from Überwald rather than the Royal Bank if pressure, not stability, is the constraint",
        ],
    },

    "political_stability": {
        "title": "Political Stability",
        "description": (
            "The absence of a credible alternative to the current arrangement. Vetinari's genius "
            "is not popularity, it is making instability unthinkable. Below five, the Assassins' Guild "
            "accepts a contract."
        ),
        "drivers": [
            "Public trust below 25 costs two points a day",
            "An incident-free week restores one point",
            "A completed structural upgrade returns a slice of its trust reward as stability",
            "Inquiries are divisive and cost three; an Überwald loan costs eight",
        ],
        "actions": [
            "Keep trust off the floor: the trust collapse penalty is the fastest route down",
            "Complete structural upgrades; the stability gain lands the day the work finishes",
            "Weigh the inquiry: it buys regulatory relief with stability",
            "Borrow domestically when stability is the scarcer resource",
        ],
    },

    "legitimacy": {
        "title": "Legitimacy",
        "description": (
            "The moral and historical right to rule, distinct from trust, which is pragmatic, "
            "and stability, which is situational. Legitimacy moves slowly and mostly downwards. "
            "Below ten, the districts declare the Patrician illegitimate and the Watch cannot hold the city."
        ),
        "drivers": [
            "Half a point returns each month that stability stays above fifty",
            "Some failures cost legitimacy outright, and nothing in the treasury buys it back",
        ],
        "actions": [
            "Keep stability above fifty for months at a stretch; that is the only source of recovery",
            "Treat public-service failures with care: those are the incidents that reach legitimacy",
            "Do not violate the charter. The city has forgotten many things. Not that.",
        ],
    },

    "public_health": {
        "title": "Public Health",
        "description": (
            "A leading indicator: the first signal that water contamination, food shortage or "
            "healthcare failure is compounding into something harder to fix. "
            "The poor districts feel it first; by the time Nap Hill notices, it is already serious."
        ),
        "drivers": [
            "Water, food and healthcare incidents carry health impacts, some immediate and some "
            "arriving days later",
            "Just-in-time logistics shortens the grace period before the second blow lands",
            "Health is lost to incidents and regained only by their absence",
        ],
        "actions": [
            "Prioritise water sources, food supply and healthcare buildings when several incidents compete",
            "Respond before the second blow is due; a resolved failure never delivers it",
            "Structural upgrades ease the just-in-time pressure that shortens the grace period",
        ],
    },

    "crime_level": {
        "title": "Crime Level",
        "description": (
            "Unlicensed criminal activity: crime that the Thieves' Guild has not sanctioned "
            "and cannot control. The Guild's quota system normally keeps crime at a manageable, "
            "taxable level that everyone pretends not to notice."
        ),
        "drivers": [
            "Watch coverage below half raises crime a little every day, more the lower it falls",
            "Watch coverage at or above eighty percent lowers it slowly",
            "Incidents with a crime impact, guild extortion above all, add to it directly",
        ],
        "actions": [
            "Keep Watch posts standing; coverage is the lever that moves this every day",
            "Respond to security incidents first when coverage is slipping",
            "Accept that the Guild's own quota is not something the Patrician's office adjusts",
        ],
    },
}

_STATUS_INFO: dict[str, dict] = {
    "infrastructure": {
        "title": "Infrastructure Health",
        "description": (
            "The percentage of city buildings currently operational across all districts. "
            "This is the strategic picture: not which districts are angry, but what capacity "
            "the city actually has."
        ),
        "drivers": [
            "Every unresolved building failure reduces this percentage",
            "Remedy completion restores buildings; the emergency patch is fastest",
            "An ignored failure rolls for cascades once a day and can take its dependants with it",
            "The Shades, Cockbill Street and the river fail more often; Nap Hill and the University hardly ever",
        ],
        "actions": [
            "Prioritise water sources, power and healthcare: everything else depends on these",
            "Structural upgrades cut a district's failure multiplier toward baseline, permanently",
            "Triage by dependency: the building everything else relies on comes first",
            "A response in progress shields dependents from cascading",
        ],
    },

    "incidents": {
        "title": "Active Incidents",
        "description": (
            "The number of detected failures currently awaiting a response. Hidden failures "
            "are not counted here, this is what has surfaced. Each unaddressed incident decays "
            "trust and may cascade. The dashboard turns red above three."
        ),
        "drivers": [
            "Failures roll every hour in every district; the city's stressors load the dice",
            "Remedy completion resolves events and removes them from this count",
            "How fast a failure surfaces depends on the district, the building, and how hard anyone is looking",
            "Cascades appear here immediately; they are never hidden",
        ],
        "actions": [
            "Apply remedies through the building on the map: the primary response mechanism",
            "Prioritise by dependency chain: one upstream fix prevents several downstream cascades",
            "Issue a press statement to halve scandal damage while the actual work is chosen",
            "Accept some incidents as tolerable losses; do nothing costs trust and invites cascades, "
            "but saves the budget",
        ],
    },

    "watch_coverage": {
        "title": "Watch Coverage",
        "description": (
            "The percentage of Watch posts currently staffed and operational. When coverage falls "
            "below half, crime rises a little every day; at eighty percent and above it falls. "
            "The Thieves' Guild watches these numbers closely."
        ),
        "drivers": [
            "Watch understaffing events take posts out of service",
            "Restoring a post restores its share of coverage",
            "Coverage feeds the crime level every day",
        ],
        "actions": [
            "Respond to Watch post incidents before crime compounds",
            "Structural upgrades on Watch posts make the next outage less likely",
            "Accept a short lapse if the budget demands it; the crime effect is gradual",
        ],
    },
}


class InfoPopup:
    """One window, torn down and rebuilt on every show."""

    def __init__(self, root: ctk.CTk, cfg: GameConfig):
        self.root = root
        self.cfg = cfg
        self._window: ctk.CTkToplevel | None = None
        self.on_emergency_borrow: Callable[[str], None] | None = None

    def show_metric(self, city: City, key: str) -> None:
        info = _METRIC_INFO.get(key)
        if not info:
            return
        metric = city.get_metric(key)
        if metric is None:
            return
        value_str = f"{metric.value:,.0f} AM$" if key == "budget" else f"{metric.value:.0f} / 100"
        colour = METRIC_COLOURS.get(key, INK)

        drivers = info["drivers"]
        action_buttons = None
        if key == "budget":
            drivers = self._budget_drivers(city)
            if self.on_emergency_borrow:
                action_buttons = self._borrow_buttons()

        self._show(info["title"], value_str, colour, info["description"],
                   drivers, info["actions"], action_buttons=action_buttons)

    def _budget_drivers(self, city: City) -> list[str]:
        income = sum(float(v) for v in self.cfg.budget_income.values())
        taxes = self.cfg.metrics_global_raw.get("budget", {}).get("income_sources", {}).get("taxes", {})
        threshold = taxes.get("trust_threshold", 30)
        penalty = 1.0 - float(taxes.get("penalty_multiplier", 0.6))
        costs = ", ".join(
            f"{r.label} {r.base_cost}" for r in self.cfg.remedies.values() if r.base_cost
        )
        return [
            f"Monthly income at full capacity: {income:,.0f} AM$; "
            "fees, tariffs and duties fall with each failed building",
            f"Public trust below {threshold} cuts tax income by {penalty:.0%}",
            f"Base remedy costs: {costs}. Repairs cost more in fragile districts, upgrades more in rich ones",
            f"Credit runs to {abs(city.budget.min_value):,.0f} AM$ below zero; a fortnight in the red is bankruptcy",
        ]

    def _borrow_buttons(self) -> list[tuple[str, str, Callable[[], None]]]:
        buttons: list[tuple[str, str, Callable[[], None]]] = []
        for lender_id, lender in self.cfg.budget_raw.get("emergency_borrowing", {}).items():
            if not lender.get("available", False):
                continue
            costs = []
            if lender.get("regulatory_pressure_cost"):
                costs.append(f"regulatory pressure +{lender['regulatory_pressure_cost']}")
            if lender.get("stability_cost"):
                costs.append(f"political stability −{lender['stability_cost']}")
            buttons.append((
                f"{lender.get('label', lender_id)}  +{float(lender.get('max_amount', 0)):,.0f} AM$",
                "; ".join(costs).capitalize() + "." if costs else "No immediate political cost.",
                partial(self._do_borrow, lender_id),
            ))
        return buttons

    def _do_borrow(self, lender_id: str) -> None:
        if self.on_emergency_borrow:
            self.on_emergency_borrow(lender_id)
        self._close()

    def show_status(self, city: City, key: str) -> None:
        info = _STATUS_INFO.get(key)
        if not info:
            return
        if key == "infrastructure":
            value_str = f"{city.infrastructure_health_pct:.0f}% operational"
            colour = _pct_colour(city.infrastructure_health_pct)
        elif key == "incidents":
            n = len(city.visible_events)
            value_str = f"{n} active"
            colour = TRUST_BAD if n > 3 else (TRUST_WARN if n > 0 else TRUST_GOOD)
        else:  # watch_coverage
            value_str = f"{city.watch_coverage_pct:.0f}% staffed"
            colour = _pct_colour(city.watch_coverage_pct)
        self._show(info["title"], value_str, colour, info["description"],
                   info["drivers"], info["actions"])

    def show_district(self, city: City, district_id: str) -> None:
        district = city.districts.get(district_id)
        if not district:
            return
        trust = district.local_trust.value
        colour = TRUST_GOOD if trust > 50 else (TRUST_WARN if trust > 25 else TRUST_BAD)

        failed = district.failed_buildings
        active = district.active_event_count

        description = _district_description(district)
        drivers = _district_drivers(district)
        actions = _district_actions(district)

        status_parts = [f"Trust {trust:.0f}"]
        if failed:
            status_parts.append(f"{len(failed)} building{'s' if len(failed) > 1 else ''} down")
        if active:
            status_parts.append(f"{active} active event{'s' if active > 1 else ''}")
        value_str = " · ".join(status_parts)

        self._show(district.name, value_str, colour, description, drivers, actions,
                   extra_rows=_district_extra(district, failed))

    def _show(
        self,
        title: str,
        value_str: str,
        value_colour: str,
        description: str,
        drivers: list[str],
        actions: list[str],
        extra_rows: list[tuple[str, str]] | None = None,
        action_buttons: list[tuple[str, str, Callable[[], None]]] | None = None,
    ) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

        f = fonts()
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        win.geometry("600x520")
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        self._window = win
        win.protocol("WM_DELETE_WINDOW", self._close)

        header = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header, text=title,
            font=(f.family, 20, "bold"), text_color=INK,
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            header, text=value_str,
            font=f.body_bold, text_color=value_colour,
        ).pack(side="right", padx=20, pady=12)

        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(
            scroll, text=description,
            font=f.body, text_color=INK,
            wraplength=540, justify="left",
        ).pack(anchor="w", padx=20, pady=(16, 8))

        if extra_rows:
            extra_frame = ctk.CTkFrame(scroll, fg_color=PAPER_DARK, corner_radius=6)
            extra_frame.pack(fill="x", padx=20, pady=(0, 8))
            for label, val in extra_rows:
                row = ctk.CTkFrame(extra_frame, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=2)
                ctk.CTkLabel(row, text=label, font=f.small, text_color=INK_MUTED).pack(side="left")
                ctk.CTkLabel(row, text=val, font=f.small_bold, text_color=INK).pack(side="right")

        _section(scroll, f, "What drives this", drivers, bullet="◆")
        _section(scroll, f, "Possible actions", actions, bullet="→")

        if action_buttons:
            ctk.CTkLabel(
                scroll, text="SUGGESTED ACTIONS",
                font=f.small_bold, text_color=ACCENT_BROWN,
            ).pack(anchor="w", padx=20, pady=(12, 4))
            for btn_label, btn_desc, btn_cmd in action_buttons:
                btn_frame = ctk.CTkFrame(scroll, fg_color=PAPER_DARK, corner_radius=6)
                btn_frame.pack(fill="x", padx=20, pady=4)
                ctk.CTkLabel(
                    btn_frame, text=btn_desc,
                    font=f.small, text_color=INK_MUTED,
                    wraplength=460, justify="left",
                ).pack(anchor="w", padx=12, pady=(8, 4))
                ctk.CTkButton(
                    btn_frame, text=btn_label,
                    command=btn_cmd,
                    font=f.small_bold,
                    height=30,
                    fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
                ).pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            win, text="Close",
            command=self._close,
            width=140, font=f.body_bold,
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=12)

    def _close(self) -> None:
        if self._window:
            self._window.destroy()
            self._window = None


_DISTRICT_DESCRIPTIONS: dict[str, str] = {
    "nap_hill": (
        "The wealthiest residential district. Residents expect service and complain immediately "
        "when they do not receive it. Failures here generate disproportionate regulatory pressure "
        "due to noble proximity to the Patrician's Palace. Discovery is fast; patience is short."
    ),
    "the_shades": (
        "The poorest district. Residents have no margin for error and every expectation of neglect. "
        "Trust here starts low and decays slowly, not because failures hurt less, but because "
        "expectations are already at the floor. The Vimes effect is strongest here: his presence "
        "collapses discovery time and restores faith that no bureaucratic action can replicate."
    ),
    "cockbill_street": (
        "Poorer than the Shades in resources, richer in pride. Cockbill Street residents will "
        "not report failures. They would rather suffer silently than admit need. Active concealment "
        "means discovery times are the longest in the city. Vimes is the only authority figure who "
        "is not perceived as a threat."
    ),
    "isle_of_gods": (
        "A medium-wealth district defined by geographic isolation. The single bridge is its "
        "critical dependency, close it and residents are stranded. Temple networks provide "
        "some informal reporting. The temples have long memories and considerable patience."
    ),
    "university_precinct": (
        "High wealth, high self-sufficiency, paradoxical trust. The city does not trust UU, "
        "it tolerates it. UU largely tolerates the city in return. Failures here are as likely "
        "to be self-caused as externally imposed. The Archchancellor responds to firm, polite "
        "requests. Wizards generally respond to nothing at all."
    ),
    "merchant_quarter": (
        "The commercial heart of the city. Very high political influence. The Guild of Merchants "
        "has direct access to the Patrician's ear. Business hours matter; night failures are slower "
        "to discover. Discovery is fast when revenue is affected. Almost everything is about revenue."
    ),
    "small_gods": (
        "The forgotten middle: mixed-use, chronic underinvestment, low political influence. "
        "Residents grumble but assume no one cares. They are largely correct. Resilience investment "
        "here is transformative because the baseline is so low. Community reporting incentives "
        "have more impact here than anywhere else."
    ),
    "river_ankh": (
        "Symbolic and industrial: the river district affects all others through its supply chains "
        "and transport links. Failures here are visible if they involve fire or flood; "
        "gradual contamination goes undetected until it is far too late."
    ),
}

_DISTRICT_ACTIONS: dict[str, list[str]] = {
    "nap_hill": [
        "Rapid technical restoration is mandatory: delay here generates noble letters "
        "within hours and regulatory pressure spikes",
        "Accountability actions land well with this audience: they want someone named",
        "Direct engagement with Lord Rust and peers prevents formal complaints from escalating",
        "Avoid public compensation: it is seen as an insult to their intelligence",
    ],
    "the_shades": [
        "Deploy Vimes personally: his presence here has the largest trust impact in the game; "
        "no bureaucratic action matches it",
        "Water carts and food drops as compensation buy hours of goodwill, not days",
        "Community outreach through Shades elder networks: the city's official channels "
        "are not trusted; local voices carry weight",
        "Do not send officials who are visibly afraid of the district: they will notice",
    ],
    "cockbill_street": [
        "Vimes visit is essential: he is the only official who is not perceived as a threat; "
        "recovery without him is measured in weeks",
        "Do not send bureaucrats: the community's response to paperwork is not cooperative",
        "Quiet investment in water and food infrastructure has transformative effect "
        "when Cockbill Street finally accepts it",
        "Pride prevents reporting; solve the problem before they admit it exists",
    ],
    "isle_of_gods": [
        "Bridge priority repair: the single transport link makes this the critical dependency; "
        "boat service as a workaround buys days, not weeks",
        "Temple liaison: the temples can mobilise mutual support networks faster than the Watch",
        "Residents are vocal but patient; a clear timeline reduces regulatory pressure significantly",
        "Geographical isolation means cascades stay contained, and also that help arrives slowly",
    ],
    "university_precinct": [
        "Negotiate with the Archchancellor directly, the Bursar signs nothing without his approval, "
        "and he approves little without being asked firmly",
        "UU can and occasionally does fix its own problems; the challenge is knowing when to wait",
        "Avoid confrontation, UU's legal position is ancient and extremely well-documented",
        "Magical incidents require specialist response; the Guild of Engineers declines to attend",
    ],
    "merchant_quarter": [
        "Rapid remedy application is essential: lost revenue focuses attention immediately; "
        "every hour of outage becomes a guild complaint",
        "Guild liaison officers reduce the formal complaint volume significantly",
        "Trade tariff pressure is real here: transport and clacks failures directly affect income",
        "The Guild of Merchants is a strong ally if it feels consulted; a difficult opponent otherwise",
    ],
    "small_gods": [
        "Resilience investment is disproportionately effective here: the baseline is low enough "
        "that genuine improvement produces visible gratitude",
        "Community reporting incentives have more impact here than anywhere else: "
        "residents want to help but do not expect to be heard",
        "Acknowledge neglect publicly: quiet restoration without acknowledgement "
        "is accepted as normal; acknowledgement is noticed",
        "Low political influence means failures here rarely generate regulatory pressure; "
        "this is the trap: it stays neglected because no one important complains",
    ],
    "river_ankh": [
        "Fires and floods are immediately visible: the response needs to match the visibility",
        "Gradual contamination is the real risk: invest in water monitoring before the Shades notice",
        "Wharves and transport infrastructure here affect supply chains city-wide; "
        "a port closure compounds within days",
        "The barge guild is informal but well-organised: they will report river failures "
        "if asked; they are rarely asked",
    ],
}


def _district_description(district: District) -> str:
    return _DISTRICT_DESCRIPTIONS.get(district.id, district.description or district.name)


def _district_drivers(district: District) -> list[str]:
    return [
        f"Wealth archetype {district.wealth_archetype.replace('_', ' ')}: "
        "affects shock absorption, recovery rate, and remedy effectiveness",
        f"Infrastructure quality modifier {district.infrastructure_quality:.1f}x: "
        + ("below average, higher failure rate" if district.infrastructure_quality > 1.0
           else "above average, lower failure rate"),
        f"Political influence {district.political_influence:.1f}x: "
        + ("failures here amplify regulatory pressure significantly" if district.political_influence >= 1.5
           else "failures here generate limited regulatory pressure"),
        f"Discovery time {district.discovery_time_hours[0]:.0f}–{district.discovery_time_hours[1]:.0f} hours base: "
        "building type modifiers and stressors apply on top",
    ]


def _district_actions(district: District) -> list[str]:
    return _DISTRICT_ACTIONS.get(district.id, [
        "Apply technical restoration to failed buildings",
        "Consider resilience investment to reduce future failure probability",
        "Monitor local trust trend: sustained decline warrants direct intervention",
    ])


def _district_extra(district: District, failed) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    total = len(district.buildings)
    operational = district.operational_building_count
    rows.append(("Buildings operational", f"{operational} / {total}"))
    if failed:
        names = ", ".join(b.name for b in failed[:4])
        if len(failed) > 4:
            names += f" +{len(failed) - 4} more"
        rows.append(("Currently failed", names))
    rows.append(("Local trust", f"{district.local_trust.value:.0f} / 100"))
    return rows


def _section(parent, f, heading: str, items: list[str], bullet: str = "•") -> None:
    ctk.CTkLabel(
        parent, text=heading.upper(),
        font=f.small_bold, text_color=ACCENT_BROWN,
    ).pack(anchor="w", padx=20, pady=(12, 4))

    for item in items:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(
            row, text=bullet,
            font=f.small_bold, text_color=ACCENT_BROWN,
            width=16, anchor="w",
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            row, text=item,
            font=f.small, text_color=INK,
            wraplength=490, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)


def _pct_colour(pct: float) -> str:
    if pct >= 80:
        return TRUST_GOOD
    if pct >= 50:
        return TRUST_WARN
    return TRUST_BAD
