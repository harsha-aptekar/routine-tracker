"""Shared fixtures: the public template schedule and an in-memory store."""
from pathlib import Path

from datetime import date

from routine_tracker.schedule import Block, Schedule
from routine_tracker.store import Store

SCHEDULE_FILE = Path(__file__).resolve().parent.parent / "schedule.example.yaml"


def make_schedule() -> Schedule:
    return Schedule.from_file(SCHEDULE_FILE)


def make_store() -> Store:
    return Store(":memory:")


def block(schedule: Schedule, day: date, key: str) -> Block:
    return next(b for b in schedule.blocks_for(day) if b.key == key)
