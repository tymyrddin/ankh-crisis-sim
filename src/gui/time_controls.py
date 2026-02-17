"""Time controls — pause, play, speed buttons and game clock display."""

from __future__ import annotations

import customtkinter as ctk

from src.engine.clock import ClockState, GameClock


class TimeControls:
    """Bottom bar with pause/play/speed controls and time display."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self.on_pause: callable | None = None
        self.on_play: callable | None = None
        self.on_speed: callable | None = None  # (multiplier: float) -> None

        # Controls row
        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=5)

        self._pause_btn = ctk.CTkButton(
            controls, text="Pause", width=70,
            command=self._on_pause,
        )
        self._pause_btn.pack(side="left", padx=3)

        self._play_btn = ctk.CTkButton(
            controls, text="Play", width=70,
            command=self._on_play,
        )
        self._play_btn.pack(side="left", padx=3)

        self._fast_btn = ctk.CTkButton(
            controls, text="Fast", width=70,
            command=lambda: self._on_speed(10.0),
        )
        self._fast_btn.pack(side="left", padx=3)

        self._faster_btn = ctk.CTkButton(
            controls, text="Faster", width=70,
            command=lambda: self._on_speed(50.0),
        )
        self._faster_btn.pack(side="left", padx=3)

        # Time display
        self._time_label = ctk.CTkLabel(
            controls, text="Day 1 - 08:00",
            font=("Arial", 14, "bold"),
        )
        self._time_label.pack(side="right", padx=15)

        # Speed display
        self._speed_label = ctk.CTkLabel(
            controls, text="1.0x",
            font=("Arial", 11), text_color="gray",
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