"""Daily targets from schedule.yaml, plus which block categories form each section."""
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Goals:
    steps: int = 8000
    sleep_hours: float = 7.5
    water_l: float = 2.5
    calories: int | None = None
    weight_kg: float | None = None
    fitness_categories: tuple[str, ...] = ("Health",)
    study_categories: tuple[str, ...] = ("Study", "Claude")

    @classmethod
    def from_file(cls, path: Path) -> "Goals":
        raw = yaml.safe_load(Path(path).read_text())
        goals, sections = raw.get("goals", {}), raw.get("sections", {})
        known = {name: goals[name] for name in ("steps", "sleep_hours", "water_l", "calories", "weight_kg") if name in goals}
        if "fitness" in sections:
            known["fitness_categories"] = tuple(sections["fitness"])
        if "study" in sections:
            known["study_categories"] = tuple(sections["study"])
        return cls(**known)
