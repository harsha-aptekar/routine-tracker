"""Fitness report: body metrics and workouts for a period, checked against goals."""
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean

from .goals import Goals
from .lifelog import LifeLog
from .stats import Gap, Period


@dataclass(frozen=True)
class FitnessReport:
    weights: dict[date, float]
    steps: dict[date, int]
    steps_avg: float | None
    steps_goal_days: int
    sleep_avg: float | None
    water_avg: float | None
    calories_avg: float | None
    workout_minutes: int
    workout_count: int
    gaps: list[Gap]

    @property
    def latest_weight(self) -> float | None:
        return self.weights[max(self.weights)] if self.weights else None

    @property
    def weight_change(self) -> float | None:
        return self.weights[max(self.weights)] - self.weights[min(self.weights)] if len(self.weights) > 1 else None


def fitness_report(period: Period, now: datetime, goals: Goals, log: LifeLog) -> FitnessReport:
    elapsed = _elapsed_days(period, now)
    metrics = log.metrics_between(period.first, period.last)
    workouts = log.workouts_between(period.first, period.last)
    steps = {m.day: m.steps for m in metrics if m.steps is not None}
    weights = {m.day: m.weight_kg for m in metrics if m.weight_kg is not None}
    report = FitnessReport(
        weights=weights,
        steps=steps,
        steps_avg=_avg(steps.values()),
        steps_goal_days=sum(1 for v in steps.values() if v >= goals.steps),
        sleep_avg=_avg(m.sleep_hours for m in metrics if m.sleep_hours is not None),
        water_avg=_avg(m.water_l for m in metrics if m.water_l is not None),
        calories_avg=_avg(m.calories for m in metrics if m.calories is not None),
        workout_minutes=sum(w.minutes for w in workouts),
        workout_count=len(workouts),
        gaps=[],
    )
    gaps = sorted(_gaps(report, goals, elapsed), key=lambda g: -g.severity)
    return FitnessReport(**{**report.__dict__, "gaps": gaps})


def _gaps(report: FitnessReport, goals: Goals, elapsed: int) -> list[Gap]:
    gaps = []
    for title, average, goal, unit, fmt in (
        ("Steps", report.steps_avg, goals.steps, " steps", ",.0f"),
        ("Sleep", report.sleep_avg, goals.sleep_hours, " h", ".1f"),
        ("Water", report.water_avg, goals.water_l, " L", ".1f"),
    ):
        if average is None:
            if elapsed:
                gaps.append(Gap(title, f"Not logged at all in {elapsed} day(s).", 0.5))
        elif average < goal:
            gaps.append(Gap(title, f"Averaging {average:{fmt}}{unit} vs a goal of {goal:{fmt}}{unit}.", 1 - average / goal))
    if goals.weight_kg and report.latest_weight and abs(report.latest_weight - goals.weight_kg) > 0.5:
        direction = "above" if report.latest_weight > goals.weight_kg else "below"
        gaps.append(Gap("Weight", f"{abs(report.latest_weight - goals.weight_kg):.1f} kg {direction} your {goals.weight_kg:g} kg goal.", 0.6))
    if elapsed >= 3 and report.workout_count == 0:
        gaps.append(Gap("Workouts", "No workout sessions logged in this period.", 0.7))
    return gaps


def _elapsed_days(period: Period, now: datetime) -> int:
    return max((min(period.last, now.date()) - period.first).days + 1, 0)


def _avg(values) -> float | None:
    values = list(values)
    return mean(values) if values else None
