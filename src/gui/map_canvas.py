"""Map canvas — base map image with district tint overlays and building lamps."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from src.gui.theme import STATUS_GREEN, STATUS_RED, STATUS_RESPONDING, STATUS_YELLOW, PAPER, INK
from src.models.building import BuildingStatus
from src.models.city import City

STATUS_COLOURS = {
    BuildingStatus.OPERATIONAL: STATUS_GREEN,
    BuildingStatus.DEGRADED: STATUS_YELLOW,
    BuildingStatus.FAILED: STATUS_RED,
}

# District tint colours (muted, semi-transparent)
DISTRICT_TINTS = {
    "nap_hill": "#FFD700",
    "the_shades": "#4A4A4A",
    "cockbill_street": "#5A3A3A",
    "isle_of_gods": "#6B8E9B",
    "university_precinct": "#7B68AE",
    "merchant_quarter": "#C0853C",
    "small_gods": "#50785A",
    "river_ankh": "#2A4A6A",
}


class MapCanvas:
    """Manages the map image, district overlays, and building indicators."""

    def __init__(self, parent: tk.Frame, map_image_path: str | Path, width: int = 900, height: int = 700):
        self.parent = parent
        self.width = width
        self.height = height

        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bg=PAPER,
        )
        self.canvas.pack(fill="both", expand=True)

        # Load and display base map
        self._image_refs: list = []  # prevent GC
        self._load_base_map(map_image_path)

        # Track building lamp canvas IDs
        self._lamp_ids: dict[str, int] = {}
        self._glow_ids: dict[str, int] = {}

        # Hover/click callback hooks
        self.on_building_hover: callable | None = None
        self.on_building_leave: callable | None = None
        self.on_building_click: callable | None = None

    def _load_base_map(self, path: str | Path) -> None:
        path = Path(path)
        if path.exists():
            img = Image.open(path).resize((self.width, self.height), Image.LANCZOS)
        else:
            # Generate a placeholder parchment map
            img = Image.new("RGB", (self.width, self.height), PAPER)
            draw = ImageDraw.Draw(img)
            # Draw a simple river
            draw.line([(0, 350), (self.width, 350)], fill="#8b7355", width=20)
            draw.text((self.width // 2 - 80, self.height // 2), "ANKH-MORPORK", fill=INK)

        self._base_map_tk = ImageTk.PhotoImage(img)
        self._image_refs.append(self._base_map_tk)
        self.canvas.create_image(0, 0, image=self._base_map_tk, anchor="nw", tags="map")

    def draw_buildings(self, city: City) -> None:
        """Draw all building lamps on the map."""
        # Clear existing lamps
        self.canvas.delete("building_glow")
        self.canvas.delete("building_lamp")
        self._lamp_ids.clear()
        self._glow_ids.clear()

        for district in city.districts.values():
            for building in district.buildings.values():
                x, y = building.position
                colour = STATUS_COLOURS.get(building.status, "#666666")

                if building.hidden_failure:
                    colour = STATUS_COLOURS[BuildingStatus.OPERATIONAL]  # looks green while hidden

                # Outer glow
                glow_id = self.canvas.create_oval(
                    x - 12, y - 12, x + 12, y + 12,
                    outline=INK, width=2,
                    tags=("building_glow", f"b_{building.id}"),
                )
                self._glow_ids[building.id] = glow_id

                # Inner lamp
                lamp_id = self.canvas.create_oval(
                    x - 8, y - 8, x + 8, y + 8,
                    fill=colour, outline=INK, width=1,
                    tags=("building_lamp", f"b_{building.id}"),
                )
                self._lamp_ids[building.id] = lamp_id

        # Bind events
        self.canvas.tag_bind("building_lamp", "<Enter>", self._on_hover)
        self.canvas.tag_bind("building_lamp", "<Leave>", self._on_leave)
        self.canvas.tag_bind("building_lamp", "<Button-1>", self._on_click)

    def update_building(
        self, building_id: str, status: BuildingStatus,
        hidden: bool = False, responding: bool = False,
    ) -> None:
        """Update a single building's lamp colour."""
        if building_id not in self._lamp_ids:
            return
        colour = STATUS_COLOURS.get(status, "#666666")
        if hidden:
            colour = STATUS_COLOURS[BuildingStatus.OPERATIONAL]
        elif responding:
            colour = STATUS_RESPONDING
        self.canvas.itemconfig(self._lamp_ids[building_id], fill=colour)

    def _get_building_id_from_tags(self, event: tk.Event) -> str | None:
        tags = self.canvas.gettags("current")
        for tag in tags:
            if tag.startswith("b_"):
                return tag[2:]
        return None

    def _on_hover(self, event: tk.Event) -> None:
        bid = self._get_building_id_from_tags(event)
        if bid and self.on_building_hover:
            self.on_building_hover(bid, event.x_root, event.y_root)

    def _on_leave(self, event: tk.Event) -> None:
        if self.on_building_leave:
            self.on_building_leave()

    def _on_click(self, event: tk.Event) -> None:
        bid = self._get_building_id_from_tags(event)
        if bid and self.on_building_click:
            self.on_building_click(bid, event.x_root, event.y_root)