"""Tests for the fitness and study reports."""
import unittest
from datetime import date, datetime

from routine_tracker.fitness import fitness_report
from routine_tracker.goals import Goals
from routine_tracker.lifelog import Achievement, DailyMetrics, LifeLog, Workout
from routine_tracker.stats import Period, Stats
from routine_tracker.store import Entry
from routine_tracker.study import UNTAGGED, study_report
from tests.helpers import block, make_schedule, make_store

MONDAY = date(2026, 10, 12)
NOW = datetime(2026, 10, 14, 12, 0)


class FitnessTest(unittest.TestCase):
    def setUp(self):
        self.log = LifeLog(make_store().connection)
        self.week = Period.week(MONDAY)

    def report(self, goals=Goals()):
        return fitness_report(self.week, NOW, goals, self.log)

    def test_steps_below_goal_become_a_gap(self):
        self.log.save_metrics(DailyMetrics(MONDAY, steps=4000, sleep_hours=8, water_l=3))
        report = self.report()
        self.assertEqual(report.steps_avg, 4000)
        self.assertEqual(report.steps_goal_days, 0)
        self.assertIn("Steps", [g.title for g in report.gaps])

    def test_missing_data_is_a_gap(self):
        self.assertIn("Sleep", [g.title for g in self.report().gaps])

    def test_weight_change_and_goal(self):
        self.log.save_metrics(DailyMetrics(MONDAY, weight_kg=80))
        self.log.save_metrics(DailyMetrics(date(2026, 10, 14), weight_kg=79))
        report = self.report(Goals(weight_kg=75))
        self.assertEqual(report.weight_change, -1)
        self.assertIn("Weight", [g.title for g in report.gaps])

    def test_workout_totals(self):
        self.log.add_workout(Workout(MONDAY, "Gym", 45))
        self.log.add_workout(Workout(date(2026, 10, 13), "Run", 30))
        report = self.report()
        self.assertEqual((report.workout_minutes, report.workout_count), (75, 2))
        self.assertNotIn("Workouts", [g.title for g in report.gaps])


class StudyTest(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.log = LifeLog(self.store.connection)
        self.schedule = make_schedule()
        self.stats = Stats(self.schedule, self.store)

    def report(self):
        return study_report(Period.week(MONDAY), NOW, ("Study", "Claude"), self.stats, self.log)

    def test_minutes_split_across_subjects_of_a_block(self):
        self.store.save(Entry(MONDAY, "study_1", "done"))
        self.log.add_achievement(Achievement(MONDAY, "study_1", "Python", "decorators"))
        self.log.add_achievement(Achievement(MONDAY, "study_1", "SQL", "joins"))
        minutes, half = self.report().minutes_by_subject, block(self.schedule, MONDAY, "study_1").minutes / 2
        self.assertEqual((minutes["Python"], minutes["SQL"]), (half, half))

    def test_untagged_minutes_and_partial(self):
        self.store.save(Entry(MONDAY, "study_2", "partial"))
        self.assertEqual(self.report().minutes_by_subject, {UNTAGGED: block(self.schedule, MONDAY, "study_2").minutes / 2})

    def test_neglected_subjects(self):
        self.log.add_achievement(Achievement(date(2026, 10, 7), "study_1", "Algebra", "x"))
        self.log.add_achievement(Achievement(MONDAY, "study_1", "Python", "y"))
        self.assertEqual(self.report().neglected, ["Algebra"])
