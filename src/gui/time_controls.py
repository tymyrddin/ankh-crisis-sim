"""Time controls — pause, play, speed buttons and game clock display."""

from __future__ import annotations

import customtkinter as ctk

from src.engine.clock import ClockState, GameClock
from src.gui.theme import ACCENT_BROWN, INK, INK_MUTED, PAPER, PAPER_DARK, fonts


class TimeControls:
    """Bottom bar with pause/play/speed controls and time display."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self.on_pause: callable | None = None
        self.on_play: callable | None = None
        self.on_speed: callable | None = None  # (multiplier: float) -> None
        f = fonts()

        # Controls row
        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=5)

        btn_kwargs = dict(
            width=70, font=f.small_bold,
            fg_color=ACCENT_BROWN, hover_color="#a07a1a",
            text_color=PAPER,
        )

        self._pause_btn = ctk.CTkButton(
            controls, text="Pause",
            command=self._on_pause, **btn_kwargs,
        )
        self._pause_btn.pack(side="left", padx=3)

        self._play_btn = ctk.CTkButton(
            controls, text="Play",
            command=self._on_play, **btn_kwargs,
        )
        self._play_btn.pack(side="left", padx=3)

        self._fast_btn = ctk.CTkButton(
            controls, text="Fast",
            command=lambda: self._on_speed(10.0), **btn_kwargs,
        )
        self._fast_btn.pack(side="left", padx=3)

        self._faster_btn = ctk.CTkButton(
            controls, text="Faster",
            command=lambda: self._on_speed(50.0), **btn_kwargs,
        )
        self._faster_btn.pack(side="left", padx=3)

        # Time display
        self._time_label = ctk.CTkLabel(
            controls, text="Day 1 - 08:00",
            font=f.clock, text_color=INK,
        )
        self._time_label.pack(side="right", padx=15)

        # Speed display
        self._speed_label = ctk.CTkLabel(
            controls, text="1.0x",
            font=f.small, text_color=INK_MUTED,
        )
        self._speed_label.pack(side="right", padx=5)

    def update(self, clock: GameClock) -> None:
        """Refresh the time display."""
        self._time_label.configure(text=clock.time_string)
        self._speed_label.configure(text=f"{clock.speed_multiplier:.1f}x")

        if clock.state == ClockState.PAUSED:
            self._pause_btn.configure(state="disabled")
            self._play_btn.configure(state="normal")
        else:
            self._pause_btn.configure(state="normal")
            self._play_btn.configure(state="disabled")

    def _on_pause(self) -> None:
        if self.on_pause:
            self.on_pause()

    def _on_play(self) -> None:
        if self.on_play:
            self.on_play()

    def _on_speed(self, multiplier: float) -> None:
        if self.on_speed:
            self.on_speed(multiplier)