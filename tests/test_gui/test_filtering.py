"""GUI integration: confirm RemedyMenu only renders filtered remedies for a
domain-restricted event (Communications)."""

from __future__ import annotations

import tkinter as tk


def _collect_button_texts(window) -> list[str]:
    """Walk every child of a Tk window and collect text from any widget that has it.
    CTk widgets raise ValueError if `text` is not a supported option, hence the
    broad except."""
    texts: list[str] = []
    stack = [window]
    while stack:
        widget = stack.pop()
        for child in widget.winfo_children():
            stack.append(child)
            try:
                text = child.cget("text")
                if isinstance(text, str) and text:
                    texts.append(text)
            except (tk.TclError, AttributeError, ValueError):
                pass
    return texts


def test_communications_event_offers_only_filtered_remedies(
    ctk_root, loaded_city, detected_event_communications
):
    """Communications events on clacks_tower buildings use the 'communications'
    label overrides. The two valid pathways + 3 universals show, the two filtered
    pathways do not."""
    cfg, city = loaded_city
    event, district, building = detected_event_communications

    from src.gui.popups import RemedyMenu
    menu = RemedyMenu(ctk_root, cfg)
    menu.show(building, event, city, x=100, y=100, current_tick=10)
    ctk_root.update_idletasks()

    button_blob = " ".join(_collect_button_texts(menu._window))

    # SHOULD appear (universals + technical_restoration + resilience_investment)
    assert "Restore Signal" in button_blob          # technical_restoration
    assert "Network Upgrade" in button_blob          # resilience_investment
    assert "Reroute Traffic" in button_blob          # operational_workaround (meta)
    assert "Issue Network Bulletin" in button_blob   # press_statement (meta)
    assert "No Comment" in button_blob               # do_nothing (meta)

    # SHOULD NOT appear (filtered out by communications domain)
    assert "Refund Subscribers" not in button_blob   # public_compensation
    assert "Suspend Tower Operator" not in button_blob  # accountability_actions

    if menu._window:
        menu._window.destroy()


def test_water_event_offers_all_pathways(ctk_root, loaded_city, detected_event_water):
    """Water events on water_source buildings use the 'infrastructure' label
    overrides and have all four pathways available."""
    cfg, city = loaded_city
    event, district, building = detected_event_water

    from src.gui.popups import RemedyMenu
    menu = RemedyMenu(ctk_root, cfg)
    menu.show(building, event, city, x=100, y=100, current_tick=10)
    ctk_root.update_idletasks()

    button_blob = " ".join(_collect_button_texts(menu._window))

    assert "Emergency Repair" in button_blob                # technical_restoration
    assert "Infrastructure Overhaul" in button_blob          # resilience_investment
    assert "Public Notice & Compensation" in button_blob    # public_compensation
    assert "Commission Technical Inquiry" in button_blob    # accountability_actions

    if menu._window:
        menu._window.destroy()
