"""Section colors, emoji, and the app stylesheet."""
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk


@dataclass(frozen=True)
class Theme:
    """One section's identity: name, emoji, and a two-color gradient."""
    key: str
    title: str
    emoji: str
    start: str
    end: str

    @property
    def start_rgb(self) -> tuple[float, float, float]:
        return _rgb(self.start)

    @property
    def end_rgb(self) -> tuple[float, float, float]:
        return _rgb(self.end)


TODAY = Theme("today", "Today", "☀️", "#f472b6", "#fb923c")
FITNESS = Theme("fitness", "Fitness", "💪", "#ff6b6b", "#ffb347")
STUDY = Theme("study", "Study", "📚", "#8b5cf6", "#38bdf8")
ROUTINE = Theme("routine", "Routine", "🧭", "#14b8a6", "#4ade80")
OVERVIEW = Theme("overview", "Overview", "✨", "#f472b6", "#fbbf24")
BY_CATEGORY_KEY = {t.key: t for t in (TODAY, FITNESS, STUDY, ROUTINE, OVERVIEW)}


def apply_theme() -> None:
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    provider = Gtk.CssProvider()
    provider.load_from_path(str(Path(__file__).with_name("style.css")))
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)


def _rgb(hex_color: str) -> tuple[float, float, float]:
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
