"""Where the schedule file and the database live."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def schedule_path() -> Path:
    personal = PROJECT_ROOT / "schedule.yaml"
    return Path(os.environ.get("ROUTINE_TRACKER_SCHEDULE", personal if personal.exists() else PROJECT_ROOT / "schedule.example.yaml"))


def db_path() -> Path:
    path = Path(os.environ.get("ROUTINE_TRACKER_DB", PROJECT_ROOT / "data" / "tracker.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
