"""News ticker — scrolling headline feed at the bottom of the screen."""

from __future__ import annotations

import customtkinter as ctk


class NewsTicker:
    """A scrolling text area showing headlines as they arrive."""

    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent

        header = ctk.CTkLabel(parent, text="NEWS", font=("Arial", 12, "bold"))
        header.pack(anchor="w", padx=10, pady=(5, 2))

        self._textbox = ctk.CTkTextbox(parent, height=100, state="disabled", wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self._headlines: list[tuple[str, str]] = []  # (timestamp, text)

    def add_headline(self, timestamp: str, text: str) -> None:
        """Add a headline to the top of the ticker."""
        self._headlines.insert(0, (timestamp, text))

        self._textbox.configure(state="normal")
        self._textbox.insert("1.0", f"[{timestamp}] {text}\n")
        self._textbox.configure(state="disabled")
        self._textbox.see("1.0")

    def add_headlines(self, timestamp: str, headlines: list[str]) -> None:
        """Add multiple headlines at once."""
        for headline in headlines:
            self.add_headline(timestamp, headline)

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
        self._headlines.clear()