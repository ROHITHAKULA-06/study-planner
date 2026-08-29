from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

WEIGHTS = {"difficulty": 0.4, "urgency": 0.5, "progress": 0.1}

EXPECTED_HOURS: dict[int, float] = {
    1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 4.0,
    6: 5.0, 7: 7.0, 8: 10.0, 9: 12.0, 10: 15.0,
}

EASY_THRESHOLD = 4
HARD_THRESHOLD = 7
AVOIDANCE_PRIORITY_CUTOFF = 5.0
AVOIDANCE_EASY_STREAK = 3

COLOUR_HIGH   = "#FF4C4C"
COLOUR_MEDIUM = "#FFA040"
COLOUR_LOW    = "#4CAF50"

@dataclass
class TaskRecord:
    id: int
    subject_id: int
    subject_name: str
    difficulty: int
    description: str
    deadline: str
    status: str
    time_spent: float

    priority_score: float = field(default=0.0, init=False)
    days_remaining: int = field(default=0, init=False)
    progress_ratio: float = field(default=0.0, init=False)
    is_overdue: bool = field(default=False, init=False)
    colour: str = field(default=COLOUR_LOW, init=False)

    def __post_init__(self) -> None:
        today = date.today()
        deadline_date = date.fromisoformat(self.deadline)
        raw_days = (deadline_date - today).days
        self.days_remaining = max(0, raw_days)
        self.is_overdue = raw_days < 0

        expected = EXPECTED_HOURS.get(self.difficulty, 5.0)
        self.progress_ratio = min(self.time_spent / expected, 1.0) if expected > 0 else 0.0

        self.priority_score = _compute_score(
            difficulty=self.difficulty,
            days_remaining=self.days_remaining,
            progress_ratio=self.progress_ratio,
            is_overdue=self.is_overdue,
        )
        self.colour = _score_to_colour(self.priority_score)

@dataclass
class AvoidanceAlert:
    message: str
    avoided_tasks: list[str]

def _compute_score(
    difficulty: int,
    days_remaining: int,
    progress_ratio: float,
    is_overdue: bool,
) -> float:
    urgency_component = 10.0 / (days_remaining + 1)

    score = (
        difficulty * WEIGHTS["difficulty"]
        + urgency_component * WEIGHTS["urgency"]
        - progress_ratio * WEIGHTS["progress"]
    )

    if is_overdue:
        score += 3.0

    return round(max(0.0, score), 2)

def _score_to_colour(score: float) -> str:
    if score >= 7.0:
        return COLOUR_HIGH
    if score >= 4.0:
        return COLOUR_MEDIUM
    return COLOUR_LOW

def compute_priority(task_row: object) -> TaskRecord:
    return TaskRecord(
        id=task_row["id"],
        subject_id=task_row["subject_id"],
        subject_name=task_row["subject_name"],
        difficulty=task_row["difficulty"],
        description=task_row["description"],
        deadline=task_row["deadline"],
        status=task_row["status"],
        time_spent=task_row["time_spent"],
    )

def rank_tasks(task_rows: list) -> list[TaskRecord]:
    records = [compute_priority(row) for row in task_rows]
    records.sort(key=lambda r: r.priority_score, reverse=True)
    return records

def check_avoidance(
    recent_completed_rows: list,
    pending_rows: list,
    streak_threshold: int = AVOIDANCE_EASY_STREAK,
) -> Optional[AvoidanceAlert]:
    if not recent_completed_rows:
        return None

    recent_slice = list(recent_completed_rows)[:streak_threshold]
    if len(recent_slice) < streak_threshold:
        return None

    easy_streak = sum(
        1 for row in recent_slice if row["difficulty"] <= EASY_THRESHOLD
    )
    if easy_streak < streak_threshold:
        return None

    pending_records = rank_tasks(pending_rows)
    critical_hard = [
        r for r in pending_records
        if r.difficulty >= HARD_THRESHOLD
        and (r.is_overdue or r.priority_score >= AVOIDANCE_PRIORITY_CUTOFF)
    ]
    if not critical_hard:
        return None

    avoided_descriptions = [
        f"[{r.subject_name}] {r.description} "
        f"({'OVERDUE' if r.is_overdue else f'Score {r.priority_score}'})"
        for r in critical_hard[:3]
    ]

    message = (
        f"⚠️  Avoidance Alert!\n\n"
        f"You've completed {easy_streak} easy tasks in a row, but you have "
        f"{len(critical_hard)} high-priority hard task(s) waiting:\n\n"
        + "\n".join(f"  • {d}" for d in avoided_descriptions)
        + "\n\nTry tackling one of these next — even 25 minutes makes a difference!"
    )

    return AvoidanceAlert(message=message, avoided_tasks=avoided_descriptions)

def difficulty_label(difficulty: int) -> str:
    if difficulty <= EASY_THRESHOLD:
        return "Easy"
    if difficulty < HARD_THRESHOLD:
        return "Medium"
    return "Hard"

def format_days_remaining(record: TaskRecord) -> str:
    if record.is_overdue:
        overdue_days = abs((date.fromisoformat(record.deadline) - date.today()).days)
        return f"OVERDUE by {overdue_days}d"
    if record.days_remaining == 0:
        return "Due TODAY"
    if record.days_remaining == 1:
        return "Due TOMORROW"
    return f"{record.days_remaining} days left"