from __future__ import annotations


def test_intro_screen_constructs(ctk_root, loaded_city):
    from src.gui.intro import IntroScreen
    screen = IntroScreen(ctk_root)
    screen.show()
    ctk_root.update_idletasks()
    if screen._overlay:
        screen._overlay.destroy()


def test_settings_popup_constructs(ctk_root, loaded_city):
    cfg, _ = loaded_city
    from src.gui.settings_popup import SettingsPopup
    popup = SettingsPopup(ctk_root)
    popup.show(cfg.settings)
    ctk_root.update_idletasks()
    if popup._overlay:
        popup._overlay.destroy()


def test_postgame_screen_constructs(ctk_root, loaded_city):
    cfg, city = loaded_city
    from src.engine.end_check import EndResult
    from src.gui.postgame import PostgameScreen
    screen = PostgameScreen(ctk_root, cfg)
    result = EndResult(
        triggered=True,
        condition_id="term_completion",
        label="Term Completion",
        narrative="Your term has ended.",
    )
    screen.show(city, result)
    ctk_root.update_idletasks()
    if screen._overlay:
        screen._overlay.destroy()


def test_hover_popup_constructs(ctk_root, loaded_city):
    cfg, city = loaded_city
    from src.gui.popups import HoverPopup
    popup = HoverPopup(ctk_root)
    district = city.districts["the_shades"]
    building = next(iter(district.buildings.values()))
    popup.show(building, district.name, x=100, y=100)
    ctk_root.update_idletasks()
    popup.hide()


def test_remedy_menu_constructs_for_water_event(ctk_root, loaded_city, detected_event_water):
    cfg, city = loaded_city
    event, district, building = detected_event_water
    from src.gui.popups import RemedyMenu
    menu = RemedyMenu(ctk_root, cfg)
    menu.show(building, event, city, x=100, y=100, current_tick=10)
    ctk_root.update_idletasks()
    if menu._window:
        menu._window.destroy()


def test_event_popup_constructs(ctk_root, loaded_city, detected_event_water):
    cfg, city = loaded_city
    event, _, _ = detected_event_water
    from src.gui.popups import EventPopup
    popup = EventPopup(ctk_root)
    popup.show(event, city, more_remaining=0)
    ctk_root.update_idletasks()
    if popup._window:
        popup._window.destroy()


def test_article_popup_constructs(ctk_root):
    from src.gui.popups import ArticlePopup
    popup = ArticlePopup(ctk_root)
    popup.show("Day 1 - 08:00", "Test headline", "Test article body, several lines of context.")
    ctk_root.update_idletasks()
    if popup._window:
        popup._window.destroy()


def test_info_popup_metric_constructs(ctk_root, loaded_city):
    cfg, city = loaded_city
    from src.gui.info_popups import InfoPopup
    popup = InfoPopup(ctk_root, cfg)
    for key in ("public_trust", "budget", "regulatory_pressure",
                "political_stability", "legitimacy", "public_health", "crime_level"):
        popup.show_metric(city, key)
        ctk_root.update_idletasks()
        if popup._window:
            popup._window.destroy()
            popup._window = None


def test_info_popup_district_constructs(ctk_root, loaded_city):
    cfg, city = loaded_city
    from src.gui.info_popups import InfoPopup
    popup = InfoPopup(ctk_root, cfg)
    for district_id in list(city.districts)[:3]:
        popup.show_district(city, district_id)
        ctk_root.update_idletasks()
        if popup._window:
            popup._window.destroy()
            popup._window = None
