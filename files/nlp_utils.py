from __future__ import annotations

import re
import threading
from datetime import date, timedelta
from typing import Optional

import spacy
from spacy.tokens import Doc

_nlp: Optional[spacy.language.Language] = None
_lock = threading.Lock()

def _get_nlp() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        with _lock:
            if _nlp is None:
                try:
                    _nlp = spacy.load("en_core_web_sm")
                except OSError:
                    raise RuntimeError(
                        "spaCy model 'en_core_web_sm' not found.\n"
                        "Run:  python -m spacy download en_core_web_sm"
                    )
    return _nlp

def extract_subject(text: str, known_subjects: list[str]) -> Optional[str]:
    lower_text = text.lower()
    for subject in sorted(known_subjects, key=len, reverse=True):
        if subject.lower() in lower_text:
            return subject
    return None

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

def _next_weekday(weekday_index: int, *, next_week: bool = False) -> date:
    today = date.today()
    days_ahead = (weekday_index - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    if next_week and days_ahead < 7:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def _parse_relative_date(text: str) -> Optional[date]:
    lower = text.lower()
    today = date.today()

    if re.search(r"\btoday\b", lower):
        return today
    if re.search(r"\btomorrow\b", lower):
        return today + timedelta(days=1)
    if re.search(r"\bnext week\b", lower):
        return today + timedelta(weeks=1)
    if re.search(r"\bthis week\b", lower):
        return today + timedelta(days=3)

    next_match = re.search(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lower)
    if next_match:
        return _next_weekday(_WEEKDAYS[next_match.group(1)], next_week=True)

    this_match = re.search(r"\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lower)
    if this_match:
        return _next_weekday(_WEEKDAYS[this_match.group(1)], next_week=False)

    weekday_match = re.search(
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lower
    )
    if weekday_match:
        return _next_weekday(_WEEKDAYS[weekday_match.group(1)])

    in_days = re.search(r"\bin\s+(\d+)\s+days?\b", lower)
    if in_days:
        return today + timedelta(days=int(in_days.group(1)))
    in_weeks = re.search(r"\bin\s+(\d+)\s+weeks?\b", lower)
    if in_weeks:
        return today + timedelta(weeks=int(in_weeks.group(1)))

    month_day = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december"
        r"|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})\b",
        lower,
    )
    if month_day:
        month_num = _MONTH_NAMES[month_day.group(1)]
        day_num = int(month_day.group(2))
        try:
            candidate = date(today.year, month_num, day_num)
            if candidate < today:
                candidate = date(today.year + 1, month_num, day_num)
            return candidate
        except ValueError:
            pass

    day_month = re.search(
        r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september"
        r"|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b",
        lower,
    )
    if day_month:
        month_num = _MONTH_NAMES[day_month.group(2)]
        day_num = int(day_month.group(1))
        try:
            candidate = date(today.year, month_num, day_num)
            if candidate < today:
                candidate = date(today.year + 1, month_num, day_num)
            return candidate
        except ValueError:
            pass

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass

    return None

class ParsedTask:
    __slots__ = ("subject", "deadline", "description", "raw")

    def __init__(
        self,
        raw: str,
        subject: Optional[str] = None,
        deadline: Optional[date] = None,
        description: str = "",
    ) -> None:
        self.raw = raw
        self.subject = subject
        self.deadline = deadline
        self.description = description

    def is_complete(self) -> bool:
        return self.subject is not None and self.deadline is not None

    def __repr__(self) -> str:
        return (
            f"ParsedTask(subject={self.subject!r}, "
            f"deadline={self.deadline!r}, description={self.description!r})"
        )

def parse_task_input(text: str, known_subjects: list[str]) -> ParsedTask:
    nlp = _get_nlp()
    doc: Doc = nlp(text)

    subject = extract_subject(text, known_subjects)

    deadline = _parse_relative_date(text)

    if deadline is None:
        for ent in doc.ents:
            if ent.label_ == "DATE":
                deadline = _parse_relative_date(ent.text)
                if deadline is not None:
                    break

    description = _clean_description(text, subject, doc)

    return ParsedTask(raw=text, subject=subject, deadline=deadline, description=description)

def _clean_description(text: str, subject: Optional[str], doc: Doc) -> str:
    cleaned = text
    if subject:
        cleaned = re.sub(re.escape(subject), "", cleaned, flags=re.IGNORECASE)

    for ent in doc.ents:
        if ent.label_ == "DATE":
            cleaned = cleaned.replace(ent.text, "")

    cleaned = re.sub(
        r"\b(due|by|on|for|before|until|at|the|a|an|is|are|has|have)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.-")
    return cleaned or text.strip()