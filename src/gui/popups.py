"""Popups — hover info and click menus for buildings and remedies."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from src.config.loader import GameConfig
from src.models.building import Building
from src.models.city import City
from src.models.event import GameEvent


class HoverPopup:
    """Tooltip that appears when hovering over a building lamp."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self._popup: tk.Toplevel | None = None

    def show(self, building: Building, district_name: str, x: int, y: int) -> None:
        self.hide()
        self._popup = tk.Toplevel(self.root)
        self._popup.wm_overrideredirect(True)
        self._popup.geometry(f"+{x + 15}+{y + 15}")
        self._popup.attributes("-topmost", True)

        frame = ctk.CTkFrame(self._popup)
        frame.pack()

        status_colours = {
            "operational": "#00cc00",
            "degraded": "#ffcc00",
            "failed": "#ff3333",
        }
        colour = status_colours.get(building.status.value, "#aaa")

        ctk.CTkLabel(
            frame, text=building.name,
            font=("Arial", 13, "bold"),
        ).pack(padx=12, pady=(8, 2))

        ctk.CTkLabel(
            frame, text=f"District: {district_name}",
            font=("Arial", 11), text_color="gray",
        ).pack(padx=12)

        ctk.CTkLabel(
            frame,
            text=f"Status: {building.status.value.title()}",
            font=("Arial", 11),
            text_color=colour,
        ).pack(padx=12, pady=(2, 8))

    def hide(self) -> None:
        if self._popup:
            self._popup.destroy()
            self._popup = None


class RemedyMenu:
    """Click menu showing available actions for a building."""

    def __init__(self, root: ctk.CTk, cfg: GameConfig):
        self.root = root
        self.cfg = cfg
        self._popup: tk.Toplevel | None = None
        self.on_remedy_selected: callable | None = None  # (event_id, remedy_id) -> None

    def show(
        self,
        building: Building,
        event: GameEvent | None,
        x: int,
        y: int,
    ) -> None:
        self.hide()

        self._popup = tk.Toplevel(self.root)
        self._popup.wm_overrideredirect(True)
        self._popup.geometry(f"+{x}+{y}")
        self._popup.attributes("-topmost", True)

        frame = ctk.CTkFrame(self._popup)
        frame.pack()

        ctk.CTkLabel(
            frame, text=building.name,
            font=("Arial", 14, "bold"),
        ).pack(padx=20, pady=(10, 5))

        if event and event.is_visible:
            ctk.CTkLabel(
                frame,
                text=f"Event: {event.name}",
                font=("Arial", 11), text_color="#ff9800",
            ).pack(padx=20, pady=2)

            # Remedy buttons
            for remedy_id, remedy in self.cfg.remedies.items():
                btn = ctk.CTkButton(
                    frame,
                    text=f"{remedy.label} ({remedy.base_cost} AM$)",
                    command=lambda eid=event.id, rid=remedy_id: self._select_remedy(eid, rid),
                    width=220,
                )
                btn.pack(padx=15, pady=3)
        else:
            ctk.CTkLabel(
                frame,
                text="No active event" if not building.is_failed else "Event not yet detected",
                font=("Arial", 11), text_color="gray",
            ).pack(padx=20, pady=5)

        ctk.CTkButton(
            frame, text="Close",
            command=self.hide,
            fg_color="gray", width=220,
        ).pack(padx=15, pady=(5, 10))

    def hide(self) -> None:
        if self._popup:
            self._popup.destroy()
            self._popup = None

    def _select_remedy(self, event_id: str, remedy_id: str) -> None:
        self.hide()
        if self.on_remedy_selected:
            self.on_remedy_selected(event_id, remedy_id)