"""Loads the timetable and answers which blocks apply on a given date."""
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import yaml

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class Block:
    """One timed slot of the day, e.g. Study 06:30-08:00."""
    key: str
    name: str
    start: time
    end: time
    category: str
    scored: bool = True
    detail: str = ""

    @property
    def minutes(self) -> int:
        return (self.end.hour - self.start.hour) * 60 + self.end.minute - self.start.minute

    @property
    def label(self) -> str:
        return f"{self.name} {self.start:%H:%M}"

    def contains(self, moment: time) -> bool:
        return self.start <= moment < self.end


class Schedule:
    """The full week, keyed by weekday name."""

    def __init__(self, blocks_by_day: dict[str, list[Block]], review_at: time):
        missing = set(DAY_NAMES) - blocks_by_day.keys()
        if missing:
            raise ValueError(f"schedule has no blocks for: {sorted(missing)}")
        self._blocks_by_day = blocks_by_day
        self.review_at = review_at

    @classmethod
    def from_file(cls, path: Path) -> "Schedule":
        raw = yaml.safe_load(Path(path).read_text())
        blocks_by_day = {}
        for day_type in raw["day_types"].values():
            blocks = [_parse_block(entry) for entry in day_type["blocks"]]
            for day in day_type["days"]:
                blocks_by_day[day] = blocks
        return cls(blocks_by_day, time.fromisoformat(raw["review_at"]))

    def blocks_for(self, day: date) -> list[Block]:
        return self._blocks_by_day[DAY_NAMES[day.weekday()]]

    def current(self, now: datetime) -> Block | None:
        return next((b for b in self.blocks_for(now.date()) if b.contains(now.time())), None)


def _parse_block(entry: dict) -> Block:
    return Block(**{**entry, "start": time.fromisoformat(entry["start"]), "end": time.fromisoformat(entry["end"])})
