"""Overview: the whole month at a glance, with a ring per section that jumps to its page."""
from datetime import datetime
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..goals import Goals
from ..stats import Stats
from . import theme
from .charts import Heatmap, Ring
from .widgets import PeriodBar, column, delta_chip, label, panel, row, tile, tile_grid

SECTIONS = (("fitness", theme.FITNESS), ("study", theme.STUDY), ("routine", theme.ROUTINE))


class OverviewPage(Gtk.ScrolledWindow):
    def __init__(self, stats: Stats, goals: Goals, navigate: Callable[[str], None], clock: Callable[[], datetime] = datetime.now):
        super().__init__()
        self._stats, self._goals, self._navigate, self._clock = stats, goals, navigate, clock
        self._body = column(spacing=14)
        for side, size in (("top", 14), ("bottom", 20), ("start", 18), ("end", 18)):
            getattr(self._body, f"set_margin_{side}")(size)
        self._bar = PeriodBar(clock, lambda _p: self.refresh(), kinds=("month", "week"))
        self.set_child(self._body)
        self.refresh()

    def refresh(self) -> None:
        period, now = self._bar.period, self._clock()
        overall = self._stats.report(period, now)
        child = self._body.get_first_child()
        while child:
            self._body.remove(child)
            child = self._body.get_first_child()
        ring = Ring(theme.OVERVIEW, 150, on_gradient=True)
        ring.update(overall.score, "overall")
        text = column(label("✨  Overview", "hero-title"), label(period.title, "muted"), delta_chip(overall.score, overall.previous, on_hero=True), spacing=8)
        text.set_hexpand(True)
        text.set_valign(Gtk.Align.CENTER)
        rings = row(*(self._section_ring(key, t, period, now) for key, t in SECTIONS), spacing=8)
        rings.set_homogeneous(True)
        tiles = [tile(f"{self._stats.streak(now)} days", "Streak at 80%+"), tile(overall.most_skipped.label if overall.most_skipped else "-", "Most skipped block")]
        for widget in (self._bar, row(text, ring, classes=("hero", "hero-overview")), panel("Sections (tap to open)", rings), tile_grid(tiles)):
            self._body.append(widget)
        if period.kind == "month":
            heatmap = Heatmap(theme.OVERVIEW)
            heatmap.update(overall.daily, period.first.year, period.first.month)
            self._body.append(panel("Calendar", heatmap))

    def _section_ring(self, key: str, section_theme: theme.Theme, period, now) -> Gtk.Button:
        categories = {"fitness": self._goals.fitness_categories, "study": self._goals.study_categories}.get(key)
        report = self._stats.report(period, now, categories)
        ring = Ring(section_theme, 96)
        ring.update(report.score, "done")
        button = Gtk.Button(child=column(ring, label(f"{section_theme.emoji} {section_theme.title}", "name", xalign=0.5), spacing=4), css_classes=["flat"])
        button.connect("clicked", lambda _b: self._navigate(key))
        return button
