"""Builds the study-coach prompt from computed facts and asks the local model."""
from .ollama_client import Ollama
from .stats import Period, Report
from .study import UNTAGGED, StudyReport

TASK = """
TASK: Write exactly 3 bullet points of advice for next week.
Each bullet must start with a verb and mention one subject or block named in the facts above.
Do not repeat the facts and do not add any number that is not in the facts.
Example bullet: - Schedule 2 extra hours for Chemistry, it dropped from 4.0h to 1.0h."""
MAX_CONTEXT = 5
BULLETS = ("-", "*", "•")


def build_prompt(period: Period, study: StudyReport, routine: Report) -> str:
    lines = [f"FACTS about my study ({period.title}):"]
    if routine.score is not None:
        lines.append(f"- Completion of Study and Claude blocks: {routine.score:.0f}%")
    subjects = sorted(((s, m) for s, m in study.minutes_by_subject.items() if s != UNTAGGED), key=lambda kv: -kv[1])
    lines += [f"- {s}: {_hours(m)} this period, {_hours(study.previous_minutes_by_subject.get(s, 0))} last period" for s, m in subjects]
    lines += [f"- Subjects not studied at all this period: {', '.join(study.neglected)}"] if study.neglected else []
    lines += [f"- Weak block: {b.label} done only {b.score:.0f}% of the time" for b in routine.blocks[:3] if b.score < 80]
    lines += [f"- Skip reason for {s.label}: {s.reason}" for s in routine.skips[:MAX_CONTEXT]]
    lines += [f"- Achieved in {a.subject or 'no subject'}: {a.text}" for a in study.achievements[:MAX_CONTEXT] if a.text]
    lines += [f"- I asked Claude: {r.text}" for r in study.claude_requests[:MAX_CONTEXT]]
    return "\n".join(lines) + "\n" + TASK


def recommend(client: Ollama, period: Period, study: StudyReport, routine: Report) -> str:
    return _bullets_only(client.generate(build_prompt(period, study, routine)))


def _bullets_only(text: str) -> str:
    bullets = [line.strip() for line in text.splitlines() if line.strip().startswith(BULLETS)]
    return "\n".join(bullets) or text


def _hours(minutes: float) -> str:
    return f"{minutes / 60:.1f}h"
