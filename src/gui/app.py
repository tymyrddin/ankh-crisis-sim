from __future__ import annotations

import customtkinter as ctk

from src.engine.simulation import Simulation, TickResult
from src.gui.dashboard import Dashboard
from src.gui.info_popups import InfoPopup
from src.gui.intro import IntroScreen
from src.gui.map_canvas import MapCanvas
from src.gui.news_ticker import NewsTicker
from src.gui.popups import ArticlePopup, EventPopup, HoverPopup, RemedyMenu
from src.gui.postgame import PostgameScreen
from src.gui.settings_popup import SettingsPopup
from src.gui.theme import PAPER, PAPER_DARK, fonts, load_fonts
from src.gui.time_controls import TimeControls


class App(ctk.CTk):
    def __init__(self, config_dir: str = "config", map_image: str = "static/images/ankh-morpork.png"):
        super().__init__()
        self.title("Ankh-Morpork: Lord Vetinari's Dilemma")
        self.geometry("1400x900")

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        font_family = load_fonts()
        self._fonts = fonts(font_family)
        self.configure(fg_color=PAPER)

        self.sim = Simulation(config_dir)

        self._tick_interval_ms = int(self.sim.cfg.speed.seconds_per_game_hour * 1000)

        self._game_over = False
        self._tick_job: str | None = None
        self._event_queue: list = []

        # map and dashboard on top, ticker and clock below
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        map_frame = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        map_frame.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="nsew")

        self.map_canvas = MapCanvas(map_frame, map_image)
        self.map_canvas.draw_buildings(self.sim.city)

        dashboard_frame = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        dashboard_frame.grid(row=0, column=1, padx=(5, 10), pady=(10, 5), sticky="nsew")

        self.dashboard = Dashboard(dashboard_frame)
        self.dashboard.build_metrics(self.sim.city)
        self.dashboard.build_status(self.sim.city)
        self.dashboard.build_districts(self.sim.city)

        bottom_left = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        bottom_left.grid(row=1, column=0, padx=(10, 5), pady=(5, 10), sticky="ew")

        self.news_ticker = NewsTicker(bottom_left)

        bottom_right = ctk.CTkFrame(self, fg_color=PAPER_DARK, border_width=1, border_color=PAPER_DARK)
        bottom_right.grid(row=1, column=1, padx=(5, 10), pady=(5, 10), sticky="ew")

        self.time_controls = TimeControls(bottom_right, self.sim.cfg.speed)
        self.time_controls.on_pause = self._on_pause
        self.time_controls.on_play = self._on_play
        self.time_controls.on_speed = self._on_speed
        self.time_controls.on_exit = self._on_exit

        self.info_popup = InfoPopup(self, self.sim.cfg)
        self.info_popup.on_emergency_borrow = self._on_emergency_borrow
        self.dashboard.attach_popup(self.info_popup, self.sim.city)
        self.hover_popup = HoverPopup(self)
        self.remedy_menu = RemedyMenu(self, self.sim.cfg)
        self.remedy_menu.on_remedy_selected = self._on_remedy_selected
        self.postgame_screen = PostgameScreen(self, self.sim.cfg)
        self.settings_popup = SettingsPopup(self)
        self.dashboard.on_settings_click = lambda: self.settings_popup.show(self.sim.cfg.settings)
        self.event_popup = EventPopup(self)
        self.event_popup.on_close = self._on_event_popup_close
        self.article_popup = ArticlePopup(self)
        self.news_ticker.on_article_click = self.article_popup.show

        self.map_canvas.on_building_hover = self._on_building_hover
        self.map_canvas.on_building_leave = self._on_building_leave
        self.map_canvas.on_building_click = self._on_building_click

        self.time_controls.update(self.sim.clock)
        self.news_ticker.add_headline(
            self.sim.clock.time_string,
            "The Patrician's term begins. The city watches.",
        )

        # the game stays paused until the briefing is dismissed
        self.after(200, self._show_intro)

    def _show_intro(self) -> None:
        intro = IntroScreen(self)
        intro.on_begin = lambda: None  # the player presses play themselves
        intro.show()

    def _schedule_tick(self) -> None:
        if self._game_over:
            return
        interval = max(10, int(self._tick_interval_ms / self.sim.clock.speed_multiplier))
        self._tick_job = self.after(interval, self._do_tick)

    def _do_tick(self) -> None:
        if self._game_over or not self.sim.clock.is_running:
            return

        result: TickResult = self.sim.tick()

        self._process_tick_result(result)

        self._schedule_tick()

    def _process_tick_result(self, result: TickResult) -> None:
        ts = self.sim.clock.time_string
        for event in result.detected_events + result.cascade_events:
            if event.headline:
                self.news_ticker.add_headline(ts, event.headline, article=event.story)

        for msg in result.completed_remedies:
            self.news_ticker.add_headline(ts, msg)

        for event in result.detected_events + result.cascade_events + result.completed_remedy_events:
            building = self.sim.city.get_building(event.target_building_id)
            if building:
                responding = event.phase.value == "responding"
                self.map_canvas.update_building(
                    building.id, building.status, building.hidden_failure, responding,
                )

        self.dashboard.update(self.sim.city)
        self.time_controls.update(self.sim.clock)

        new_incidents = result.detected_events + result.cascade_events
        if new_incidents and not self._game_over:
            self._event_queue.extend(new_incidents)
            self.sim.pause()
            self.time_controls.update(self.sim.clock)
            if not self.event_popup.is_visible():
                self._show_next_event()

        if result.end_result and result.end_result.triggered:
            self._game_over = True
            self.sim.pause()
            self.postgame_screen.show(self.sim.city, result.end_result)

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
        # restart the loop at the new speed
        if self.sim.clock.is_running:
            if self._tick_job:
                self.after_cancel(self._tick_job)
            self._schedule_tick()

    def _on_exit(self) -> None:
        self.sim.pause()
        self.destroy()

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
