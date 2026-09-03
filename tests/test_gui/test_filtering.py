from __future__ import annotations

import tkinter as tk


def _collect_button_texts(window) -> list[str]:
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
    cfg, city = loaded_city
    event, district, building = detected_event_communications

    from src.gui.popups import RemedyMenu
    menu = RemedyMenu(ctk_root, cfg)
    menu.show(building, event, city, x=100, y=100, current_tick=10)
    ctk_root.update_idletasks()

    button_blob = " ".join(_collect_button_texts(menu._window))

    # the labels are the communications-category overrides of the remedy ids
    assert "Restore Signal" in button_blob
    assert "Network Upgrade" in button_blob
    assert "Reroute Traffic" in button_blob
    assert "Issue Network Bulletin" in button_blob
    assert "No Comment" in button_blob

    # public_compensation and accountability_actions are not valid for communications
    assert "Refund Subscribers" not in button_blob
    assert "Suspend Tower Operator" not in button_blob

    if menu._window:
        menu._window.destroy()


def test_water_event_offers_all_pathways(ctk_root, loaded_city, detected_event_water):
    cfg, city = loaded_city
    event, district, building = detected_event_water

    from src.gui.popups import RemedyMenu
    menu = RemedyMenu(ctk_root, cfg)
    menu.show(building, event, city, x=100, y=100, current_tick=10)
    ctk_root.update_idletasks()

    button_blob = " ".join(_collect_button_texts(menu._window))

    assert "Emergency Repair" in button_blob
    assert "Infrastructure Overhaul" in button_blob
    assert "Public Notice & Compensation" in button_blob
    assert "Commission Technical Inquiry" in button_blob

    if menu._window:
        menu._window.destroy()
