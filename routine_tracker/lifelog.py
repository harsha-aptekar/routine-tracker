"""SQLite storage for body metrics, workouts, study achievements, and Claude requests."""
import sqlite3
from dataclasses import dataclass
from datetime import date

METRIC_FIELDS = ("weight_kg", "steps", "sleep_hours", "water_l", "calories")


@dataclass(frozen=True)
class DailyMetrics:
    """Optional body numbers for one day."""
    day: date
    weight_kg: float | None = None
    steps: int | None = None
    sleep_hours: float | None = None
    water_l: float | None = None
    calories: int | None = None


@dataclass(frozen=True)
class Workout:
    day: date
    kind: str
    minutes: int
    note: str = ""
    id: int | None = None


@dataclass(frozen=True)
class Achievement:
    """What you got done in a study block, tagged by subject."""
    day: date
    block_key: str
    subject: str
    text: str
    id: int | None = None


@dataclass(frozen=True)
class ClaudeRequest:
    day: date
    text: str
    id: int | None = None


class LifeLog:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS metrics (day TEXT PRIMARY KEY, weight_kg REAL, steps INTEGER,"
                " sleep_hours REAL, water_l REAL, calories INTEGER)"
            )
            conn.execute("CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY, day TEXT, kind TEXT, minutes INTEGER, note TEXT)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS achievements (id INTEGER PRIMARY KEY, day TEXT, block_key TEXT, subject TEXT, text TEXT)"
            )
            conn.execute("CREATE TABLE IF NOT EXISTS claude_requests (id INTEGER PRIMARY KEY, day TEXT, text TEXT)")

    def save_metrics(self, metrics: DailyMetrics) -> None:
        values = [getattr(metrics, name) for name in METRIC_FIELDS]
        with self._conn:
            self._conn.execute("INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?, ?, ?)", (metrics.day.isoformat(), *values))

    def metrics(self, day: date) -> DailyMetrics:
        return next(iter(self.metrics_between(day, day)), DailyMetrics(day))

    def metrics_between(self, first: date, last: date) -> list[DailyMetrics]:
        rows = self._rows("SELECT day, weight_kg, steps, sleep_hours, water_l, calories FROM metrics WHERE day BETWEEN ? AND ? ORDER BY day", first, last)
        return [DailyMetrics(date.fromisoformat(r[0]), *r[1:]) for r in rows]

    def add_workout(self, workout: Workout) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO workouts (day, kind, minutes, note) VALUES (?, ?, ?, ?)",
                (workout.day.isoformat(), workout.kind, workout.minutes, workout.note),
            )

    def workouts_between(self, first: date, last: date) -> list[Workout]:
        rows = self._rows("SELECT id, day, kind, minutes, note FROM workouts WHERE day BETWEEN ? AND ? ORDER BY day, id", first, last)
        return [Workout(date.fromisoformat(r[1]), r[2], r[3], r[4], r[0]) for r in rows]

    def add_achievement(self, achievement: Achievement) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO achievements (day, block_key, subject, text) VALUES (?, ?, ?, ?)",
                (achievement.day.isoformat(), achievement.block_key, achievement.subject, achievement.text),
            )

    def achievements_between(self, first: date, last: date) -> list[Achievement]:
        rows = self._rows("SELECT id, day, block_key, subject, text FROM achievements WHERE day BETWEEN ? AND ? ORDER BY day, id", first, last)
        return [Achievement(date.fromisoformat(r[1]), r[2], r[3], r[4], r[0]) for r in rows]

    def subjects(self) -> list[str]:
        rows = self._conn.execute("SELECT subject FROM achievements WHERE subject != '' GROUP BY subject ORDER BY MAX(day) DESC, MAX(id) DESC")
        return [r[0] for r in rows]

    def add_claude_request(self, request: ClaudeRequest) -> None:
        with self._conn:
            self._conn.execute("INSERT INTO claude_requests (day, text) VALUES (?, ?)", (request.day.isoformat(), request.text))

    def claude_requests_between(self, first: date, last: date) -> list[ClaudeRequest]:
        rows = self._rows("SELECT id, day, text FROM claude_requests WHERE day BETWEEN ? AND ? ORDER BY day, id", first, last)
        return [ClaudeRequest(date.fromisoformat(r[1]), r[2], r[0]) for r in rows]

    def _rows(self, sql: str, first: date, last: date) -> list[tuple]:
        return self._conn.execute(sql, (first.isoformat(), last.isoformat())).fetchall()
