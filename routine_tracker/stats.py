"""Turns logs into scores, streaks, and per-period reports."""
import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import mean

from .schedule import Block, Schedule
from .store import Store

SCORES = {"done": 1.0, "partial": 0.5, "skipped": 0.0}
TARGET = 80.0
MIN_DAYS_FOR_WEEKDAY_GAP = 10
REMARKS = (
    (90, "Outstanding. This is the standard you set for yourself."),
    (TARGET, "Solid day, target met. Keep the streak alive."),
    (60, "Below target. Find the one block that slipped and protect it tomorrow."),
    (40, "Rough day. Decide tonight what tomorrow's first block looks like."),
    (0, "The day got away from you. Reset now: sleep on time and win your first block tomorrow."),
)


@dataclass(frozen=True)
class Period:
    """A week (Mon-Sun) or a calendar month."""
    kind: str
    first: date
    last: date

    @classmethod
    def week(cls, day: date) -> "Period":
        monday = day - timedelta(days=day.weekday())
        return cls("week", monday, monday + timedelta(days=6))

    @classmethod
    def month(cls, day: date) -> "Period":
        return cls("month", day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1]))

    @classmethod
    def of(cls, kind: str, day: date) -> "Period":
        return cls.week(day) if kind == "week" else cls.month(day)

    def previous(self) -> "Period":
        return Period.of(self.kind, self.first - timedelta(days=1))

    def following(self) -> "Period":
        return Period.of(self.kind, self.last + timedelta(days=1))

    @property
    def title(self) -> str:
        if self.kind == "month":
            return f"{calendar.month_name[self.first.month]} {self.first.year}"
        return f"{self.first:%d %b} - {self.last:%d %b}"


@dataclass(frozen=True)
class Outcome:
    """A block's result for one day; an unlogged finished block counts as skipped."""
    day: date
    block: Block
    status: str
    note: str = ""
    focus: int | None = None


@dataclass(frozen=True)
class BlockStat:
    """How one recurring block (e.g. Study 06:30) fared across the period."""
    label: str
    score: float
    done: int
    partial: int
    skipped: int

    @property
    def total(self) -> int:
        return self.done + self.partial + self.skipped


@dataclass(frozen=True)
class Skip:
    day: date
    label: str
    reason: str


@dataclass(frozen=True)
class Gap:
    """Something falling short, with a 0-1 severity used to rank it."""
    title: str
    detail: str
    severity: float


@dataclass(frozen=True)
class Report:
    score: float | None
    previous: float | None
    planned_minutes: int
    done_minutes: float
    daily: dict[date, float]
    blocks: list[BlockStat]
    weekdays: dict[int, float]
    skips: list[Skip]
    by_category: dict[str, float]
    avg_focus: float | None

    @property
    def best(self) -> tuple[date, float] | None:
        return max(self.daily.items(), key=lambda item: item[1], default=None)

    @property
    def worst(self) -> tuple[date, float] | None:
        return min(self.daily.items(), key=lambda item: item[1], default=None)

    @property
    def most_skipped(self) -> BlockStat | None:
        return max((b for b in self.blocks if b.skipped), key=lambda b: b.skipped, default=None)


def block_gaps(report: Report, limit: int = 4) -> list[Gap]:
    weak = [b for b in report.blocks if b.score < TARGET and b.total >= 2][:limit]
    return [Gap(b.label, f"Done {b.done} of {b.total} times, {b.skipped} skipped ({b.score:.0f}%).", 1 - b.score / 100) for b in weak]


def report_gaps(report: Report) -> list[Gap]:
    gaps = block_gaps(report)
    if len(report.daily) >= MIN_DAYS_FOR_WEEKDAY_GAP:
        weekday, score = min(report.weekdays.items(), key=lambda item: item[1])
        if score < TARGET:
            gaps.append(Gap(f"{calendar.day_name[weekday]}s", f"Your weakest weekday: only {score:.0f}% done.", 1 - score / 100))
    return sorted(gaps, key=lambda g: -g.severity)


def remark_for(score: float) -> str:
    return next(text for threshold, text in REMARKS if score >= threshold)


class Stats:
    def __init__(self, schedule: Schedule, store: Store):
        self._schedule = schedule
        self._store = store

    def day_score(self, day: date, now: datetime) -> float | None:
        outcomes = self._outcomes(day, now)
        return _percent(outcomes) if outcomes else None

    def streak(self, now: datetime) -> int:
        first = self._store.first_day()
        if first is None:
            return 0
        today_score = self.day_score(now.date(), now)
        count = 1 if today_score is not None and today_score >= TARGET else 0
        day = now.date() - timedelta(days=1)
        while day >= first and (score := self.day_score(day, now)) is not None and score >= TARGET:
            count += 1
            day -= timedelta(days=1)
        return count

    def report(self, period: Period, now: datetime, categories: tuple[str, ...] | None = None) -> Report:
        by_day = self._by_day(period, now, categories)
        outcomes = [o for day_outcomes in by_day.values() for o in day_outcomes]
        previous_outcomes = self.outcomes(period.previous(), now, categories)
        focus = [o.focus for o in outcomes if o.focus is not None]
        return Report(
            score=_percent(outcomes) if outcomes else None,
            previous=_percent(previous_outcomes) if previous_outcomes else None,
            planned_minutes=sum(o.block.minutes for o in outcomes),
            done_minutes=sum(o.block.minutes * SCORES[o.status] for o in outcomes),
            daily={day: _percent(items) for day, items in by_day.items()},
            blocks=_block_stats(outcomes),
            weekdays={wd: _percent(items) for wd, items in _group(outcomes, lambda o: o.day.weekday()).items()},
            skips=[Skip(o.day, o.block.label, o.note) for o in outcomes if o.status == "skipped" and o.note],
            by_category={c: _percent(items) for c, items in _group(outcomes, lambda o: o.block.category).items()},
            avg_focus=mean(focus) if focus else None,
        )

    def outcomes(self, period: Period, now: datetime, categories: tuple[str, ...] | None = None) -> list[Outcome]:
        return [o for day_outcomes in self._by_day(period, now, categories).values() for o in day_outcomes]

    def _by_day(self, period: Period, now: datetime, categories) -> dict[date, list[Outcome]]:
        first_logged = self._store.first_day()
        by_day = {}
        for offset in range((period.last - period.first).days + 1):
            day = period.first + timedelta(days=offset)
            if first_logged and first_logged <= day <= now.date():
                outcomes = [o for o in self._outcomes(day, now) if categories is None or o.block.category in categories]
                if outcomes:
                    by_day[day] = outcomes
        return by_day

    def _outcomes(self, day: date, now: datetime) -> list[Outcome]:
        entries = self._store.entries(day)
        outcomes = []
        for block in self._schedule.blocks_for(day):
            logged = entries.get(block.key)
            if block.scored and (logged or _has_ended(day, block, now)):
                outcomes.append(Outcome(day, block, logged.status if logged else "skipped", logged.note if logged else "", logged.focus if logged else None))
        return outcomes


def _has_ended(day: date, block: Block, now: datetime) -> bool:
    return day < now.date() or (day == now.date() and block.end <= now.time())


def _percent(outcomes: list[Outcome]) -> float:
    return mean(SCORES[o.status] for o in outcomes) * 100


def _group(outcomes: list[Outcome], key) -> dict:
    grouped = defaultdict(list)
    for outcome in outcomes:
        grouped[key(outcome)].append(outcome)
    return grouped


def _block_stats(outcomes: list[Outcome]) -> list[BlockStat]:
    stats = []
    for label, items in _group(outcomes, lambda o: o.block.label).items():
        counts = {status: sum(1 for o in items if o.status == status) for status in SCORES}
        stats.append(BlockStat(label, _percent(items), counts["done"], counts["partial"], counts["skipped"]))
    return sorted(stats, key=lambda b: b.score)
