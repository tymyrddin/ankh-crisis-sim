from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.gui.theme import ACCENT_BROWN, INK, PAPER, fonts


class NewsTicker:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        f = fonts()

        ctk.CTkLabel(
            parent, text="NEWS", font=f.heading, text_color=ACCENT_BROWN,
        ).pack(anchor="w", padx=10, pady=(5, 2))

        self._textbox = ctk.CTkTextbox(
            parent, height=100, state="disabled", wrap="word",
            font=f.small, text_color=INK, fg_color=PAPER,
        )
        self._textbox.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self._headlines: list[tuple[str, str, str]] = []  # (timestamp, text, article)
        self._tag_counter = 0
        self._tag_articles: dict[str, tuple[str, str, str]] = {}
        self.on_article_click: Callable[[str, str, str], None] | None = None

    def add_headline(self, timestamp: str, text: str, article: str = "") -> None:
        self._headlines.insert(0, (timestamp, text, article))

        content = f"[{timestamp}] {text}\n"

        self._textbox.configure(state="normal")
        self._textbox.insert("1.0", content)
        self._textbox.configure(state="disabled")
        self._textbox.see("1.0")

        if article:
            tag = f"h{self._tag_counter}"
            self._tag_counter += 1
            self._tag_articles[tag] = (timestamp, text, article)

            # CTkTextbox does not expose tags
            tk_text = self._textbox._textbox
            tk_text.tag_add(tag, "1.0", "2.0")
            tk_text.tag_configure(tag, foreground=ACCENT_BROWN, underline=True)
            tk_text.tag_bind(
                tag, "<Button-1>",
                lambda e, t=tag: self._on_click(t),
            )
            tk_text.tag_bind(tag, "<Enter>", lambda e: tk_text.configure(cursor="hand2"))
            tk_text.tag_bind(tag, "<Leave>", lambda e: tk_text.configure(cursor=""))

    def add_headlines(self, timestamp: str, headlines: list[str]) -> None:
        for headline in headlines:
            self.add_headline(timestamp, headline)

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
        self._headlines.clear()
        self._tag_articles.clear()

    def _on_click(self, tag: str) -> None:
        data = self._tag_articles.get(tag)
        if data and self.on_article_click:
            self.on_article_click(*data)