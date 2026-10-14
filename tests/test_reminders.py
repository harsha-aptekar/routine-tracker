"""Tests for which reminders fire and when."""
import unittest
from datetime import date, datetime, timedelta

from routine_tracker.reminders import ReminderPlanner
from routine_tracker.store import Entry
from tests.helpers import block, make_schedule, make_store


class ReminderTest(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.schedule = make_schedule()
        self.planner = ReminderPlanner(self.schedule, self.store)

    def at(self, key, edge, seconds=10, minutes=0):
        moment = getattr(block(self.schedule, date(2026, 10, 12), key), edge)
        return datetime.combine(date(2026, 10, 12), moment) + timedelta(seconds=seconds, minutes=minutes)

    def kinds(self, now):
        return [(r.id[1], r.id[2]) for r in self.planner.due(now)]

    def test_start_and_previous_end_reminders(self):
        self.assertEqual(self.kinds(self.at("study_1", "start")), [("wake", "end"), ("study_1", "start")])

    def test_end_reminder_only_if_unlogged(self):
        self.assertIn(("walk", "end"), self.kinds(self.at("walk", "end")))
        self.store.save(Entry(date(2026, 10, 12), "walk", "done"))
        self.assertNotIn(("walk", "end"), self.kinds(self.at("walk", "end")))

    def test_late_nudge_fifteen_minutes_after_end(self):
        self.assertIn(("walk", "late"), self.kinds(self.at("walk", "end", minutes=15)))

    def test_day_review(self):
        self.assertIn(("day", "review"), self.kinds(datetime.combine(date(2026, 10, 12), self.schedule.review_at) + timedelta(seconds=5)))

    def test_nothing_due_in_a_gap(self):
        self.assertEqual(self.kinds(self.at("walk", "end", minutes=5)), [])
