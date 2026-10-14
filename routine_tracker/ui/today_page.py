"""Today view: the Now card, daily score, what needs attention, check-in, and the block timeline."""
from datetime import datetime
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..goals import Goals
from ..lifelog import Achievement, ClaudeRequest, DailyMetrics, LifeLog, Workout
from ..schedule import Block, Schedule
from ..stats import TARGET, Period, Stats, remark_for
from ..store import Entry, Store
from . import theme
from .charts import Ring
from .log_dialog import Extras, ask_log, ask_workout
from .widgets import chip, column, label, panel, row

STATUSES = (("done", "Done"), ("partial", "Partial"), ("skipped", "Skip"))
HERO_BY_SECTION = {"fitness": theme.FITNESS, "study": theme.STUDY, "routine": theme.ROUTINE}
CHECKIN_FIELDS = (("weight_kg", "Weight (kg)", float), ("steps", "Steps", int), ("sleep_hours", "Sleep (h)", float), ("water_l", "Water (L)", float), ("calories", "Calories", int))


class TodayPage(Gtk.ScrolledWindow):
    def __init__(self, schedule: Schedule, store: Store, stats: Stats, goals: Goals, log: LifeLog,
                 navigate: Callable[[str], None], clock: Callable[[], datetime] = datetime.now):
        super().__init__()
        self._schedule, self._store, self._stats, self._goals, self._log = schedule, store, stats, goals, log
        self._navigate, self._clock = navigate, clock
        self._hero = row(classes=("hero",))
        self._score = row(classes=("panel",))
        self._attention = column(spacing=10, classes=("panel",))
        self._timeline = column(spacing=8)
        self._fields: dict[str, Gtk.Entry] = {}
        self._checkin_message = label("", "muted")
        body = column(self._hero, self._score, self._attention, self._checkin(), panel("Today's timeline", self._timeline), self._remark_panel(), spacing=14)
        for side in ("top", "bottom", "start", "end"):
            getattr(body, f"set_margin_{side}")(18 if side in ("start", "end") else 14)
        self.set_child(body)
        self.refresh()

    def refresh(self) -> None:
        now = self._clock()
        entries = self._store.entries(now.date())
        self._fill_hero(now, entries)
        self._fill_score(now)
        self._fill_attention(now)
        self._fill_timeline(now, entries)

    def _fill_hero(self, now: datetime, entries: dict[str, Entry]) -> None:
        _clear(self._hero)
        for name in ("hero-today", "hero-fitness", "hero-study", "hero-routine"):
            self._hero.remove_css_class(name)
        current = self._schedule.current(now)
        if current is None:
            upcoming = next((b for b in self._schedule.blocks_for(now.date()) if b.start > now.time()), None)
            self._hero.add_css_class("hero-today")
            text = f"Next: {upcoming.name} at {upcoming.start:%H:%M}" if upcoming else "Day complete. Write your remark below."
            self._hero.append(column(label("☀️  Between blocks", "hero-title"), label(text, "muted"), spacing=6))
            return
        section = self._section_of(current)
        self._hero.add_css_class(f"hero-{section}")
        left = (datetime.combine(now.date(), current.end) - now).seconds // 60
        details = column(label(f"NOW · {HERO_BY_SECTION[section].emoji}", "muted"), label(current.name, "hero-title"),
                         label(f"{current.start:%H:%M} - {current.end:%H:%M} · {left} min left" + (f" · {current.detail}" if current.detail else ""), "muted", wrap=True), spacing=4)
        details.set_hexpand(True)
        self._hero.append(details)
        if current.scored:
            self._hero.append(self._status_buttons(current, entries.get(current.key), "pill-btn"))

    def _fill_score(self, now: datetime) -> None:
        _clear(self._score)
        score = self._stats.day_score(now.date(), now)
        ring = Ring(theme.ROUTINE, 96)
        ring.update(score, "today")
        streak = self._stats.streak(now)
        hint = remark_for(score) if score is not None else "Your day has just begun."
        text = column(label("Today's score", "section-title"), label(hint, "muted", wrap=True), chip(f"🔥 {streak} day streak at 80%+", "warn" if streak else ""), spacing=6)
        text.set_hexpand(True)
        text.set_valign(Gtk.Align.CENTER)
        self._score.append(ring)
        self._score.append(text)

    def _fill_attention(self, now: datetime) -> None:
        _clear(self._attention)
        self._attention.append(label("Needs attention this week", "section-title"))
        week, flagged = Period.week(now.date()), row(spacing=8)
        for section, categories in (("fitness", self._goals.fitness_categories), ("study", self._goals.study_categories), ("routine", None)):
            score = self._stats.report(week, now, categories).score
            if score is not None and score < TARGET:
                button = Gtk.Button(label=f"{HERO_BY_SECTION[section].emoji} {HERO_BY_SECTION[section].title} {score:.0f}%", css_classes=["chip", "chip-bad", "flat"])
                button.connect("clicked", lambda _b, key=section: self._navigate(key))
                flagged.append(button)
        self._attention.append(flagged if flagged.get_first_child() else label("All three sections are on track this week. 🎉", "muted"))

    def _fill_timeline(self, now: datetime, entries: dict[str, Entry]) -> None:
        _clear(self._timeline)
        current = self._schedule.current(now)
        for block in self._schedule.blocks_for(now.date()):
            entry = entries.get(block.key)
            classes = ["block-row", f"stripe-{self._section_of(block)}"] + (["now"] if block == current else [])
            name = column(label(f"{block.start:%H:%M} - {block.end:%H:%M}", "time"), label(block.name, "name"), spacing=0)
            name.set_hexpand(True)
            line = row(name, spacing=10, classes=tuple(classes))
            summary = _summary(entry)
            if summary:
                line.append(label(summary, "muted", wrap=True))
            if block.scored:
                line.append(self._status_buttons(block, entry, "status-btn"))
            self._timeline.append(line)

    def _status_buttons(self, block: Block, entry: Entry | None, css: str) -> Gtk.Box:
        box = row(spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        for status, text in STATUSES:
            button = Gtk.Button(label=text, css_classes=[css] + ([status if css == "status-btn" else "picked"] if entry and entry.status == status else []))
            button.connect("clicked", self._on_click, block, status, entry)
            box.append(button)
        return box

    def _on_click(self, _button, block: Block, status: str, entry: Entry | None) -> None:
        day = self._clock().date()
        if status == "done" and not entry and block.category not in ("Study", "Claude"):
            self._save(Entry(day, block.key, "done"), Extras())
        else:
            ask_log(self.get_root(), block, day, status, entry, self._log.subjects(), self._save)

    def _save(self, entry: Entry, extras: Extras) -> None:
        self._store.save(entry)
        block_category = next(b.category for b in self._schedule.blocks_for(entry.day) if b.key == entry.block_key)
        if extras.text and block_category == "Study":
            self._log.add_achievement(Achievement(entry.day, entry.block_key, extras.subject, extras.text))
        elif extras.subject and block_category == "Study":
            self._log.add_achievement(Achievement(entry.day, entry.block_key, extras.subject, ""))
        if extras.text and block_category == "Claude":
            self._log.add_claude_request(ClaudeRequest(entry.day, extras.text))
        self.refresh()

    def _section_of(self, block: Block) -> str:
        if block.category in self._goals.fitness_categories:
            return "fitness"
        return "study" if block.category in self._goals.study_categories else "routine"

    def _checkin(self) -> Gtk.Box:
        metrics = self._log.metrics(self._clock().date())
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2, max_children_per_line=5, column_spacing=8, row_spacing=8, homogeneous=True)
        for name, title, _kind in CHECKIN_FIELDS:
            value = getattr(metrics, name)
            entry = Gtk.Entry(width_chars=7, placeholder_text=title, text="" if value is None else f"{value:g}", input_purpose=Gtk.InputPurpose.NUMBER)
            self._fields[name] = entry
            grid.append(column(label(title, "caption"), entry, spacing=3))
        save = Gtk.Button(label="Save check-in", css_classes=["pill-btn", "suggested-action"])
        save.connect("clicked", self._save_checkin)
        add = Gtk.Button(label="+ Workout", css_classes=["pill-btn"])
        add.connect("clicked", lambda _b: ask_workout(self.get_root(), self._clock().date(), self._add_workout))
        return panel("💪 Daily check-in", grid, row(save, add, self._checkin_message, spacing=10))

    def _add_workout(self, workout: Workout) -> None:
        self._log.add_workout(workout)
        self._checkin_message.set_label(f"Added {workout.kind}, {workout.minutes} min.")

    def _save_checkin(self, _button) -> None:
        values = {}
        for name, title, kind in CHECKIN_FIELDS:
            text = self._fields[name].get_text().strip().replace(",", "")
            try:
                values[name] = kind(float(text)) if text else None
            except ValueError:
                self._checkin_message.set_label(f"'{text}' is not a number for {title}.")
                return
        self._log.save_metrics(DailyMetrics(self._clock().date(), **values))
        self._checkin_message.set_label("Saved.")

    def _remark_panel(self) -> Gtk.Box:
        remark = Adw.EntryRow(title="Your remark for today", show_apply_button=True)
        remark.set_text(self._store.remark(self._clock().date()))
        remark.connect("apply", lambda r: self._store.set_remark(self._clock().date(), r.get_text().strip()))
        group = Adw.PreferencesGroup()
        group.add(remark)
        return column(group, classes=("panel",))


def _clear(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child:
        box.remove(child)
        child = box.get_first_child()


def _summary(entry: Entry | None) -> str:
    if entry is None:
        return ""
    focus = f"focus {entry.focus}" if entry.focus else ""
    return " · ".join(p for p in (focus, entry.note) if p)
