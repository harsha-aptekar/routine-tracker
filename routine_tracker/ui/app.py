"""GTK application: window with five tabs, background reminders, and notifications."""
import os
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Notify", "0.7")
from gi.repository import Adw, Gio, GLib, Gtk, Notify

from .. import config
from ..goals import Goals
from ..lifelog import LifeLog
from ..ollama_client import Ollama
from ..reminders import ReminderPlanner
from ..schedule import Schedule
from ..stats import Stats
from ..store import Store
from . import theme
from .fitness_view import FitnessView
from .overview_page import OverviewPage
from .routine_view import RoutineView
from .section_page import SectionPage
from .study_view import StudyView
from .today_page import TodayPage

TICK_SECONDS = 30
APP_ID = "dev.harsha.RoutineTracker"


class TrackerApp(Adw.Application):
    def __init__(self, background: bool):
        super().__init__(application_id=APP_ID)
        self._background = background
        self._fired: set[tuple] = set()

    def do_startup(self):
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(APP_ID)
        theme.apply_theme()
        schedule = Schedule.from_file(config.schedule_path())
        goals = Goals.from_file(config.schedule_path())
        store = Store(config.db_path())
        log, stats = LifeLog(store.connection), Stats(schedule, store)
        client = Ollama(os.environ.get("ROUTINE_TRACKER_OLLAMA_MODEL", ""))
        self._planner = ReminderPlanner(schedule, store)
        self._today = TodayPage(schedule, store, stats, goals, log, self._show)
        self._pages = {
            "today": self._today,
            "fitness": SectionPage(FitnessView(stats, goals, log)),
            "study": SectionPage(StudyView(stats, goals, log, client)),
            "routine": SectionPage(RoutineView(stats)),
            "overview": OverviewPage(stats, goals, self._show),
        }
        self._window = self._build_window()
        self.set_accels_for_action("app.quit", ["<Control>q"])
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        Notify.init("Routine Tracker")
        GLib.timeout_add_seconds(TICK_SECONDS, self._tick)
        self.hold()

    def do_activate(self):
        if self._background:
            self._background = False
            return
        self._window.present()

    def _build_window(self) -> Adw.ApplicationWindow:
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        nav, group, self._nav_buttons = Gtk.Box(spacing=4), None, {}
        for section in (theme.TODAY, theme.FITNESS, theme.STUDY, theme.ROUTINE, theme.OVERVIEW):
            self._stack.add_named(self._pages[section.key], section.key)
            button = Gtk.ToggleButton(label=f"{section.emoji} {section.title}", css_classes=["nav-btn", f"nav-{section.key}"])
            if group:
                button.set_group(group)
            group = group or button
            button.connect("toggled", lambda b, key=section.key: b.get_active() and self._show(key))
            self._nav_buttons[section.key] = button
            nav.append(button)
        self._nav_buttons["today"].set_active(True)
        header = Adw.HeaderBar(title_widget=nav)
        header.pack_end(Gtk.Button(icon_name="application-exit-symbolic", action_name="app.quit", tooltip_text="Quit (stops reminders)"))
        view = Adw.ToolbarView(content=self._stack)
        view.add_top_bar(header)
        window = Adw.ApplicationWindow(application=self, title="Routine Tracker", default_width=820, default_height=860, content=view)
        window.connect("close-request", self._hide_instead_of_close)
        return window

    def _show(self, key: str) -> None:
        self._nav_buttons[key].set_active(True)
        self._pages[key].refresh()
        self._stack.set_visible_child_name(key)

    @staticmethod
    def _hide_instead_of_close(window) -> bool:
        window.set_visible(False)
        return True

    def _tick(self) -> bool:
        for reminder in self._planner.due(datetime.now()):
            if reminder.id not in self._fired:
                self._fired.add(reminder.id)
                Notify.Notification.new(reminder.title, reminder.body).show()
        self._today.refresh()
        return True
