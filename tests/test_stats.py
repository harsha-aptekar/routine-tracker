"""Tests for scoring, streaks, and the month report."""
import unittest
from datetime import date, datetime

from routine_tracker.stats import Period, Stats, remark_for
from routine_tracker.store import Entry
from tests.helpers import block, make_schedule, make_store

MONDAY = date(2026, 10, 12)
EVENING = datetime(2026, 10, 12, 23, 59, 59)


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.schedule, self.store = make_schedule(), make_store()
        self.stats = Stats(self.schedule, self.store)

    def log_all(self, day, status="done"):
        for block in self.schedule.blocks_for(day):
            if block.scored:
                self.store.save(Entry(day, block.key, status, "reason"))

    def test_unlogged_finished_blocks_count_as_skipped(self):
        self.assertEqual(self.stats.day_score(MONDAY, EVENING), 0.0)

    def test_partial_counts_half(self):
        self.store.save(Entry(MONDAY, "wake", "done"))
        self.store.save(Entry(MONDAY, "study_1", "partial"))
        study = block(self.schedule, MONDAY, "study_1")
        self.assertEqual(self.stats.day_score(MONDAY, datetime.combine(MONDAY, study.end)), 75.0)

    def test_no_score_before_anything_ends(self):
        self.assertIsNone(self.stats.day_score(MONDAY, datetime.combine(MONDAY, block(self.schedule, MONDAY, "wake").start)))

    def test_free_time_is_not_scored(self):
        saturday = date(2026, 10, 17)
        self.store.save(Entry(saturday, "free", "skipped", "x"))
        self.assertTrue(all(o.block.key != "free" for o in self.stats._outcomes(saturday, datetime(2026, 10, 17, 23, 59))))

    def test_streak_counts_consecutive_good_days(self):
        for day in (date(2026, 10, 10), date(2026, 10, 11), MONDAY):
            self.log_all(day)
        self.assertEqual(self.stats.streak(EVENING), 3)

    def test_streak_breaks_on_bad_day(self):
        self.log_all(date(2026, 10, 10))
        self.log_all(date(2026, 10, 11), "skipped")
        self.log_all(MONDAY)
        self.assertEqual(self.stats.streak(EVENING), 1)

    def test_report_for_month(self):
        self.log_all(date(2026, 10, 10))
        self.log_all(date(2026, 10, 11))
        self.log_all(MONDAY)
        self.store.save(Entry(MONDAY, "walk", "skipped", "rain"))
        report = self.stats.report(Period.month(MONDAY), EVENING)
        self.assertEqual(report.most_skipped.label, block(self.schedule, MONDAY, "walk").label)
        self.assertEqual(report.worst[0], MONDAY)
        self.assertLess(report.by_category["Health"], 100)
        self.assertEqual(report.skips[0].reason, "rain")

    def test_report_filters_by_category(self):
        self.log_all(MONDAY)
        report = self.stats.report(Period.week(MONDAY), EVENING, ("Study",))
        self.assertEqual(list(report.by_category), ["Study"])
        study_minutes = sum(block(self.schedule, MONDAY, key).minutes for key in ("study_1", "study_2"))
        self.assertEqual((report.planned_minutes, report.done_minutes), (study_minutes, study_minutes))

    def test_report_compares_with_previous_period(self):
        for offset in range(7):
            self.log_all(date(2026, 10, 5 + offset))
        self.log_all(MONDAY, "skipped")
        report = self.stats.report(Period.week(MONDAY), EVENING)
        self.assertEqual((report.score, report.previous), (0.0, 100.0))

    def test_weekday_scores(self):
        self.log_all(MONDAY)
        self.assertEqual(self.stats.report(Period.week(MONDAY), EVENING).weekdays, {0: 100.0})

    def test_period_navigation(self):
        week = Period.week(date(2026, 10, 14))
        self.assertEqual((week.first, week.last), (date(2026, 10, 12), date(2026, 10, 18)))
        self.assertEqual(Period.month(date(2026, 10, 14)).previous().first, date(2026, 9, 1))
        self.assertEqual(week.following().first, date(2026, 10, 19))

    def test_days_before_first_log_are_ignored(self):
        self.log_all(MONDAY)
        report = self.stats.report(Period.month(MONDAY), EVENING)
        self.assertEqual(list(report.daily), [MONDAY])

    def test_remark_bands(self):
        self.assertIn("Outstanding", remark_for(95))
        self.assertIn("got away", remark_for(10))
