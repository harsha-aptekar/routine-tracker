"""Study section: hours per subject, achievements, Claude requests, and local-AI recommendations."""
import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from ..goals import Goals
from ..lifelog import LifeLog
from ..ollama_client import Ollama, OllamaError
from ..recommend import recommend
from ..stats import Gap, Period, Report, Stats, report_gaps
from ..study import StudyReport, study_report
from . import theme
from .charts import HBars
from .section_page import SectionData
from .widgets import good_row, label, panel, tile, tile_grid


class RecommendationPanel(Gtk.Box):
    """Button + result area; asks the local model in a background thread so the UI never freezes."""

    def __init__(self, client: Ollama, cache: dict, key: tuple, period: Period, study: StudyReport, report: Report):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10, css_classes=["panel"])
        self._client, self._cache, self._key = client, cache, key
        self._args = (period, study, report)
        self._result = label(cache.get(key, "Ask your local model for study advice based on this period."), "muted", wrap=True)
        self._button = Gtk.Button(label="✨ Get recommendations", halign=Gtk.Align.START, css_classes=["pill-btn", "suggested-action"])
        self._button.connect("clicked", self._ask)
        for widget in (label("Recommendations", "section-title"), self._result, self._button):
            self.append(widget)

    def _ask(self, _button) -> None:
        self._button.set_sensitive(False)
        self._result.set_label("Thinking... a local model on CPU can take a minute.")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self) -> None:
        try:
            text = recommend(self._client, *self._args)
            self._cache[self._key] = text
        except OllamaError as error:
            text = str(error)
        GLib.idle_add(self._show, text)

    def _show(self, text: str) -> None:
        self._result.set_label(text)
        self._button.set_sensitive(True)


class StudyView:
    theme = theme.STUDY

    def __init__(self, stats: Stats, goals: Goals, log: LifeLog, client: Ollama):
        self._stats, self._goals, self._log, self._client = stats, goals, log, client
        self._cache: dict = {}

    def load(self, period: Period, now: datetime) -> SectionData:
        categories = self._goals.study_categories
        report = self._stats.report(period, now, categories)
        study = study_report(period, now, categories, self._stats, self._log)
        extras = [tile_grid(self._tiles(report, study)), self._subjects(study), self._achievements(study), self._claude(study)]
        extras.append(RecommendationPanel(self._client, self._cache, (period.kind, period.first), period, study, report))
        subtitle = f"{report.done_minutes / 60:.1f}h done of {report.planned_minutes / 60:.1f}h planned"
        gaps = report_gaps(report)
        gaps += [self._neglected(subject) for subject in study.neglected]
        return SectionData(report, sorted(gaps, key=lambda g: -g.severity), extras, subtitle)

    @staticmethod
    def _neglected(subject: str) -> Gap:
        return Gap(subject, "You studied this last period but not in this one.", 0.8)

    def _tiles(self, report: Report, study: StudyReport) -> list[Gtk.Widget]:
        subjects = [s for s in study.minutes_by_subject if s != "Untagged"]
        return [
            tile(f"{report.done_minutes / 60:.1f} h", "Hours done", f"of {report.planned_minutes / 60:.1f} h"),
            tile(str(len(subjects)), "Subjects studied"),
            tile(str(len(study.achievements)), "Achievements logged"),
            tile(str(len(study.claude_requests)), "Claude requests"),
        ]

    def _subjects(self, study: StudyReport) -> Gtk.Box:
        chart = HBars(self.theme)
        items = sorted(study.minutes_by_subject.items(), key=lambda kv: -kv[1])
        chart.update([(name, minutes, f"{minutes / 60:.1f} h") for name, minutes in items], max([m for _, m in items] + [1]))
        return panel("Hours by subject", chart if items else label("Log a subject when you finish a study block.", "muted"))

    def _achievements(self, study: StudyReport) -> Gtk.Box:
        rows = [good_row(f"{a.subject or 'No subject'} · {a.day:%a %d %b}", a.text) for a in reversed(study.achievements[-12:])]
        return panel("What you achieved", *(rows or [label("Nothing logged for this period yet.", "muted")]))

    def _claude(self, study: StudyReport) -> Gtk.Box:
        rows = [good_row(f"{r.day:%a %d %b}", r.text) for r in reversed(study.claude_requests[-10:])]
        return panel("What you asked Claude to do", *(rows or [label("Add what you asked Claude when logging the Claude block.", "muted")]))
