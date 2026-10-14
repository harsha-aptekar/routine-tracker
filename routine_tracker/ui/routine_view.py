"""Routine section: are you following the whole timetable?"""
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..stats import Period, Stats, report_gaps
from . import theme
from .charts import Heatmap
from .section_page import SectionData
from .widgets import label, note_row, panel, tile, tile_grid


class RoutineView:
    theme = theme.ROUTINE

    def __init__(self, stats: Stats):
        self._stats = stats

    def load(self, period: Period, now: datetime) -> SectionData:
        report = self._stats.report(period, now)
        best, worst = report.best, report.worst
        tiles = [
            tile(f"{self._stats.streak(now)} days", "Streak at 80%+"),
            tile(f"{best[0]:%a %d} · {best[1]:.0f}%" if best else "-", "Best day"),
            tile(f"{worst[0]:%a %d} · {worst[1]:.0f}%" if worst else "-", "Toughest day"),
            tile(f"{report.avg_focus:.1f} / 5" if report.avg_focus else "-", "Average focus"),
        ]
        extras = [tile_grid(tiles)]
        if period.kind == "month":
            heatmap = Heatmap(self.theme)
            heatmap.update(report.daily, period.first.year, period.first.month)
            extras.append(panel("Calendar", heatmap))
        extras.append(self._skips(report))
        score = f"{report.score:.0f}% of the timetable followed" if report.score is not None else "Nothing finished in this period yet"
        return SectionData(report, report_gaps(report), extras, score)

    def _skips(self, report) -> Gtk.Box:
        reasons = [note_row(f"{s.label} · {s.day:%a %d %b}", s.reason) for s in reversed(report.skips[-8:])]
        return panel("Why you skipped", *(reasons or [label("No skip reasons recorded.", "muted")]))
