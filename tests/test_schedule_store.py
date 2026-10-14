"""Tests for the schedule and the store."""
import unittest
from datetime import date, datetime

from routine_tracker.store import Entry
from tests.helpers import block, make_schedule, make_store

MONDAY, SATURDAY = date(2026, 10, 12), date(2026, 10, 17)


class ScheduleTest(unittest.TestCase):
    def test_weekday_and_weekend_differ(self):
        schedule = make_schedule()
        self.assertIn("work", [b.key for b in schedule.blocks_for(MONDAY)])
        self.assertIn("lunch", [b.key for b in schedule.blocks_for(SATURDAY)])

    def test_current_block(self):
        schedule = make_schedule()
        study, walk = block(schedule, MONDAY, "study_1"), block(schedule, MONDAY, "walk")
        self.assertEqual(schedule.current(datetime.combine(MONDAY, study.start)).key, "study_1")
        self.assertIsNone(schedule.current(datetime.combine(MONDAY, walk.end)))


class StoreTest(unittest.TestCase):
    def test_save_replaces_entry(self):
        store = make_store()
        store.save(Entry(MONDAY, "walk", "partial"))
        store.save(Entry(MONDAY, "walk", "done", "good", 4))
        self.assertEqual(store.entries(MONDAY)["walk"].status, "done")

    def test_skip_requires_reason(self):
        with self.assertRaises(ValueError):
            Entry(MONDAY, "walk", "skipped")

    def test_focus_range(self):
        with self.assertRaises(ValueError):
            Entry(MONDAY, "walk", "done", focus=6)

    def test_remark_round_trip(self):
        store = make_store()
        store.set_remark(MONDAY, "Good day")
        self.assertEqual(store.remark(MONDAY), "Good day")
