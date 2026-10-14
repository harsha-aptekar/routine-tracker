"""Shared layout for the Fitness, Study and Routine pages: hero, gaps, weekday chart, then section extras."""
import calendar
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..stats import Gap, Period, Report
from .charts import ColumnChart, Ring
from .theme import Theme
from .widgets import PeriodBar, column, delta_chip, good_row, gap_row, label, panel, row

WEEKDAYS = [name[:3] for name in calendar.day_name]


@dataclass
class SectionData:
    """Everything a view hands to the page for one period."""
    report: Report
    gaps: list[Gap]
    extras: list[Gtk.Widget]
    subtitle: str


class SectionView(Protocol):
    theme: Theme

    def load(self, period: Period, now: datetime) -> SectionData: ...


class SectionPage(Gtk.ScrolledWindow):
    def __init__(self, view: SectionView, clock: Callable[[], datetime] = datetime.now):
        super().__init__()
        self._view, self._clock = view, clock
        self._body = column(spacing=14)
        self._body.set_margin_top(14)
        self._body.set_margin_bottom(20)
        self._body.set_margin_start(18)
        self._body.set_margin_end(18)
        self._bar = PeriodBar(clock, lambda _period: self.refresh())
        self.set_child(self._body)
        self.refresh()

    def refresh(self) -> None:
        theme = self._view.theme
        data = self._view.load(self._bar.period, self._clock())
        child = self._body.get_first_child()
        while child:
            self._body.remove(child)
            child = self._body.get_first_child()
        for widget in (self._bar, self._hero(theme, data), self._gaps(data), self._weekdays(theme, data.report), *data.extras):
            self._body.append(widget)

    def _hero(self, theme: Theme, data: SectionData) -> Gtk.Box:
        ring = Ring(theme, 140, on_gradient=True)
        ring.update(data.report.score, "done")
        text = column(
            label(f"{theme.emoji}  {theme.title}", "hero-title"),
            label(data.subtitle, "muted", wrap=True),
            delta_chip(data.report.score, data.report.previous, on_hero=True),
            spacing=8,
        )
        text.set_hexpand(True)
        text.set_valign(Gtk.Align.CENTER)
        return row(text, ring, classes=("hero", f"hero-{theme.key}"))

    def _gaps(self, data: SectionData) -> Gtk.Box:
        rows = [gap_row(g) for g in data.gaps] or [good_row("Nothing is lacking 🎉", "Every measure is at or above target for this period.")]
        return panel("Where you're lacking", *rows)

    def _weekdays(self, theme: Theme, report: Report) -> Gtk.Box:
        chart = ColumnChart(theme, 150, unit="%")
        chart.update(WEEKDAYS, [report.weekdays.get(i) for i in range(7)], goal=80, max_value=100)
        return panel("Which weekdays slip? (dashed = 80% target)", chart)
