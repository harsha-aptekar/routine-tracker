"""Small reusable widgets: panels, tiles, chips, rows, and the period selector."""
from datetime import datetime
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..stats import Gap, Period


def label(text: str, *classes: str, wrap: bool = False, xalign: float = 0) -> Gtk.Label:
    return Gtk.Label(label=text, xalign=xalign, wrap=wrap, css_classes=list(classes))


def chip(text: str, kind: str = "") -> Gtk.Label:
    return Gtk.Label(label=text, css_classes=["chip", f"chip-{kind}"] if kind else ["chip"], halign=Gtk.Align.START)


def column(*children: Gtk.Widget, spacing: int = 12, classes: tuple[str, ...] = ()) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing, css_classes=list(classes))
    for child in children:
        box.append(child)
    return box


def row(*children: Gtk.Widget, spacing: int = 12, classes: tuple[str, ...] = ()) -> Gtk.Box:
    box = Gtk.Box(spacing=spacing, css_classes=list(classes))
    for child in children:
        box.append(child)
    return box


def panel(title: str, *children: Gtk.Widget) -> Gtk.Box:
    return column(label(title, "section-title"), *children, spacing=10, classes=("panel",))


def tile(value: str, caption: str, note: str = "", note_kind: str = "") -> Gtk.Box:
    box = column(label(value, "value"), label(caption, "caption"), spacing=2, classes=("tile",))
    box.set_hexpand(True)
    if note:
        box.append(chip(note, note_kind))
    return box


def tile_grid(tiles: list[Gtk.Widget]) -> Gtk.FlowBox:
    grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2, max_children_per_line=4, column_spacing=10, row_spacing=10, homogeneous=True)
    for item in tiles:
        grid.append(item)
    return grid


def gap_row(gap: Gap) -> Gtk.Box:
    return column(label(gap.title, "name"), label(gap.detail, "muted", wrap=True), spacing=2, classes=("gap-row",))


def good_row(title: str, detail: str) -> Gtk.Box:
    return column(label(title, "name"), label(detail, "muted", wrap=True), spacing=2, classes=("good-row",))


def note_row(title: str, detail: str) -> Gtk.Box:
    return column(label(title, "name"), label(detail, "muted", wrap=True), spacing=2, classes=("note-row",))


def delta_chip(score: float | None, previous: float | None, on_hero: bool = False) -> Gtk.Label:
    if score is None or previous is None:
        return chip("no previous period")
    diff = score - previous
    arrow = "▲" if diff > 0.5 else "▼" if diff < -0.5 else "■"
    kind = "" if on_hero else "good" if diff > 0.5 else "bad" if diff < -0.5 else ""
    return chip(f"{arrow} {abs(diff):.0f} pts vs last period", kind)


class PeriodBar(Gtk.Box):
    """Week/Month toggle with previous/next arrows; calls on_change(period)."""

    def __init__(self, clock: Callable[[], datetime], on_change: Callable[[Period], None], kinds: tuple[str, ...] = ("week", "month")):
        super().__init__(spacing=8)
        self._clock, self._on_change = clock, on_change
        self.period = Period.of(kinds[0], clock().date())
        self._title = Gtk.Label(hexpand=True, css_classes=["section-title"])
        previous, following = Gtk.Button(icon_name="go-previous-symbolic"), Gtk.Button(icon_name="go-next-symbolic")
        previous.connect("clicked", lambda _b: self._set(self.period.previous()))
        following.connect("clicked", lambda _b: self._set(self.period.following()))
        for widget in (previous, self._title, following):
            self.append(widget)
        if len(kinds) > 1:
            self.append(self._kind_toggle(kinds))
        self._title.set_label(self.period.title)

    def _kind_toggle(self, kinds: tuple[str, ...]) -> Gtk.Box:
        box, group = Gtk.Box(css_classes=["linked"]), None
        for kind in kinds:
            button = Gtk.ToggleButton(label=kind.capitalize(), active=kind == self.period.kind)
            if group:
                button.set_group(group)
            group = group or button
            button.connect("toggled", lambda b, k=kind: b.get_active() and self._set(Period.of(k, self._clock().date())))
            box.append(button)
        return box

    def _set(self, period: Period) -> None:
        self.period = period
        self._title.set_label(period.title)
        self._on_change(period)
