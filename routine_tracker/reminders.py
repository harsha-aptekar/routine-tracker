"""Decides which reminders are due right now (pure logic, no UI)."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .schedule import Schedule
from .store import Store

LATE_AFTER = timedelta(minutes=15)


@dataclass(frozen=True)
class Reminder:
    """A notification; `id` lets the caller avoid showing it twice."""
    id: tuple
    title: str
    body: str


class ReminderPlanner:
    def __init__(self, schedule: Schedule, store: Store, window: timedelta = timedelta(seconds=90)):
        self._schedule = schedule
        self._store = store
        self._window = window

    def due(self, now: datetime) -> list[Reminder]:
        return [r for when, r in self._planned(now.date()) if now - self._window < when <= now]

    def _planned(self, day: date) -> list[tuple[datetime, Reminder]]:
        logged = self._store.entries(day)
        planned = []
        for block in self._schedule.blocks_for(day):
            planned.append((_at(day, block.start), Reminder((day, block.key, "start"), f"Now: {block.name}", block.detail or "Time to begin.")))
            if block.scored and block.key not in logged:
                end = _at(day, block.end)
                planned.append((end, Reminder((day, block.key, "end"), f"{block.name} is over", "Log it: done, partial or skipped?")))
                planned.append((end + LATE_AFTER, Reminder((day, block.key, "late"), f"{block.name} still not logged", "Be honest and log it now.")))
        unlogged = sum(1 for b in self._schedule.blocks_for(day) if b.scored and b.key not in logged)
        body = f"{unlogged} block(s) unlogged. Log them and write today's remark." if unlogged else "All logged. Write today's remark."
        planned.append((_at(day, self._schedule.review_at), Reminder((day, "day", "review"), "Day review", body)))
        return planned


def _at(day: date, moment: time) -> datetime:
    return datetime.combine(day, moment)
