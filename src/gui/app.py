"""Main application window:assembles all GUI components and connects to the simulation."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from src.engine.simulation import Simulation, TickResult
from src.gui.dashboard import Dashboard
from src.gui.map_canvas import MapCanvas
from src.gui.news_ticker import NewsTicker
from src.gui.info_popups import InfoPopup
from src.gui.popups import ArticlePopup, HoverPopup, RemedyMenu, EventPopup
from src.gui.intro import IntroScreen
from src.gui.settings_popup import SettingsPopup
from src.gui.postgame import PostgameScreen
from src.gui.theme import PAPER, PAPER_DARK, load_fonts, fonts
from src.gui.time_controls import TimeControls
from src.models.building import Building


class App(ctk.CTk):
    """The main Ankh-Morpork Crisis Simulator window."""

    def __init__(self, config_dir: str = "config", map_image: str = "static/images/ankh-morpork.png"):
        super().__init__()
        self.title("Ankh-Morpork: Lord Vetinari's Dilemma")
        self.geometry("1400x900")

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Load steampunk fonts and paper palette
        font_family = load_fonts()
        self._fonts = fonts(font_family)
        self.configure(fg_color=PAPER)

        # Simulation engine
        self.sim = Simulation(config_dir)
        self.sim.initialise()

        # Tick interval derived from config: seconds_per_game_hour → milliseconds
        self._tick_interval_ms = int(self.sim.cfg.speed.seconds_per_game_hour * 1000)

        self._game_over = False
        self._tick_job: str | None = None
        self._event_queue: list = []

        # --- Layout ---
        # Top row: map (left) + dashboard (right)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Map frame
        map_frame = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        map_frame.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="nsew")

        self.map_canvas = MapCanvas(map_frame, map_image)
        self.map_canvas.draw_buildings(self.sim.city)

        # Dashboard frame
        dashboard_frame = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        dashboard_frame.grid(row=0, column=1, padx=(5, 10), pady=(10, 5), sticky="nsew")

        self.dashboard = Dashboard(dashboard_frame)
        self.dashboard.build_metrics(self.sim.city)
        self.dashboard.build_status(self.sim.city)
        self.dashboard.build_districts(self.sim.city)

        # Bottom row: news ticker (left) + time controls (right)
        bottom_left = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        bottom_left.grid(row=1, column=0, padx=(10, 5), pady=(5, 10), sticky="ew")

        self.news_ticker = NewsTicker(bottom_left)

        bottom_right = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        bottom_right.grid(row=1, column=1, padx=(5, 10), pady=(5, 10), sticky="ew")

        self.time_controls = TimeControls(bottom_right)
        self.time_controls.on_pause = self._on_pause
        self.time_controls.on_play = self._on_play
        self.time_controls.on_speed = self._on_speed
        self.time_controls.on_exit = self._on_exit

        # Popups
        self.info_popup = InfoPopup(self)
        self.info_popup.on_emergency_borrow = self._on_emergency_borrow
        self.dashboard.attach_popup(self.info_popup, self.sim.city)
        self.hover_popup = HoverPopup(self)
        self.remedy_menu = RemedyMenu(self, self.sim.cfg)
        self.remedy_menu.on_remedy_selected = self._on_remedy_selected
        self.postgame_screen = PostgameScreen(self)
        self.settings_popup = SettingsPopup(self)
        self.dashboard.on_settings_click = lambda: self.settings_popup.show(self.sim.cfg.settings)
        self.event_popup = EventPopup(self)
        self.event_popup.on_close = self._on_event_popup_close
        self.article_popup = ArticlePopup(self)
        self.news_ticker.on_article_click = self.article_popup.show

        # Map interaction hooks
        self.map_canvas.on_building_hover = self._on_building_hover
        self.map_canvas.on_building_leave = self._on_building_leave
        self.map_canvas.on_building_click = self._on_building_click

        # Initial display
        self.time_controls.update(self.sim.clock)
        self.news_ticker.add_headline(
            self.sim.clock.time_string,
            "The Patrician's term begins. The city watches.",
        )

        # Briefing screen:shown immediately; game stays paused until dismissed
        self.after(200, self._show_intro)

    def _show_intro(self) -> None:
        intro = IntroScreen(self)
        intro.on_begin = lambda: None  # game stays paused; player presses play themselves
        intro.show()

    # --- Tick loop ---

    def _schedule_tick(self) -> None:
        if self._game_over:
            return
        interval = max(10, int(self._tick_interval_ms / self.sim.clock.speed_multiplier))
        self._tick_job = self.after(interval, self._do_tick)

    def _do_tick(self) -> None:
        if self._game_over or not self.sim.clock.is_running:
            return

        result: TickResult = self.sim.tick()

        # Update GUI
        self._process_tick_result(result)

        # Schedule next tick
        self._schedule_tick()

    def _process_tick_result(self, result: TickResult) -> None:
        """Update all GUI components from a tick result."""
        # Event headlines:clickable if the event has a story
        ts = self.sim.clock.time_string
        for event in result.detected_events + result.cascade_events:
            if event.headline:
                self.news_ticker.add_headline(ts, event.headline, article=event.story)

        # Completed remedies:plain, no article
        for msg in result.completed_remedies:
            self.news_ticker.add_headline(ts, msg)

        # Update building lamps for any changed buildings
        for event in result.detected_events + result.cascade_events + result.completed_remedy_events:
            building = self.sim.city.get_building(event.target_building_id)
            if building:
                responding = event.phase.value == "responding"
                self.map_canvas.update_building(
                    building.id, building.status, building.hidden_failure, responding,
                )

        # Update dashboard every tick (cheap enough)
        self.dashboard.update(self.sim.city)
        self.time_controls.update(self.sim.clock)

        # New incidents:pause and queue popups
        new_incidents = result.detected_events + result.cascade_events
        if new_incidents and not self._game_over:
            self._event_queue.extend(new_incidents)
            self.sim.pause()
            self.time_controls.update(self.sim.clock)
            if not self.event_popup.is_visible():
                self._show_next_event()

        # End condition
        if result.end_result and result.end_result.triggered:
            self._game_over = True
            self.sim.pause()
            self.postgame_screen.show(self.sim.city, result.end_result)

    # --- Player controls ---

    def _on_pause(self) -> None:
        self.sim.pause()
        if self._tick_job:
            self.after_cancel(self._tick_job)
            self._tick_job = None
        self.time_controls.update(self.sim.clock)

    def _show_next_event(self) -> None:
        if self._event_queue:
            event = self._event_queue.pop(0)
            self.event_popup.show(event, self.sim.city, more_remaining=len(self._event_queue))

    def _on_event_popup_close(self) -> None:
        self._show_next_event()

    def _on_play(self) -> None:
        self.sim.resume()
        self.time_controls.update(self.sim.clock)
        self._schedule_tick()

    def _on_speed(self, multiplier: float) -> None:
        self.sim.set_speed(multiplier)
        self.time_controls.update(self.sim.clock)
        # If already running, restart the tick loop at new speed
        if self.sim.clock.is_running:
            if self._tick_job:
                self.after_cancel(self._tick_job)
            self._schedule_tick()

    def _on_exit(self) -> None:
        self.sim.pause()
        self.destroy()

    # --- Building interaction ---

    def _on_building_hover(self, building_id: str, x: int, y: int) -> None:
        building = self.sim.city.get_building(building_id)
        if not building:
            return
        district = self.sim.city.get_district_for_building(building_id)
        district_name = district.name if district else "Unknown"
        self.hover_popup.show(building, district_name, x, y)

    def _on_building_leave(self) -> None:
        self.hover_popup.hide()

    def _on_building_click(self, building_id: str, x: int, y: int) -> None:
        self.hover_popup.hide()
        building = self.sim.city.get_building(building_id)
        if not building:
            return

        # Find active event for this building
        event = next(
            (e for e in self.sim.city.active_events
             if e.target_building_id == building_id and e.is_visible),
            None,
        )
        self.remedy_menu.show(building, event, self.sim.city, x, y, current_tick=self.sim.clock.tick)

    def _on_emergency_borrow(self, lender_id: str) -> None:
        result = self.sim.emergency_borrow(lender_id)
        self.news_ticker.add_headline(self.sim.clock.time_string, result.message)
        self.dashboard.update(self.sim.city)

    def _on_remedy_selected(self, event_id: str, remedy_id: str) -> None:
        result = self.sim.apply_remedy(event_id, remedy_id)
        if result.success:
            self.news_ticker.add_headline(self.sim.clock.time_string, result.headline or result.message)
            # Update the building lamp
            event = next((e for e in self.sim.city.events if e.id == event_id), None)
            if event:
                building = self.sim.city.get_building(event.target_building_id)
                if building:
                    responding = event.phase.value == "responding"
                    self.map_canvas.update_building(
                        building.id, building.status, building.hidden_failure, responding,
                    )
            self.dashboard.update(self.sim.city)
        else:
            self.news_ticker.add_headline(self.sim.clock.time_string, f"Failed: {result.message}")