"""SQLite storage for block logs and daily remarks."""
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

STATUSES = ("done", "partial", "skipped")


@dataclass(frozen=True)
class Entry:
    """What happened in one block on one day."""
    day: date
    block_key: str
    status: str
    note: str = ""
    focus: int | None = None

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        if self.status == "skipped" and not self.note.strip():
            raise ValueError("a skipped block needs a reason")
        if self.focus is not None and not 1 <= self.focus <= 5:
            raise ValueError("focus must be between 1 and 5")


class Store:
    def __init__(self, path: Path | str):
        self._conn = sqlite3.connect(path)
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS entries (day TEXT, block_key TEXT, status TEXT, note TEXT, focus INTEGER,"
                " PRIMARY KEY (day, block_key))"
            )
            self._conn.execute("CREATE TABLE IF NOT EXISTS remarks (day TEXT PRIMARY KEY, text TEXT)")

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def save(self, entry: Entry) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?)",
                (entry.day.isoformat(), entry.block_key, entry.status, entry.note, entry.focus),
            )

    def entries(self, day: date) -> dict[str, Entry]:
        return {e.block_key: e for e in self.entries_between(day, day)}

    def entries_between(self, first: date, last: date) -> list[Entry]:
        rows = self._conn.execute(
            "SELECT day, block_key, status, note, focus FROM entries WHERE day BETWEEN ? AND ?",
            (first.isoformat(), last.isoformat()),
        )
        return [Entry(date.fromisoformat(d), key, status, note, focus) for d, key, status, note, focus in rows]

    def first_day(self) -> date | None:
        value = self._conn.execute("SELECT MIN(day) FROM entries").fetchone()[0]
        return date.fromisoformat(value) if value else None

    def set_remark(self, day: date, text: str) -> None:
        with self._conn:
            self._conn.execute("INSERT OR REPLACE INTO remarks VALUES (?, ?)", (day.isoformat(), text))

    def remark(self, day: date) -> str:
        row = self._conn.execute("SELECT text FROM remarks WHERE day = ?", (day.isoformat(),)).fetchone()
        return row[0] if row else ""
