"""Dialogs to log how a block went and to add a workout."""
from dataclasses import dataclass
from datetime import date
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..lifelog import Workout
from ..schedule import Block
from ..store import Entry

FOCUS_CHOICES = ["Not rated", "1", "2", "3", "4", "5"]
WORKOUT_KINDS = ["Gym", "Run", "Walk", "Cycling", "Yoga", "Swim"]
MAX_SUBJECT_CHIPS = 8


@dataclass(frozen=True)
class Extras:
    """Optional study subject plus free text (an achievement, or what you asked Claude)."""
    subject: str = ""
    text: str = ""


def ask_log(parent, block: Block, day: date, status: str, existing: Entry | None, subjects: list[str], on_save: Callable[[Entry, Extras], None]) -> None:
    dialog = Adw.AlertDialog(heading=f"{block.name}: {status}", body="A skipped block needs a reason.")
    note = Adw.EntryRow(title="Why was it skipped? (required)" if status == "skipped" else "Note (optional)")
    note.set_text(existing.note if existing else "")
    focus = Adw.ComboRow(title="Focus", model=Gtk.StringList.new(FOCUS_CHOICES))
    focus.set_selected((existing.focus or 0) if existing else 0)
    group = Adw.PreferencesGroup()
    group.add(note)
    subject = Adw.EntryRow(title="Subject (e.g. Python)")
    detail = Adw.EntryRow(title=_detail_title(block))
    if status != "skipped":
        group.add(focus)
        if block.category == "Study":
            group.add(subject)
        if block.category in ("Study", "Claude"):
            group.add(detail)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.append(group)
    if status != "skipped" and block.category == "Study" and subjects:
        content.append(_subject_chips(subjects, subject))
    dialog.set_extra_child(content)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("save", "Save")
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("save")

    def refresh_save(*_):
        dialog.set_response_enabled("save", status != "skipped" or bool(note.get_text().strip()))

    def on_response(_dialog, response):
        if response == "save":
            rating = None if status == "skipped" or focus.get_selected() == 0 else focus.get_selected()
            entry = Entry(day, block.key, status, note.get_text().strip(), rating)
            on_save(entry, Extras(subject.get_text().strip(), detail.get_text().strip()))

    note.connect("changed", refresh_save)
    refresh_save()
    dialog.connect("response", on_response)
    dialog.present(parent)


def ask_workout(parent, day: date, on_save: Callable[[Workout], None]) -> None:
    dialog = Adw.AlertDialog(heading="Add a workout", body="Pick a type or type your own.")
    kind = Adw.EntryRow(title="Type")
    minutes = Adw.SpinRow.new_with_range(5, 300, 5)
    minutes.set_title("Minutes")
    minutes.set_value(45)
    note = Adw.EntryRow(title="Details (sets, reps, distance...)")
    group = Adw.PreferencesGroup()
    for row in (kind, minutes, note):
        group.add(row)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.append(_chips(WORKOUT_KINDS, kind))
    content.append(group)
    dialog.set_extra_child(content)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("save", "Save")
    dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_response_enabled("save", False)
    kind.connect("changed", lambda *_: dialog.set_response_enabled("save", bool(kind.get_text().strip())))
    dialog.connect("response", lambda _d, r: r == "save" and on_save(Workout(day, kind.get_text().strip(), int(minutes.get_value()), note.get_text().strip())))
    dialog.present(parent)


def _detail_title(block: Block) -> str:
    return "What did you ask Claude to do?" if block.category == "Claude" else "What did you achieve?"


def _subject_chips(subjects: list[str], target: Adw.EntryRow) -> Gtk.Widget:
    return _chips(subjects[:MAX_SUBJECT_CHIPS], target)


def _chips(options: list[str], target: Adw.EntryRow) -> Gtk.FlowBox:
    flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=6, column_spacing=6, row_spacing=6)
    for option in options:
        button = Gtk.Button(label=option, css_classes=["pill", "flat"])
        button.connect("clicked", lambda _b, text=option: target.set_text(text))
        flow.append(button)
    return flow
