"""Popups: hover info and click menus for buildings and remedies."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from src.config.loader import GameConfig
from src.engine.remedies import get_available_remedies
from src.gui.theme import (
    ACCENT_BROWN,
    INK,
    INK_MUTED,
    PAPER,
    PAPER_DARK,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_RESPONDING,
    STATUS_YELLOW,
    fonts,
)
from src.models.building import Building, BuildingStatus
from src.models.city import City
from src.models.event import EventPhase, GameEvent

_TYPE_DESCRIPTIONS: dict[str, str] = {
    "guild_hq": (
        "A self-governing professional body holding monopoly rights over its trade. "
        "Functions simultaneously as economic regulator, tax intermediary, and informal court. "
        "Its failure is felt immediately by every member and client, which is to say, most of the city."
    ),
    "tavern": (
        "The social infrastructure of the district. Not merely a drinking establishment, "
        "a place where information circulates, alliances form, and the temperature of public mood "
        "becomes readable. The Watch sends observers here before anywhere else."
    ),
    "civic_amenity": (
        "A public space, cultural site, or civic facility. Non-essential in the strict sense: "
        "people do not die when it closes. They notice, however, and their noticing "
        "carries weight proportional to how visible the closure is."
    ),
    "slum_dwelling": (
        "High-density residential housing at the bottom of the city's resource distribution. "
        "The population here absorbs infrastructure failure rather than reporting it, "
        "until absorption becomes impossible."
    ),
    "middle_class_housing": (
        "Artisan and professional households. Politically vocal, economically productive, "
        "and acutely aware of service quality. A failure here generates complaints before "
        "it generates crisis, which is warning enough, if anyone is listening."
    ),
    "civic_institution": (
        "A major organ of city administration or services. Its operations underpin dozens "
        "of other processes. Failure is immediately visible to the public and press, "
        "and the political fallout arrives before the technical team does."
    ),
    "palace": (
        "The Patrician's seat of power. Infrastructure for governance itself. "
        "A failure here is not merely a technical problem, it is a statement. "
        "Vetinari is aware of this. So is everyone else."
    ),
    "university": (
        "Unseen University: a city within a city, operating under its own charter, "
        "its own physics, and its own definition of emergency. The city tolerates it "
        "because it is less dangerous inside the agreement than outside it."
    ),
    "water_source": (
        "Primary water pumping infrastructure. The supply chain for water, sanitation, "
        "and public health originates here. Every building downstream depends on it. "
        "Failure is noticed within hours; disease risk follows within days."
    ),
    "power_source": (
        "Electrical generation or distribution node. Energy is the dependency that "
        "underpins every other dependency. When this fails, it does not fail alone,"
        "it cascades immediately through everything connected to it."
    ),
    "clacks_tower": (
        "Communications relay in the Grand Trunk or city network. A single tower failure "
        "degrades the whole: response times lengthen, coordination falters, and incidents "
        "that would have been caught become incidents that are merely discovered later."
    ),
    "food_supply": (
        "Primary food distribution point. Ankh-Morpork runs on just-in-time logistics, "
        "there is no strategic reserve. A disruption here becomes a price spike within hours "
        "and a political crisis within days."
    ),
    "brewery": (
        "Supplier to the taverns, and through them to morale, to the Watch's informants, "
        "and to the social cohesion that no official programme has ever successfully replaced. "
        "Its failure is measurable before it is reportable."
    ),
    "transport": (
        "Physical infrastructure for movement and trade. Supply chains, labour flows, "
        "and emergency responses all depend on this functioning. Structural decay "
        "hides longer than almost any other failure mode."
    ),
    "communications_office": (
        "Commercial clacks operator or messaging exchange. The company office coordinates "
        "the network; its failure degrades service even when the towers remain standing. "
        "It holds contracts and liabilities that become relevant the moment something goes wrong."
    ),
    "healthcare": (
        "Medical care facility. When this fails, people cannot get treatment. "
        "The trust collapse is instantaneous and the regulatory pressure is severe. "
        "The long-term legitimacy damage outlasts both."
    ),
    "security": (
        "Watch post or security institution. Coverage determines discovery time across "
        "the entire district. When a post goes dark, crime fills the gap within hours, "
        "and the Thieves' Guild notices before the Patrician's Office does."
    ),
    "tech_business": (
        "Technical firm providing data management or resilience services to guilds, the Bank, "
        "and city institutions. Vendor monoculture risk is extreme: one firm, one point of failure, "
        "multiple critical clients with no alternative."
    ),
    "hackerspace": (
        "Informal technical collective of unclear legal status and considerable practical value. "
        "They find things before anyone else, and tell the right people. Sometimes. "
        "The Patrician is aware of their existence. This is itself a policy decision."
    ),
    "workshop": (
        "Industrial manufacturing or craft facility. Local failure by default, not city-wide. "
        "But fire spreads, unemployment compounds, and a district that loses its employment "
        "base does not recover quickly or quietly."
    ),
    "fire_service": (
        "Fire suppression and emergency response. A force multiplier for every other disaster: "
        "present, it contains; absent, it allows. Its failures are invisible until the moment "
        "they become catastrophic and visible to everyone."
    ),
    "media": (
        "Newspaper or press operation. Shapes public narrative, which is to say, shapes "
        "what the public believes is happening. A functioning press beats rumour. "
        "Silence does not: rumour fills the void faster and is considerably less accurate."
    ),
    "intelligence_service": (
        "An institution that does not officially exist, performing functions that are not "
        "officially performed. Its operational failure is invisible by design, which is to say, "
        "you will not know it has failed until something that was supposed to be quietly prevented "
        "is not. At which point, deniability becomes the primary product."
    ),
    "apothecary": (
        "A small dispensary, herbalist, or informal healer serving the immediate district. "
        "Not a hospital: there are no wards, no transfers, no Guild oversight worth mentioning. "
        "When it closes, the people who depended on it have nowhere else nearby to go. "
        "In the Shades, this is the only medical care that exists."
    ),
}


# Display-only remedy labels per building category. No mechanic changes.
_CATEGORY_MAP: dict[str, str] = {
    "water_source": "infrastructure",
    "power_source": "infrastructure",
    "clacks_tower": "communications",
    "communications_office":"communications",
    "healthcare": "healthcare",
    "security": "security",
    "fire_service": "fire_service",
    "food_supply": "food",
    "brewery": "food",
    "transport": "transport",
    "media": "media",
    "civic_institution": "civic",
    "civic_amenity": "civic",
    "palace": "civic",
    "university": "education",
    "guild_hq": "guild",
    "tech_business": "trade",
    "hackerspace": "trade",
    "workshop": "trade",
    "slum_dwelling": "housing",
    "middle_class_housing": "housing",
    "tavern": "hospitality",
    "intelligence_service": "intelligence",
    "apothecary": "apothecary",
}

# (label, description) keyed by category, then remedy id.
_REMEDY_LABELS: dict[str, dict[str, tuple[str, str]]] = {
    "infrastructure": {
        "technical_restoration": (
            "Emergency Repair",
            "Patch the immediate fault. Fast, but the underlying condition remains.",
        ),
        "resilience_investment": (
            "Infrastructure Overhaul",
            "Rebuild to a higher standard. Slow and expensive, but permanently reduces risk.",
        ),
        "operational_workaround": (
            "Temporary Bypass",
            "Reroute supply. Shifts pressure to adjacent systems: a short-term fix with long-term consequences.",
        ),
        "public_compensation": (
            "Public Notice & Compensation",
            "Issue warnings and financial relief to affected households. Buys goodwill, not repairs.",
        ),
        "accountability_actions": (
            "Commission Technical Inquiry",
            "Assign responsibility and investigate. May satisfy public anger or produce a convenient scapegoat.",
        ),
        "press_statement": (
            "Issue Official Statement",
            "Manage the narrative. Buys time; backfires if no substantive action follows.",
        ),
        "do_nothing": (
            "Defer Maintenance",
            "Ignore the problem. Trust erodes, cascades accumulate.",
        ),
    },
    "communications": {
        "technical_restoration": (
            "Restore Signal",
            "Get the network back up. Fast fix; recurrence likely without underlying repair.",
        ),
        "resilience_investment": (
            "Network Upgrade",
            "Rebuild relay infrastructure to full specification. Slow, costly, lasting.",
        ),
        "operational_workaround": (
            "Reroute Traffic",
            "Divert through alternate relays. Maintains service here; degrades capacity elsewhere.",
        ),
        "public_compensation": (
            "Refund Subscribers",
            "Compensate affected users and commercial clients. Trust patch, no technical fix.",
        ),
        "accountability_actions": (
            "Suspend Tower Operator",
            "Assign blame publicly. May satisfy guild pressure or trigger a costly dispute.",
        ),
        "press_statement": (
            "Issue Network Bulletin",
            "Inform the public of progress. Slows trust decay while action is pending.",
        ),
        "do_nothing": (
            "No Comment",
            "Say nothing, do nothing. Rumour fills the void faster than the signal returns.",
        ),
    },
    "healthcare": {
        "technical_restoration": (
            "Emergency Staffing",
            "Draft in additional surgeons or healers. Addresses the immediate shortfall.",
        ),
        "resilience_investment": (
            "Facility Refurbishment",
            "Rebuild and re-equip the ward. Long downtime, lasting improvement.",
        ),
        "operational_workaround": (
            "Transfer Patients",
            "Send cases to another facility. Relieves pressure here; increases it elsewhere.",
        ),
        "public_compensation": (
            "Compensation Fund",
            "Financial relief to those who couldn't receive care. Helps trust, not health.",
        ),
        "accountability_actions": (
            "Demand Medical Inquiry",
            "Public investigation into the failure. High visibility and considerable political risk.",
        ),
        "press_statement": (
            "Release Health Bulletin",
            "Reassure the public about care availability. Effective only while the crisis is fresh.",
        ),
        "do_nothing": (
            "Ignore the Situation",
            "Trust collapses fastest here. The public knows when it cannot get treatment.",
        ),
    },
    "security": {
        "technical_restoration": (
            "Deploy Reserve Officers",
            "Bring Watch reserves to cover the gap. Restores basic coverage quickly.",
        ),
        "resilience_investment": (
            "Barracks & Equipment Overhaul",
            "Upgrade facilities and armoury. Slow, expensive, lasting.",
        ),
        "operational_workaround": (
            "Reassign from Neighbouring Post",
            "Thin coverage elsewhere to shore up here. A tactical shuffle with strategic cost.",
        ),
        "public_compensation": (
            "Victim Support Fund",
            "Compensate those affected by crime during the lapse. Goodwill without prevention.",
        ),
        "accountability_actions": (
            "Discipline Commanding Officer",
            "Assign blame publicly. The Watch resents it; the public approves, briefly.",
        ),
        "press_statement": (
            "Issue Security Advisory",
            "Warn citizens and manage expectations. Buys time while cover is restored.",
        ),
        "do_nothing": (
            "Stand Down",
            "Ignore the gap. Crime fills it within hours.",
        ),
    },
    "fire_service": {
        "technical_restoration": (
            "Redeploy Reserve Engines",
            "Bring emergency equipment to restore response capacity.",
        ),
        "resilience_investment": (
            "Station Upgrade",
            "Rebuild and re-equip to full specification. Significant downtime, significant benefit.",
        ),
        "operational_workaround": (
            "Mutual Aid Request",
            "Draw resources from a neighbouring district. Helps here; weakens there.",
        ),
        "public_compensation": (
            "Affected Residents Fund",
            "Support those who suffered losses during the coverage gap.",
        ),
        "accountability_actions": (
            "Investigate Fire Service Command",
            "Assign responsibility for the lapse. Politically useful, operationally disruptive.",
        ),
        "press_statement": (
            "Issue Emergency Notice",
            "Inform residents of reduced coverage. Manages expectations, reduces panic.",
        ),
        "do_nothing": (
            "Hope There's No Fire",
            "The city is largely flammable. This option carries obvious risks.",
        ),
    },
    "food": {
        "technical_restoration": (
            "Emergency Resupply",
            "Source replacement stock at cost. Quick fix, higher price.",
        ),
        "resilience_investment": (
            "Supply Chain Upgrade",
            "Build reserves and redundancy into logistics. Expensive, lasting.",
        ),
        "operational_workaround": (
            "Source Alternatives",
            "Switch to secondary suppliers. Disrupts existing contracts; maintains supply.",
        ),
        "public_compensation": (
            "Distribute Emergency Rations",
            "Provide subsidised food to the affected district. Buys political goodwill.",
        ),
        "accountability_actions": (
            "Blame the Merchants",
            "Commission an inquiry into price manipulation or supply failure. Popular with the poor.",
        ),
        "press_statement": (
            "Issue Market Reassurance",
            "Calm public anxiety about shortages. Effective only if supply actually returns soon.",
        ),
        "do_nothing": (
            "Let the Market Decide",
            "Prices spike, tempers rise, and the Watch works overtime.",
        ),
    },
    "transport": {
        "technical_restoration": (
            "Emergency Structural Repair",
            "Patch the immediate damage. Fast, but structural risk remains.",
        ),
        "resilience_investment": (
            "Full Infrastructure Rebuild",
            "Restore to engineering standard. Long closure, lasting outcome.",
        ),
        "operational_workaround": (
            "Establish Detour Route",
            "Redirect traffic. Adds journey time and strain to other routes.",
        ),
        "public_compensation": (
            "Transport Disruption Fund",
            "Compensate traders and commuters for losses during the closure.",
        ),
        "accountability_actions": (
            "Commission Engineering Inquiry",
            "Investigate why maintenance was deferred. Politically safe; rarely produces change.",
        ),
        "press_statement": (
            "Issue Progress Update",
            "Keep the public informed of repair timelines. Manages anger.",
        ),
        "do_nothing": (
            "Leave It",
            "Structural decay continues. Eventual failure will be considerably more expensive.",
        ),
    },
    "media": {
        "technical_restoration": (
            "Restore Press Operations",
            "Fix the immediate printing failure. Back to presses quickly.",
        ),
        "resilience_investment": (
            "Print House Modernisation",
            "Upgrade machinery and facilities. Slow, but permanently improves reliability.",
        ),
        "operational_workaround": (
            "Arrange Guest Printing",
            "Use a competitor's press. Keeps publication running; reveals vulnerabilities.",
        ),
        "public_compensation": (
            "Subscriber Compensation",
            "Refund readers and advertisers. Goodwill preserved, content gap remains.",
        ),
        "accountability_actions": (
            "Investigate Editorial Failure",
            "Public inquiry into press reliability. May expose things best left unexposed.",
        ),
        "press_statement": (
            "Issue Temporary Bulletin",
            "Minimal communication to maintain presence. Buys time.",
        ),
        "do_nothing": (
            "Go Silent",
            "The void fills with rumour. Rumour is rarely flattering to the Patrician.",
        ),
    },
    "civic": {
        "technical_restoration": (
            "Emergency Restoration",
            "Restore essential functions immediately. Quick but superficial.",
        ),
        "resilience_investment": (
            "Civic Refurbishment",
            "Full structural and operational upgrade. Significant investment, lasting benefit.",
        ),
        "operational_workaround": (
            "Redirect Services",
            "Route functions through neighbouring facilities. Manages the gap temporarily.",
        ),
        "public_compensation": (
            "Public Goodwill Fund",
            "Financial relief to affected citizens. A trust patch.",
        ),
        "accountability_actions": (
            "Commission Administrative Review",
            "Investigate the failure publicly. Politically useful.",
        ),
        "press_statement": (
            "Statement of Civic Intent",
            "Affirm commitment to restoration. Buys time.",
        ),
        "do_nothing": (
            "Postpone Indefinitely",
            "Public confidence erodes. The queue for other failures grows.",
        ),
    },
    "education": {
        "technical_restoration": (
            "Emergency Academic Restoration",
            "Restore immediate operational capacity. The Archchancellor's patience has limits.",
        ),
        "resilience_investment": (
            "Faculty Infrastructure Upgrade",
            "Comprehensive rebuilding of affected facilities. The University operates on its own schedule.",
        ),
        "operational_workaround": (
            "Temporary Closure & Reallocation",
            "Suspend affected operations and redistribute staff. Loss of research continuity.",
        ),
        "public_compensation": (
            "Scholar Stipend Fund",
            "Compensation for disrupted students and faculty. The University requests this be substantial.",
        ),
        "accountability_actions": (
            "Call for a University Inquiry",
            "An internal investigation. The University will conduct it entirely on its own terms.",
        ),
        "press_statement": (
            "Chancellor's Public Statement",
            "Official reassurance from the academic leadership. The Times will print it verbatim.",
        ),
        "do_nothing": (
            "Leave to the Wizards",
            "The University manages its own crises. Usually.",
        ),
    },
    "trade": {
        "technical_restoration": (
            "Emergency Repair",
            "Fix the immediate operational failure. Rapid restoration of trade functions.",
        ),
        "resilience_investment": (
            "Facility & Systems Upgrade",
            "Invest in lasting operational improvements. Expensive, durable.",
        ),
        "operational_workaround": (
            "Temporary Workaround",
            "Improvise a bypass. Keeps income flowing; documents nothing.",
        ),
        "public_compensation": (
            "Client Compensation",
            "Compensate affected businesses and customers. Goodwill, not fixes.",
        ),
        "accountability_actions": (
            "Guild Inquiry",
            "Formal investigation into the failure. Guildmasters take this personally.",
        ),
        "press_statement": (
            "Trade Statement",
            "Reassure commercial partners and the public. Narrative management.",
        ),
        "do_nothing": (
            "Ignore It",
            "Trade disruption compounds. Competitors notice.",
        ),
    },
    "housing": {
        "technical_restoration": (
            "Emergency Repairs",
            "Patch the most immediate structural or service failures.",
        ),
        "resilience_investment": (
            "Housing Improvement Programme",
            "Substantive upgrade to fabric and services. Residents remember who paid for it.",
        ),
        "operational_workaround": (
            "Temporary Relocation",
            "Move affected residents to alternative accommodation. Disrupts community structure.",
        ),
        "public_compensation": (
            "Resident Compensation Fund",
            "Financial support for displaced or affected residents.",
        ),
        "accountability_actions": (
            "Landlord & Builder Inquiry",
            "Investigate responsibility for the failure. Popular with residents.",
        ),
        "press_statement": (
            "Reassure Residents",
            "Communicate action plan to the affected community. Manages anxiety.",
        ),
        "do_nothing": (
            "Leave Residents to Manage",
            "They are accustomed to being left to manage. Their trust reflects this.",
        ),
    },
    "hospitality": {
        "technical_restoration": (
            "Emergency Reopening",
            "Get the doors back open. Morale returns with the first pint.",
        ),
        "resilience_investment": (
            "Full Premises Refurbishment",
            "Rebuild and reopen properly. Worth the wait, according to regulars.",
        ),
        "operational_workaround": (
            "Temporary Venue",
            "Set up a makeshift arrangement. Not the same, but the Watch informants need somewhere to sit.",
        ),
        "public_compensation": (
            "Complimentary Round",
            "A goodwill gesture to regulars. Costs little, means a great deal.",
        ),
        "accountability_actions": (
            "Investigate the Landlord",
            "Formal inquiry into the management failure. The regulars will have opinions.",
        ),
        "press_statement": (
            "Post a Notice",
            "Communicate the situation to patrons. Reduces grumbling slightly.",
        ),
        "do_nothing": (
            "Keep the Doors Shut",
            "Trust erodes quickly. The social temperature of the district with it.",
        ),
    },
    "intelligence": {
        "technical_restoration": (
            "Operational Reset",
            "Reactivate dormant assets and restore routine collection. Fast. The underlying vulnerability remains.",
        ),
        "resilience_investment": (
            "Structural Reorganisation",
            "Rebuild the network from new foundations. Slow, thorough, and not something that can be discussed "
            "in any committee with a record.",
        ),
        "operational_workaround": (
            "Redirect Existing Assets",
            "Repurpose other operatives to cover the gap. Effective in the short term. "
            "Depleting in the medium term. Do not examine what they are being redirected from.",
        ),
        "public_compensation": (
            "Official Diversion",
            "Draw attention to something else. Buys time. Does not fix anything. "
            "Works best applied early; considerably less so once the story exists.",
        ),
        "accountability_actions": (
            "Internal Review",
            "Identify the failure point and the person responsible for it. "
            "Conducted quietly. Conclusions not shared. Outcomes occasionally apparent in retrospect.",
        ),
        "press_statement": (
            "Managed Silence",
            "Ensure the incident remains unprinted. Standard practice. "
            "The Times editor is, as always, cooperative within the usual understanding.",
        ),
        "do_nothing": (
            "Monitor and Wait",
            "Observe. Do not intervene. The risk of action may exceed the risk of inaction. "
            "This is a legitimate assessment. Probably.",
        ),
    },
    "guild": {
        "technical_restoration": (
            "Bring in a Mediator",
            "Negotiate a rapid settlement. Work resumes quickly, but the underlying dispute is not resolved.",
        ),
        "resilience_investment": (
            "Address the Underlying Grievances",
            "Structural reform of wages, conditions, or representation. Slow, expensive, but earns lasting loyalty.",
        ),
        "operational_workaround": (
            "Hire Replacement Labour",
            "Bypass the guild entirely. Keeps operations running; the guild will remember. Political cost is high.",
        ),
        "public_compensation": (
            "Buy Off the Strikers",
            "Direct financial settlement. Work resumes; the precedent invites repetition.",
        ),
        "accountability_actions": (
            "Sanction Guild Leadership",
            "Assign blame publicly and discipline the organisers. May satisfy the press; will not satisfy the members.",
        ),
        "press_statement": (
            "Issue Conciliatory Statement",
            "Signal willingness to negotiate without committing to anything. "
            "Buys time; backfires if no action follows.",
        ),
        "do_nothing": (
            "Wait It Out",
            "Let the strike run. Trust erodes daily. The guild is watching how long the Patrician holds.",
        ),
    },
    "apothecary": {
        "technical_restoration": (
            "Emergency Restock",
            "Procure medicines and get the doors open. Fast, but supply remains precarious.",
        ),
        "resilience_investment": (
            "Proper Premises & Equipment",
            "Upgrade the facility and secure Guild certification. Slow and expensive; "
            "considerably harder to close without cause afterwards.",
        ),
        "operational_workaround": (
            "Refer to Nearest Physician",
            "Direct cases to the closest Guild-licensed practitioner. "
            "May be some distance away. In the Shades, it is.",
        ),
        "public_compensation": (
            "Open the Door for Free",
            "Treat without payment until supplies run out. "
            "Trust rises; stock depletes faster than it is replaced.",
        ),
        "accountability_actions": (
            "Guild Inspection",
            "Request formal review by the Guild of Physicians. "
            "May resolve the problem. May also surface other problems. Attention cuts both ways.",
        ),
        "press_statement": (
            "Post a Notice",
            "Inform the district of the situation and what is being done about it. "
            "Manages expectations. Does not manage the underlying shortage.",
        ),
        "do_nothing": (
            "Remain Closed",
            "The district has no alternative nearby. Trust in the city's capacity to care "
            "for its residents decays accordingly.",
        ),
    },
}


def _remedy_text(type_id: str, remedy_id: str, default_label: str, default_desc: str) -> tuple[str, str]:
    category = _CATEGORY_MAP.get(type_id)
    if category:
        override = _REMEDY_LABELS.get(category, {}).get(remedy_id)
        if override:
            return override
    return default_label, default_desc


def _status_colour(status: BuildingStatus) -> str:
    return {
        BuildingStatus.OPERATIONAL: STATUS_GREEN,
        BuildingStatus.DEGRADED: STATUS_YELLOW,
        BuildingStatus.FAILED: STATUS_RED,
    }.get(status, INK_MUTED)


def _buildings_relying_on(
    building: Building,
    city: City,
    district_id: str | None = None,
) -> list[tuple[Building, str]]:
    """Buildings consuming something this one produces, with the dependency level.

    Restricting to district_id matches cascade scope "neighbours": buildings in
    other districts are not real cascade targets there.
    """
    produced = set(building.produces)
    if not produced:
        return []

    result: list[tuple[Building, str]] = []
    for district in city.districts.values():
        if district_id and district.id != district_id:
            continue
        for b in district.buildings.values():
            if b.id == building.id:
                continue
            consuming = set(b.consumes) & produced
            if not consuming:
                continue
            if consuming & set(b.dependencies.critical):
                level = "critical"
            elif consuming & set(b.dependencies.operational):
                level = "operational"
            else:
                level = "strategic"
            result.append((b, level))

    level_order = {"critical": 0, "operational": 1, "strategic": 2}
    status_order = {BuildingStatus.FAILED: 0, BuildingStatus.DEGRADED: 1, BuildingStatus.OPERATIONAL: 2}
    result.sort(key=lambda x: (level_order.get(x[1], 3), status_order.get(x[0].status, 3)))
    return result


def _section_heading(parent, f, text: str) -> None:
    ctk.CTkLabel(
        parent, text=text.upper(),
        font=f.small_bold, text_color=ACCENT_BROWN,
    ).pack(anchor="w", padx=20, pady=(14, 4))


def _bullet(parent, f, text: str, colour: str = INK) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=2)
    ctk.CTkLabel(
        row, text="◆", font=f.small_bold, text_color=ACCENT_BROWN,
        width=16, anchor="w",
    ).pack(side="left", padx=(0, 6))
    ctk.CTkLabel(
        row, text=text, font=f.small, text_color=colour,
        wraplength=530, justify="left", anchor="w",
    ).pack(side="left", fill="x", expand=True)


class HoverPopup:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self._popup: tk.Toplevel | None = None

    def show(self, building: Building, district_name: str, x: int, y: int) -> None:
        self.hide()
        f = fonts()
        self._popup = tk.Toplevel(self.root)
        self._popup.wm_overrideredirect(True)
        self._popup.geometry(f"+{x + 15}+{y + 15}")
        self._popup.attributes("-topmost", True)

        frame = ctk.CTkFrame(self._popup, fg_color=PAPER_DARK)
        frame.pack()

        status_colours = {
            "operational": STATUS_GREEN,
            "degraded": STATUS_YELLOW,
            "failed": STATUS_RED,
        }
        colour = status_colours.get(building.status.value, INK_MUTED)

        ctk.CTkLabel(
            frame, text=building.name,
            font=f.body_bold, text_color=INK,
        ).pack(padx=12, pady=(8, 2))

        ctk.CTkLabel(
            frame, text=f"District: {district_name}",
            font=f.small, text_color=INK_MUTED,
        ).pack(padx=12)

        ctk.CTkLabel(
            frame,
            text=f"Status: {building.status.value.title()}",
            font=f.small,
            text_color=colour,
        ).pack(padx=12, pady=(2, 8))

    def hide(self) -> None:
        if self._popup:
            self._popup.destroy()
            self._popup = None


class RemedyMenu:
    """Building briefing: description, dependencies, incident status and remedy actions."""

    def __init__(self, root: ctk.CTk, cfg: GameConfig):
        self.root = root
        self.cfg = cfg
        self._window: ctk.CTkToplevel | None = None
        self.on_remedy_selected: Callable[[str, str], None] | None = None

    def show(
        self,
        building: Building,
        event: GameEvent | None,
        city: City,
        x: int,
        y: int,
        current_tick: int = 0,
    ) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

        f = fonts()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        px = min(x + 10, sw - 660)
        py = min(y + 10, sh - 640)

        win = ctk.CTkToplevel(self.root)
        win.title(building.name)
        win.geometry(f"640x620+{px}+{py}")
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        self._window = win
        win.protocol("WM_DELETE_WINDOW", self.hide)

        header = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text=building.name,
            font=(f.family, 18, "bold"), text_color=INK,
        ).pack(side="left", padx=20, pady=12)

        if event and event.phase == EventPhase.RESPONDING:
            badge_text = "● RESPONDING"
            badge_colour = STATUS_RESPONDING
        else:
            badge_text = f"● {building.status.value.upper()}"
            badge_colour = _status_colour(building.status)

        ctk.CTkLabel(
            header, text=badge_text,
            font=f.body_bold, text_color=badge_colour,
        ).pack(side="right", padx=20, pady=12)

        district = city.districts.get(building.district_id)
        district_name = district.name if district else building.district_id
        type_label = building.type_id.replace("_", " ").title()
        ctk.CTkLabel(
            win,
            text=f"{type_label}  ·  {district_name}  ·  Sensitivity: {building.sensitivity.replace('_', ' ')}",
            font=f.small, text_color=INK_MUTED,
        ).pack(anchor="w", padx=20, pady=(8, 0))

        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        description = _TYPE_DESCRIPTIONS.get(
            building.type_id,
            f"A {type_label.lower()} operating within {district_name}.",
        )
        ctk.CTkLabel(
            scroll, text=description,
            font=f.body, text_color=INK,
            wraplength=575, justify="left",
        ).pack(anchor="w", padx=20, pady=(14, 4))

        if building.consumes:
            _section_heading(scroll, f, "Depends on (consumes)")
            deps = building.dependencies
            for resource in building.consumes:
                if resource in deps.critical:
                    tag, colour = "Critical", STATUS_RED
                elif resource in deps.operational:
                    tag, colour = "Operational", STATUS_YELLOW
                else:
                    tag, colour = "Strategic", INK_MUTED
                _bullet(scroll, f, f"{resource.replace('_', ' ')}: {tag}", colour)

        if building.produces:
            _section_heading(scroll, f, "Produces (outputs)")
            for resource in building.produces:
                _bullet(scroll, f, resource.replace("_", " "), INK_MUTED)

        relying = _buildings_relying_on(building, city)
        if relying:
            _section_heading(scroll, f, "Relied on by")
            shown = relying[:8]
            for b, level in shown:
                level_tag = {"critical": "critically", "operational": "operationally"}.get(level, "strategically")
                dot_colour = _status_colour(b.status)
                _bullet(
                    scroll, f,
                    f"{b.name}: depends {level_tag}  ·  {b.status.value}",
                    dot_colour if b.status != BuildingStatus.OPERATIONAL else INK_MUTED,
                )
            if len(relying) > 8:
                ctk.CTkLabel(
                    scroll,
                    text=f"  +{len(relying) - 8} more buildings depend on this",
                    font=f.small, text_color=INK_MUTED,
                ).pack(anchor="w", padx=36, pady=2)

        if event and event.is_visible:
            phase_colour = STATUS_RESPONDING if event.phase == EventPhase.RESPONDING else STATUS_YELLOW
            _section_heading(scroll, f, "Active incident")

            ctk.CTkLabel(
                scroll, text=event.name,
                font=f.body_bold, text_color=phase_colour,
            ).pack(anchor="w", padx=20, pady=(0, 4))

            if event.story:
                ctk.CTkLabel(
                    scroll, text=event.story,
                    font=f.small, text_color=INK,
                    wraplength=575, justify="left",
                ).pack(anchor="w", padx=20, pady=(0, 6))
            elif event.headline:
                ctk.CTkLabel(
                    scroll, text=event.headline,
                    font=f.small, text_color=INK,
                    wraplength=575, justify="left",
                ).pack(anchor="w", padx=20, pady=(0, 6))

            if event.statement_remedy and event.statement_tick is not None:
                statement = self.cfg.remedies.get(event.statement_remedy)
                window = statement.raw.get("trust_effect", {}).get("duration_hours", 48) if statement else 48
                left = max(0, window - (current_tick - event.statement_tick))
                ctk.CTkLabel(
                    scroll,
                    text=f"Statement issued: {statement.label if statement else event.statement_remedy}"
                         f"  ·  {left}h to follow it with action",
                    font=f.small_bold, text_color=STATUS_YELLOW,
                ).pack(anchor="w", padx=20, pady=(0, 8))

            if event.phase == EventPhase.RESPONDING:
                remedy_cfg = self.cfg.remedies.get(event.remedy_applied or "")
                label_text = remedy_cfg.label if remedy_cfg else (event.remedy_applied or "")
                total_h = event.effective_downtime_hours or 0.0
                if total_h > 0 and event.remedy_applied_tick is not None:
                    elapsed_h = current_tick - event.remedy_applied_tick
                    remaining_h = max(0.0, total_h - elapsed_h)
                    time_text = f"  ·  {remaining_h:.0f}h remaining of {total_h:.0f}h"
                else:
                    time_text = ""
                ctk.CTkLabel(
                    scroll,
                    text=f"Response in progress: {label_text}{time_text}",
                    font=f.small_bold, text_color=STATUS_RESPONDING,
                ).pack(anchor="w", padx=20, pady=(0, 8))
            else:
                # Filtered by domain: the threatmodel restricts recovery pathways per domain.
                _section_heading(scroll, f, "Available responses")
                for remedy in get_available_remedies(self.cfg, event):
                    remedy_id = remedy.id
                    card = ctk.CTkFrame(scroll, fg_color=PAPER_DARK, corner_radius=6)
                    card.pack(fill="x", padx=20, pady=4)

                    label, desc = _remedy_text(
                        building.type_id, remedy_id, remedy.label, remedy.description,
                    )

                    if remedy.downtime_hours == 0:
                        downtime_text = "immediate"
                    else:
                        downtime_text = f"{remedy.downtime_hours}h repair"

                    ctk.CTkButton(
                        card,
                        text=f"{label}   ·   {remedy.base_cost} AM$   ·   {downtime_text}",
                        command=lambda eid=event.id, rid=remedy_id: self._select_remedy(eid, rid),
                        font=f.body_bold,
                        fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
                        anchor="w",
                    ).pack(fill="x", padx=10, pady=(8, 4))

                    ctk.CTkLabel(
                        card, text=desc,
                        font=f.small, text_color=INK_MUTED,
                        wraplength=555, justify="left",
                    ).pack(anchor="w", padx=14, pady=(0, 8))

        else:
            _section_heading(scroll, f, "Current status")
            if building.is_failed and not event:
                msg = "Building has failed. Incident not yet detected."
                colour = STATUS_RED
            elif building.is_degraded:
                msg = "Building is degraded. Monitoring recommended."
                colour = STATUS_YELLOW
            else:
                msg = "No active incident. Building is operational."
                colour = STATUS_GREEN
            ctk.CTkLabel(
                scroll, text=msg,
                font=f.small, text_color=colour,
            ).pack(anchor="w", padx=20, pady=(0, 12))

        ctk.CTkButton(
            win, text="Close",
            command=self.hide,
            width=140, font=f.body_bold,
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=10)

    def hide(self) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

    def _select_remedy(self, event_id: str, remedy_id: str) -> None:
        self.hide()
        if self.on_remedy_selected:
            self.on_remedy_selected(event_id, remedy_id)


class EventPopup:
    """Incident report shown when a failure is detected. The app pauses the clock around it."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._window: ctk.CTkToplevel | None = None
        self.on_close: Callable[[], None] | None = None

    def is_visible(self) -> bool:
        return self._window is not None

    def show(self, event: GameEvent, city: City, more_remaining: int = 0) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

        f = fonts()

        building = city.get_building(event.target_building_id)
        district = city.districts.get(event.target_district_id)
        district_name = district.name if district else event.target_district_id

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 620, 580
        px = (sw - w) // 2
        py = (sh - h) // 2

        win = ctk.CTkToplevel(self.root)
        win.title("New Incident")
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        self._window = win
        win.protocol("WM_DELETE_WINDOW", self._close)

        header = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        header.pack(fill="x")

        header_title = "NEW INCIDENT" if more_remaining == 0 else f"NEW INCIDENT  (+{more_remaining} more)"
        ctk.CTkLabel(
            header, text=header_title,
            font=(f.family, 18, "bold"), text_color=STATUS_RED,
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            header, text=district_name,
            font=f.body, text_color=INK_MUTED,
        ).pack(side="right", padx=20, pady=12)

        if building:
            type_label = building.type_id.replace("_", " ").title()
            ctk.CTkLabel(
                win,
                text=f"{building.name}  ·  {district_name}  ·  {type_label}",
                font=f.small, text_color=INK_MUTED,
            ).pack(anchor="w", padx=20, pady=(8, 0))

        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(
            scroll, text=event.name,
            font=f.body_bold, text_color=STATUS_RED,
        ).pack(anchor="w", padx=20, pady=(14, 6))

        story_text = event.story or event.headline or ""
        if story_text:
            ctk.CTkLabel(
                scroll, text=story_text,
                font=f.body, text_color=INK,
                wraplength=555, justify="left",
            ).pack(anchor="w", padx=20, pady=(0, 8))

        if building:
            _section_heading(scroll, f, "Affected building")
            status_colour = _status_colour(building.status)
            _bullet(scroll, f, f"Status: {building.status.value.title()}", status_colour)
            _bullet(
                scroll, f,
                f"Sensitivity: {building.sensitivity.replace('_', ' ')}",
                INK_MUTED,
            )
            desc = _TYPE_DESCRIPTIONS.get(building.type_id)
            if desc:
                ctk.CTkLabel(
                    scroll, text=desc,
                    font=f.small, text_color=INK,
                    wraplength=555, justify="left",
                ).pack(anchor="w", padx=20, pady=(6, 4))

        # Cascade scope "neighbours" only reaches the same district, so only list those.
        if building:
            cascade_district = (
                event.target_district_id
                if event.cascade_scope == "neighbours"
                else None
            )
            relying = _buildings_relying_on(building, city, district_id=cascade_district)
            if relying:
                scope_label = (
                    f"Buildings at risk  ·  {district_name} only"
                    if cascade_district
                    else "Buildings at risk"
                )
                _section_heading(scroll, f, scope_label)
                for b, level in relying[:6]:
                    level_tag = {
                        "critical": "critically",
                        "operational": "operationally",
                    }.get(level, "strategically")
                    dot_colour = _status_colour(b.status)
                    _bullet(
                        scroll, f,
                        f"{b.name}: depends {level_tag}  ·  {b.status.value}",
                        dot_colour if b.status != BuildingStatus.OPERATIONAL else INK_MUTED,
                    )
                if len(relying) > 6:
                    ctk.CTkLabel(
                        scroll,
                        text=f"  +{len(relying) - 6} more buildings depend on this",
                        font=f.small, text_color=INK_MUTED,
                    ).pack(anchor="w", padx=36, pady=2)
                if cascade_district:
                    vendor_mono = city.stressors.get("vendor_monoculture", 0.0)
                    if vendor_mono >= 0.5:
                        ctk.CTkLabel(
                            scroll,
                            text=f"⚠  Vendor monoculture is high ({vendor_mono:.0%}): "
                                 "the cascade may spread city-wide.",
                            font=f.small, text_color=STATUS_YELLOW,
                            wraplength=555, justify="left",
                        ).pack(anchor="w", padx=20, pady=(4, 0))

        ctk.CTkLabel(
            scroll,
            text="The city is paused. Click the highlighted building on the map to choose a response, "
                 "or resume from the controls when ready.",
            font=f.small, text_color=INK_MUTED,
            wraplength=555, justify="left",
        ).pack(anchor="w", padx=20, pady=(18, 10))

        btn_text = "Close" if more_remaining == 0 else f"Next incident  ({more_remaining} remaining)"
        ctk.CTkButton(
            win, text=btn_text,
            command=self._close,
            width=200, font=f.body_bold,
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=10)

    def hide(self) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

    def _close(self) -> None:
        self.hide()
        if self.on_close:
            self.on_close()


class ArticlePopup:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self._window: ctk.CTkToplevel | None = None

    def show(self, timestamp: str, headline: str, article: str) -> None:
        if self._window:
            self._window.destroy()
            self._window = None

        f = fonts()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 580, 460
        px = (sw - w) // 2
        py = (sh - h) // 2

        win = ctk.CTkToplevel(self.root)
        win.title("The Ankh-Morpork Times")
        win.geometry(f"{w}x{h}+{px}+{py}")
        win.configure(fg_color=PAPER)
        win.attributes("-topmost", True)
        self._window = win
        win.protocol("WM_DELETE_WINDOW", self.hide)

        masthead = ctk.CTkFrame(win, fg_color=PAPER_DARK)
        masthead.pack(fill="x")

        ctk.CTkLabel(
            masthead, text="THE ANKH-MORPORK TIMES",
            font=(f.family, 16, "bold"), text_color=INK,
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            masthead, text=timestamp,
            font=f.small, text_color=INK_MUTED,
        ).pack(side="right", padx=20, pady=10)

        ctk.CTkLabel(
            win, text=headline,
            font=(f.family, 15, "bold"), text_color=INK,
            wraplength=520, justify="left",
        ).pack(anchor="w", padx=24, pady=(16, 8))

        ctk.CTkFrame(win, fg_color=ACCENT_BROWN, height=2).pack(fill="x", padx=24, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(win, fg_color=PAPER, label_text="")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(
            scroll, text=article,
            font=f.body, text_color=INK,
            wraplength=520, justify="left",
        ).pack(anchor="w", padx=24, pady=(8, 16))

        ctk.CTkButton(
            win, text="Close",
            command=self.hide,
            width=140, font=f.body_bold,
            fg_color=ACCENT_BROWN, hover_color="#a07a1a", text_color=PAPER,
        ).pack(pady=10)

    def hide(self) -> None:
        if self._window:
            self._window.destroy()
            self._window = None
