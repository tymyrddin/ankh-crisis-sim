"""Info popups: clickable explanations for dashboard metrics, status, and districts."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.gui.theme import (
    ACCENT_BROWN, INK, INK_MUTED, PAPER, PAPER_DARK,
    TRUST_BAD, TRUST_GOOD, TRUST_WARN, METRIC_COLOURS, fonts,
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
            "failure and recovers slowly when things are seen to work."
        ),
        "drivers": [
            "Infrastructure failures, especially visible ones, decay trust per day unresolved",
            "Low trust (below 30) reduces tax collection efficiency, compressing budget further",
            "District trust levels are averaged into the global figure; poor districts have less weight",
            "Prompt remedies, accountability actions, and compensation all slow decay",
        ],
        "actions": [
            "Issue a press statement through the Ankh-Morpork Times: immediate small effect, "
            "but the Times may ask questions",
            "Commission Moist von Lipwig for a high-visibility restoration: fast trust recovery, "
            "initial dip, politically complex",
            "Apply technical restorations quickly: visible action is trusted action; "
            "the longer a failure sits, the more trust it costs",
            "Prioritise Cockbill Street and the Shades: Vimes's presence there has an "
            "outsized trust effect far exceeding their political weight",
            "Do nothing. Trust recovers at 2 points per month without new incidents. "
            "Sometimes patience is the action.",
        ],
    },

    "budget": {
        "title": "Budget",
        "description": (
            "The city treasury: the only constraint that is not political. Without budget, remedies "
            "cannot be applied, compensation cannot be paid, and investment is impossible. Unlike trust, "
            "budget does not recover by itself; it requires income. Monthly income arrives from taxes, "
            "guild fees, trade tariffs, and UU's symbolic contribution."
        ),
        "drivers": [
            "Trust below 30 triggers a tax collection penalty: income falls by 40%",
            "Transport and commerce disruptions reduce trade tariff income",
            "Technical restoration costs 150 AM$ per event; resilience investment costs 400 AM$",
            "Compensation and accountability actions are cheaper but do not fix the underlying problem",
        ],
        "actions": [
            "Emergency borrowing from the Royal Bank of Ankh-Morpork: available up to 2,000 AM$, "
            "but regulatory pressure increases by 15; Vetinari dislikes debt",
            "Borrowing from the Überwald banking consortium: no domestic political cost, "
            "but creates strategic exposure to foreign influence",
            "Raise guild fees: immediate revenue, significant regulatory pressure spike; "
            "the guilds will remember",
            "Defer maintenance on low-priority buildings: saves spending in the short term, "
            "increases infrastructure failure probability",
            "Issue a special trade levy through the Guild of Merchants: contested, slow to collect",
            "Recover public trust above 30: restores full tax collection efficiency; "
            "the most sustainable budget fix",
        ],
    },

    "regulatory_pressure": {
        "title": "Regulatory Pressure",
        "description": (
            "The combined force of guilds, nobility, press, and concerned factions demanding that "
            "something be done. At low levels it is background noise every Patrician learns to ignore. "
            "Above 60, the Watch receives authorisation for extraordinary measures. "
            "Above 80, Moist von Lipwig receives a polite note that he cannot decline."
        ),
        "drivers": [
            "Guild complaints add 8 points; noble outcry adds 12",
            "Media campaigns and Watch requests add 5–8 points each",
            "Repeated failures in the same district or on the same problem add 15 (cumulative)",
            "Successful restorations and accountability actions reduce pressure",
            "A new crisis elsewhere reduces pressure on the previous problem by 5, "
            "the city's attention is finite",
        ],
        "actions": [
            "Grant audience to guild representatives: releases pressure temporarily; "
            "the guilds feel heard and reduce formal demands",
            "Accountability actions: identify and publicly hold someone responsible; "
            "reduces pressure by 12 if the target is correct; backfires if the target is popular",
            "Successful technical restoration of a high-profile failure reduces pressure by 8",
            "Guild negotiation: formal concessions in exchange for reduced formal complaints",
            "Do nothing for a week without new incidents: pressure decreases 2 points per week "
            "on its own; the city has a short memory",
        ],
    },

    "political_stability": {
        "title": "Political Stability",
        "description": (
            "The absence of a credible alternative to the current arrangement. Vetinari's genius "
            "is not popularity, it is making instability unthinkable. When this metric falls, "
            "factions begin calculating whether the moment has arrived. Guild wars, noble conspiracies, "
            "and food or water crises are the primary triggers."
        ),
        "drivers": [
            "Trust collapse below 25 causes stability to decay 2 points per tick, the domino",
            "Guild war: -30. Noble conspiracy: -20. Food or water shortage: -20",
            "Succession rumours are the most acute trigger: -40 if activated",
            "Successful crisis management, guild concessions, and time without incident all recover it",
        ],
        "actions": [
            "Foster rivalry between the Assassins' and Thieves' Guilds: their attention "
            "turns inward; the Palace recedes from their focus",
            "Invite key noble families to dinner individually: the personal touch; "
            "time-consuming but each dinner removes a potential conspirator from the calculation",
            "Promote Carrot Ironfoundersson to a visible public role: his popularity provides "
            "a stability shield; his loyalty to the city is unquestioned",
            "Commission a visible public work: bridge repair, market improvement; "
            "demonstrated competence is the most durable stabiliser",
            "Concessions to guilds in exchange for a formal show of support: costly but buys time",
            "Address succession rumours directly and decisively: publicly deny; privately arrange",
        ],
    },

    "legitimacy": {
        "title": "Legitimacy",
        "description": (
            "The moral and historical right to rule, distinct from trust, which is pragmatic, "
            "and stability, which is situational. Legitimacy changes slowly in either direction. "
            "It survives crises that destroy trust. But certain events, charter violations, "
            "guild withdrawal, failed coups, leave marks that time alone cannot erase."
        ),
        "drivers": [
            "Long unbroken competent rule adds 2 points per year, the most reliable source",
            "Guild endorsement adds 10; guild withdrawal subtracts 25",
            "Charter violation: -40. This is not recoverable through normal means",
            "A failed coup that Vetinari survives actually increases legitimacy by 5, "
            "the city respects someone who cannot be removed",
            "Carrot Ironfoundersson's public endorsement: +50. Effectively immediate maximum.",
        ],
        "actions": [
            "Negotiate formal Guild Council endorsement: expensive in concessions; "
            "the guilds will use the negotiation itself as leverage",
            "Commission and complete public works, slow, permanent, uncontestable",
            "Demonstrate competent crisis management consistently, "
            "the accumulated record matters more than any single event",
            "Maintain Carrot's loyalty and public presence: he does not seek power; "
            "that is precisely why his support is so valuable",
            "Do not violate the charter. Under any circumstances. "
            "The city has forgotten many things. Not that.",
        ],
    },

    "public_health": {
        "title": "Public Health",
        "description": (
            "A leading indicator: the first signal that water contamination, food shortage, "
            "or healthcare failure is compounding into something harder to fix. When public health "
            "falls below 50, disease cascades become possible and legitimacy follows. "
            "The poor districts feel it first; by the time Nap Hill notices, it is already serious."
        ),
        "drivers": [
            "Water pump failures: -5 delayed (contamination and disease risk accumulates)",
            "Food supply disruption: -6 delayed (malnutrition; low-wealth districts cannot buy alternatives)",
            "Hospital outage: -15 immediate, -5 delayed (untreated conditions compound rapidly)",
            "Workshop fires: -3 immediate (injuries, smoke, displacement)",
        ],
        "actions": [
            "Fund emergency capacity at Lady Sybil Free Hospital. This is the most direct intervention",
            "Dispatch water safety advisories via the clacks network: "
            "cheap, immediate, and the Times will print it",
            "Organise food distribution through the Guild of Merchants and Shambles: "
            "the guild handles logistics; the Patrician provides authorisation and cover",
            "Request Omnian Medical Mission expansion to under-served districts: "
            "they ask only for the right to preach; the trade is acceptable",
            "Deploy Watch officers to enforce quarantine if disease is suspected: "
            "Vimes will object; he is probably right; do it anyway",
            "Commission UU to investigate unusual outbreaks: unreliable; "
            "occasionally transformative; always interesting",
        ],
    },

    "crime_level": {
        "title": "Crime Level",
        "description": (
            "Unlicensed criminal activity: crime that the Thieves' Guild has not sanctioned "
            "and cannot control. The Guild's quota system normally keeps crime at a manageable, "
            "taxable level that everyone pretends not to notice. When this metric rises, "
            "someone is operating outside the arrangement, which concerns both the Watch and the Guild."
        ),
        "drivers": [
            "Watch post closures: +8 immediately because unlicensed actors fill the vacuum",
            "Food supply disruption: +3 delayed because economic desperation drives informal economies",
            "Workshop closures (unemployment): +6 because the employment-crime relationship is reliable",
            "Guild extortion events: +4 when organised crime is testing the boundaries of the arrangement",
            "Trust collapse: +10. When the social contract fails, so does social order",
        ],
        "actions": [
            "Negotiate with the Thieves' Guild to reassert control over unlicensed actors: "
            "fastest and cheapest; the Guild finds unlicensed competition as offensive as the Watch does",
            "Deploy additional Watch patrols to high-crime districts: "
            "visible and direct; resource-intensive",
            "Fund Vimes's overtime budget: his focused attention collapses crime in targeted areas; "
            "he is expensive in political capital but effective in results",
            "Activate Dept. of Silent Stability intelligence on criminal network structure: "
            "they already know; the question is whether they will share",
            "Offer limited amnesty for minor offenders: reduces immediate pressure; "
            "politically complex; Commander Vimes will have opinions",
            "Make a high-profile accountability example: visible deterrent; "
            "effective if the target is genuinely guilty; corrosive if they are not",
        ],
    },
}

_STATUS_INFO: dict[str, dict] = {
    "infrastructure": {
        "title": "Infrastructure Health",
        "description": (
            "The percentage of city buildings currently operational across all districts. "
            "This is the strategic picture: not which districts are angry, but what capacity "
            "the city actually has. Below 70%, cascades accelerate: failing buildings depend "
            "on other failing buildings, and the dependency chains begin to close."
        ),
        "drivers": [
            "Every unresolved building failure reduces this percentage",
            "Remedy completion restores buildings: technical restoration is fastest",
            "Cascade events create secondary failures from a single root cause",
            "Poor infrastructure districts (Shades, Cockbill) have higher baseline failure rates",
        ],
        "actions": [
            "Prioritise technical restoration on critical infrastructure: "
            "water sources, power stations, and healthcare first; "
            "everything else depends on these",
            "Resilience investment prevents recurrence. This is more expensive, "
            "but each upgraded building reduces future failure probability",
            "Triage by dependency: fix the building that everything else depends on first; "
            "a restored water source stabilises brewery, fire service, and healthcare simultaneously",
            "Emergency engineering corps via Guild of Engineers gives rapid deployment; "
            "they will charge accordingly",
            "Request UU Artificers for unusual structural problems. The "
            "success rates vary; enthusiasm is consistent",
        ],
    },

    "incidents": {
        "title": "Active Incidents",
        "description": (
            "The number of detected failures currently awaiting a response. Hidden failures "
            "are not counted here, this is what has surfaced. Each unaddressed incident decays "
            "trust and may cascade. Above five simultaneous incidents, the Watch begins to struggle "
            "to prioritise; above ten, the city feels like it is in genuine crisis."
        ),
        "drivers": [
            "Event generation rolls each tick: stressors amplify probability",
            "Remedy application resolves events and removes them from this count",
            "Detection speed affects how quickly hidden events surface: "
            "more Watch patrols and clacks redundancy accelerate discovery",
            "Some incidents resolve through cascades: fixing the root cause resolves dependents",
        ],
        "actions": [
            "Apply remedies through building interactions, the primary response mechanism",
            "Prioritise by dependency chain, one upstream fix may resolve several downstream events",
            "Prioritise by district political influence if budget is constrained, "
            "cynical, but Nap Hill will escalate faster than the Shades",
            "Issue a press statement to manage narrative while the actual work proceeds. This "
            "buys hours of tolerance",
            "Accept some incidents as tolerable losses (do nothing). "
            "This produces a trust cost, but preserves budget for what matters",
            "Invest in detection improvement: find hidden failures before they cascade; "
            "more Watch patrols reduce discovery time across all districts",
        ],
    },

    "watch_coverage": {
        "title": "Watch Coverage",
        "description": (
            "The percentage of Watch posts currently staffed and operational. The Watch is "
            "the city's immune system, not just for crime, but for detection. Officers on patrol "
            "find failures before citizens do. When coverage falls, discovery times increase "
            "and crime fills the gap. The Thieves' Guild watches coverage numbers closely."
        ),
        "drivers": [
            "Watch understaffing events reduce coverage, caused by budget shortfall and underinvestment",
            "Technical restoration of Watch posts restores coverage",
            "Low coverage increases crime_level immediately, unlicensed activity tests the gaps",
            "Low coverage increases discovery times across all affected districts",
        ],
        "actions": [
            "Emergency officer recruitment via the Guild of Watchmen. This is "
            "not fast, but the only sustainable path",
            "Redeploy officers from low-crime, well-covered districts to high-crime areas: "
            "resource-neutral; politically sensitive in the districts losing coverage",
            "Request Vimes to personally walk the beat in the most critical district. "
            "His effect on discovery time and crime is large; his patience for bureaucracy is not",
            "Fund Watch overtime budget: short-term coverage while understaffing is resolved; "
            "effective and resented in equal measure",
            "Temporarily deputise trusted civilians in Cockbill Street and the Shades: "
            "legally ambiguous; Vimes will object; the community will accept what they know",
            "Negotiate with the Thieves' Guild for informal neighbourhood Watch to find out "
            "they already do this; the negotiation is about acknowledgement, not activation",
        ],
    },
}


class InfoPopup:
    """One window, torn down and rebuilt on every show."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._window: ctk.CTkToplevel | None = None
        self.on_emergency_borrow: Callable[[str], None] | None = None

    def show_metric(self, city: City, key: str) -> None:
        info = _METRIC_INFO.get(key)
        if not info:
            return
        metric = city.get_metric(key)
        value_str = f"{metric.value:,.0f} AM$" if key == "budget" else f"{metric.value:.0f} / 100"
        colour = METRIC_COLOURS.get(key, INK)

        action_buttons = None
        if key == "budget" and self.on_emergency_borrow:
            action_buttons = [
                (
                    "Royal Bank of Ankh-Morpork  +2,000 AM$",
                    "Domestic loan. Regulatory pressure +15. The guilds notice.",
                    lambda: self._do_borrow("royal_bank"),
                ),
                (
                    "Überwald Banking Consortium  +3,000 AM$",
                    "Foreign loan. No domestic political cost, but political stability −8. "
                    "The Patrician dislikes foreign creditors.",
                    lambda: self._do_borrow("ueberwald"),
                ),
            ]

        self._show(info["title"], value_str, colour, info["description"],
                   info["drivers"], info["actions"], action_buttons=action_buttons)

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
        f"{'below average, higher failure rate' if district.infrastructure_quality > 1.0 else 'above average, lower failure rate'}",
        f"Political influence {district.political_influence:.1f}x: "
        f"{'failures here amplify regulatory pressure significantly' if district.political_influence >= 1.5 else 'failures here generate limited regulatory pressure'}",
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