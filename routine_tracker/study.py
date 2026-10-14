"""Study report: hours per subject, achievements, and subjects slipping away."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .lifelog import Achievement, ClaudeRequest, LifeLog
from .stats import SCORES, Period, Stats

UNTAGGED = "Untagged"


@dataclass(frozen=True)
class StudyReport:
    minutes_by_subject: dict[str, float]
    previous_minutes_by_subject: dict[str, float]
    achievements: list[Achievement]
    claude_requests: list[ClaudeRequest]
    neglected: list[str]


def study_report(period: Period, now: datetime, categories: tuple[str, ...], stats: Stats, log: LifeLog) -> StudyReport:
    achievements = log.achievements_between(period.first, period.last)
    previous = period.previous()
    previous_achievements = log.achievements_between(previous.first, previous.last)
    subjects_now = {a.subject for a in achievements if a.subject}
    subjects_before = [a.subject for a in previous_achievements if a.subject]
    return StudyReport(
        minutes_by_subject=_minutes_by_subject(stats.outcomes(period, now, categories), achievements),
        previous_minutes_by_subject=_minutes_by_subject(stats.outcomes(previous, now, categories), previous_achievements),
        achievements=achievements,
        claude_requests=log.claude_requests_between(period.first, period.last),
        neglected=sorted(set(subjects_before) - subjects_now),
    )


def _minutes_by_subject(outcomes, achievements: list[Achievement]) -> dict[str, float]:
    tagged = defaultdict(set)
    for achievement in achievements:
        tagged[(achievement.day, achievement.block_key)].add(achievement.subject or UNTAGGED)
    minutes = defaultdict(float)
    for outcome in outcomes:
        worked = outcome.block.minutes * SCORES[outcome.status]
        if worked:
            subjects = tagged.get((outcome.day, outcome.block.key)) or {UNTAGGED}
            for subject in subjects:
                minutes[subject] += worked / len(subjects)
    return dict(minutes)
