"""Fitness section: workout blocks plus body metrics against your goals."""
from datetime import datetime, timedelta

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..fitness import fitness_report
from ..goals import Goals
from ..lifelog import LifeLog
from ..stats import Period, Stats, report_gaps
from . import theme
from .charts import ColumnChart, LineChart
from .section_page import WEEKDAYS, SectionData
from .widgets import good_row, label, panel, tile, tile_grid


class FitnessView:
    theme = theme.FITNESS

    def __init__(self, stats: Stats, goals: Goals, log: LifeLog):
        self._stats, self._goals, self._log = stats, goals, log

    def load(self, period: Period, now: datetime) -> SectionData:
        report = self._stats.report(period, now, self._goals.fitness_categories)
        body = fitness_report(period, now, self._goals, self._log)
        gaps = sorted(body.gaps + report_gaps(report), key=lambda g: -g.severity)
        extras = [tile_grid(self._tiles(body)), self._steps(period, body)]
        if body.weights:
            extras.append(self._weight(period, body))
        extras.append(self._workouts(period))
        subtitle = f"{report.done_minutes / 60:.1f}h of {report.planned_minutes / 60:.1f}h planned workouts and walks done"
        return SectionData(report, gaps, extras, subtitle)

    def _tiles(self, body) -> list[Gtk.Widget]:
        goals = self._goals
        weight = f"{body.latest_weight:.1f} kg" if body.latest_weight else "-"
        change = f"{body.weight_change:+.1f} kg" if body.weight_change is not None else ""
        tiles = [
            tile(weight, "Latest weight", change),
            tile(f"{body.steps_avg:,.0f}" if body.steps_avg else "-", "Avg steps / day", f"goal hit {body.steps_goal_days}x", "good" if body.steps_goal_days else ""),
            tile(f"{body.workout_minutes} min", "Workouts", f"{body.workout_count} session(s)"),
            tile(f"{body.sleep_avg:.1f} h" if body.sleep_avg else "-", "Avg sleep", f"goal {goals.sleep_hours:g} h"),
            tile(f"{body.water_avg:.1f} L" if body.water_avg else "-", "Avg water", f"goal {goals.water_l:g} L"),
        ]
        if body.calories_avg:
            tiles.append(tile(f"{body.calories_avg:,.0f}", "Avg calories"))
        return tiles

    def _steps(self, period: Period, body) -> Gtk.Box:
        if period.kind == "week":
            chart = ColumnChart(self.theme, 160)
            days = [period.first + timedelta(days=i) for i in range(7)]
            chart.update(WEEKDAYS, [body.steps.get(d) for d in days], goal=self._goals.steps)
        else:
            chart = LineChart(self.theme)
            chart.update(body.steps, period.first, period.last, goal=self._goals.steps)
        return panel("Steps (dashed = goal)", chart)

    def _weight(self, period: Period, body) -> Gtk.Box:
        chart = LineChart(self.theme)
        chart.update(body.weights, period.first, period.last, goal=self._goals.weight_kg)
        return panel("Weight (kg)", chart)

    def _workouts(self, period: Period) -> Gtk.Box:
        workouts = self._log.workouts_between(period.first, period.last)
        rows = [good_row(f"{w.kind} · {w.minutes} min", f"{w.day:%a %d %b}" + (f" · {w.note}" if w.note else "")) for w in reversed(workouts[-10:])]
        return panel("Workout log", *(rows or [label("No workouts logged yet. Add one from the Today tab.", "muted")]))
