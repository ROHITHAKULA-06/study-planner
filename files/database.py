import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import Optional

DB_PATH = Path(__file__).parent / "planner.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS subjects (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL UNIQUE,
                difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 10)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                description TEXT    NOT NULL,
                deadline    TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending'
                                    CHECK(status IN ('pending','in_progress','done')),
                time_spent  REAL    NOT NULL DEFAULT 0.0,
                created_at  TEXT    NOT NULL DEFAULT (DATE('now'))
            );
        """)

        seed_subjects = [
            ("Mathematics",   9),
            ("Physics",       8),
            ("Chemistry",     7),
            ("History",       5),
            ("English",       4),
            ("Biology",       6),
            ("Computer Science", 8),
            ("Geography",     4),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO subjects (name, difficulty) VALUES (?, ?)",
            seed_subjects,
        )

def get_all_subjects() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()

def add_subject(name: str, difficulty: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO subjects (name, difficulty) VALUES (?, ?)", (name, difficulty)
        )
        return cur.lastrowid

def update_subject_difficulty(subject_id: int, difficulty: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE subjects SET difficulty = ? WHERE id = ?", (difficulty, subject_id)
        )

def delete_subject(subject_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))

def add_task(
    subject_id: int,
    description: str,
    deadline: date,
    status: str = "pending",
    time_spent: float = 0.0,
) -> int:
    deadline_str = deadline.isoformat() if isinstance(deadline, date) else str(deadline)
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO tasks (subject_id, description, deadline, status, time_spent)
               VALUES (?, ?, ?, ?, ?)""",
            (subject_id, description, deadline_str, status, time_spent),
        )
        return cur.lastrowid

def get_all_tasks() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT  t.id,
                    t.subject_id,
                    s.name        AS subject_name,
                    s.difficulty,
                    t.description,
                    t.deadline,
                    t.status,
                    t.time_spent,
                    t.created_at
            FROM tasks t
            JOIN subjects s ON s.id = t.subject_id
            ORDER BY t.deadline ASC
        """).fetchall()

def get_pending_tasks() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT  t.id,
                    t.subject_id,
                    s.name        AS subject_name,
                    s.difficulty,
                    t.description,
                    t.deadline,
                    t.status,
                    t.time_spent
            FROM tasks t
            JOIN subjects s ON s.id = t.subject_id
            WHERE t.status != 'done'
            ORDER BY t.deadline ASC
        """).fetchall()

def update_task_status(task_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
        )

def update_task_time(task_id: int, additional_hours: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET time_spent = time_spent + ? WHERE id = ?",
            (additional_hours, task_id),
        )

def delete_task(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

def get_recently_completed_tasks(limit: int = 10) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT  t.id,
                    s.difficulty,
                    t.status,
                    t.deadline
            FROM tasks t
            JOIN subjects s ON s.id = t.subject_id
            WHERE t.status = 'done'
            ORDER BY t.rowid DESC
            LIMIT ?
        """, (limit,)).fetchall()