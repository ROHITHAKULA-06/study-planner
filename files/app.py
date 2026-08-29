from __future__ import annotations

import threading
import tkinter as tk
from datetime import date
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from database import (
    init_db,
    add_task,
    get_all_subjects,
    add_subject,
    get_pending_tasks,
    get_recently_completed_tasks,
    update_task_status,
    update_task_time,
    delete_task,
)
from nlp_utils import parse_task_input
from planner_logic import (
    TaskRecord,
    check_avoidance,
    difficulty_label,
    format_days_remaining,
    rank_tasks,
    COLOUR_HIGH,
    COLOUR_MEDIUM,
    COLOUR_LOW,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_HEAD    = ("Segoe UI", 14, "bold")
FONT_BODY    = ("Segoe UI", 12)
FONT_SMALL   = ("Segoe UI", 10)
FONT_MONO    = ("Consolas", 11)

BG_CARD      = "#1E1E2E"
BG_PANEL     = "#181825"
BG_INPUT     = "#2A2A3E"
ACCENT       = "#7C6AF7"
TEXT_PRIMARY = "#CDD6F4"
TEXT_MUTED   = "#6C7086"

PILL_COLOURS = {
    COLOUR_HIGH:   ("#FF4C4C", "#2B1010"),
    COLOUR_MEDIUM: ("#FFA040", "#2B1C0A"),
    COLOUR_LOW:    ("#4CAF50", "#0A2B0E"),
}

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

class TaskCard(ctk.CTkFrame):
    def __init__(self, master, record: TaskRecord, refresh_cb, **kwargs):
        fg, bg = PILL_COLOURS.get(record.colour, ("#AAAAAA", "#222233"))
        super().__init__(master, fg_color=BG_CARD, corner_radius=10, **kwargs)
        self.record = record
        self.refresh_cb = refresh_cb
        self._build(fg, bg)

    def _build(self, accent_fg: str, accent_bg: str) -> None:
        r = self.record
        accent_bar = ctk.CTkFrame(self, width=5, fg_color=accent_fg, corner_radius=5)
        accent_bar.pack(side="left", fill="y", padx=(4, 8), pady=6)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, pady=6)

        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x", anchor="w")

        subj_pill = ctk.CTkLabel(
            row1,
            text=f" {r.subject_name} ",
            font=FONT_SMALL,
            fg_color=accent_bg,
            text_color=accent_fg,
            corner_radius=6,
        )
        subj_pill.pack(side="left", padx=(0, 8))

        diff_pill = ctk.CTkLabel(
            row1,
            text=f"D:{r.difficulty} ({difficulty_label(r.difficulty)})",
            font=FONT_SMALL,
            fg_color="#2A2A3E",
            text_color=TEXT_MUTED,
            corner_radius=6,
        )
        diff_pill.pack(side="left", padx=(0, 8))

        desc_lbl = ctk.CTkLabel(
            row1,
            text=r.description[:80] + ("…" if len(r.description) > 80 else ""),
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        desc_lbl.pack(side="left", fill="x", expand=True)

        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", anchor="w", pady=(2, 0))

        deadline_text = format_days_remaining(r)
        deadline_colour = accent_fg if r.is_overdue else TEXT_MUTED

        ctk.CTkLabel(
            row2, text=f"📅 {r.deadline}  •  {deadline_text}",
            font=FONT_SMALL, text_color=deadline_colour,
        ).pack(side="left")

        ctk.CTkLabel(
            row2, text=f"  ⏱ {r.time_spent:.1f}h logged",
            font=FONT_SMALL, text_color=TEXT_MUTED,
        ).pack(side="left")

        score_lbl = ctk.CTkLabel(
            row2,
            text=f"  Priority: {r.priority_score:.1f}",
            font=("Segoe UI", 10, "bold"),
            text_color=accent_fg,
        )
        score_lbl.pack(side="left")

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(side="right", padx=10, pady=6)

        status_var = ctk.StringVar(value=r.status)
        status_menu = ctk.CTkOptionMenu(
            ctrl,
            values=["pending", "in_progress", "done"],
            variable=status_var,
            width=120,
            command=lambda s: self._on_status_change(s),
        )
        status_menu.pack(pady=(0, 4))

        time_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        time_frame.pack()

        self._time_entry = ctk.CTkEntry(
            time_frame, width=50, placeholder_text="hrs",
            font=FONT_SMALL,
        )
        self._time_entry.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            time_frame, text="Log", width=40,
            command=self._on_log_time,
            fg_color=ACCENT, hover_color="#5A4FD1",
            font=FONT_SMALL,
        ).pack(side="left")

        ctk.CTkButton(
            ctrl, text="✕", width=30, height=24,
            fg_color="#3D1A1A", hover_color="#6B2020",
            text_color="#FF4C4C",
            command=self._on_delete,
            font=FONT_SMALL,
        ).pack(pady=(4, 0))

    def _on_status_change(self, status: str) -> None:
        update_task_status(self.record.id, status)
        self.refresh_cb()

    def _on_log_time(self) -> None:
        val = self._time_entry.get().strip()
        try:
            hours = float(val)
            if hours <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Enter a positive number of hours.")
            return
        update_task_time(self.record.id, hours)
        self.refresh_cb()

    def _on_delete(self) -> None:
        if messagebox.askyesno("Delete task", "Remove this task permanently?"):
            delete_task(self.record.id)
            self.refresh_cb()

class SubjectManager(ctk.CTkToplevel):
    def __init__(self, master, refresh_cb):
        super().__init__(master)
        self.title("Manage Subjects")
        self.geometry("400x520")
        self.resizable(False, False)
        self.grab_set()
        self.refresh_cb = refresh_cb
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Subjects & Difficulty", font=FONT_HEAD).pack(pady=(20, 10))
        self.list_frame = ctk.CTkScrollableFrame(self, height=300)
        self.list_frame.pack(fill="x", padx=20, pady=(0, 16))
        self._populate_list()

        ctk.CTkLabel(self, text="Add new subject:", font=FONT_SMALL).pack(anchor="w", padx=20)
        inp_row = ctk.CTkFrame(self, fg_color="transparent")
        inp_row.pack(fill="x", padx=20, pady=(4, 0))

        self.name_entry = ctk.CTkEntry(inp_row, placeholder_text="Subject name", width=200)
        self.name_entry.pack(side="left", padx=(0, 8))

        self.diff_var = ctk.IntVar(value=5)
        ctk.CTkLabel(inp_row, text="Difficulty:").pack(side="left")
        ctk.CTkSlider(
            inp_row, from_=1, to=10,
            variable=self.diff_var,
            number_of_steps=9, width=80,
        ).pack(side="left", padx=4)
        self.diff_lbl = ctk.CTkLabel(inp_row, textvariable=self.diff_var, width=24)
        self.diff_lbl.pack(side="left")

        ctk.CTkButton(
            self, text="Add Subject", command=self._add_subject,
            fg_color=ACCENT,
        ).pack(pady=12)

    def _populate_list(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()
        for subj in get_all_subjects():
            row = ctk.CTkFrame(self.list_frame, fg_color=BG_CARD, corner_radius=6)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=f"{subj['name']} — D:{subj['difficulty']} ({difficulty_label(subj['difficulty'])})",
                font=FONT_SMALL,
            ).pack(side="left", padx=10, pady=6)

    def _add_subject(self) -> None:
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Subject name cannot be empty.", parent=self)
            return
        add_subject(name, self.diff_var.get())
        self.name_entry.delete(0, "end")
        self._populate_list()
        self.refresh_cb()

class AddTaskDialog(ctk.CTkToplevel):
    def __init__(self, master, parsed, subjects, refresh_cb):
        super().__init__(master)
        self.title("Confirm New Task")
        self.geometry("480x360")
        self.resizable(False, False)
        self.grab_set()
        self.parsed = parsed
        self.subjects = subjects
        self.refresh_cb = refresh_cb
        self._saved = False
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Review & Confirm Task", font=FONT_HEAD).pack(pady=(20, 10))
        form = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        form.pack(fill="x", padx=20, pady=8)

        self._row(form, "Subject:")
        subject_names = [s["name"] for s in self.subjects]
        default_subject = self.parsed.subject or (subject_names[0] if subject_names else "")
        self.subject_var = ctk.StringVar(value=default_subject)
        ctk.CTkOptionMenu(
            form, values=subject_names, variable=self.subject_var,
        ).pack(fill="x", padx=16, pady=(0, 8))

        self._row(form, "Description:")
        self.desc_entry = ctk.CTkEntry(form, width=400)
        self.desc_entry.insert(0, self.parsed.description or self.parsed.raw)
        self.desc_entry.pack(fill="x", padx=16, pady=(0, 8))

        self._row(form, "Deadline (YYYY-MM-DD):")
        self.deadline_entry = ctk.CTkEntry(form, width=200)
        deadline_str = self.parsed.deadline.isoformat() if self.parsed.deadline else ""
        self.deadline_entry.insert(0, deadline_str)
        self.deadline_entry.pack(fill="x", padx=16, pady=(0, 12))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(
            btn_row, text="Save Task", command=self._save,
            fg_color=ACCENT, width=140,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row, text="Cancel", command=self.destroy,
            fg_color="#333", width=100,
        ).pack(side="left")

    def _row(self, parent, label: str) -> None:
        ctk.CTkLabel(parent, text=label, font=FONT_SMALL, text_color=TEXT_MUTED).pack(
            anchor="w", padx=16, pady=(8, 2)
        )

    def _save(self) -> None:
        subject_name = self.subject_var.get()
        desc = self.desc_entry.get().strip()
        deadline_str = self.deadline_entry.get().strip()

        subject_row = next(
            (s for s in self.subjects if s["name"] == subject_name), None
        )
        if not subject_row:
            messagebox.showerror("Error", "Please select a valid subject.", parent=self)
            return
        if not desc:
            messagebox.showerror("Error", "Description cannot be empty.", parent=self)
            return
        try:
            deadline_date = date.fromisoformat(deadline_str)
        except ValueError:
            messagebox.showerror(
                "Error", "Invalid date format. Use YYYY-MM-DD.", parent=self
            )
            return

        add_task(
            subject_id=subject_row["id"],
            description=desc,
            deadline=deadline_date,
        )
        self._saved = True
        self.refresh_cb()
        self.destroy()

class StudyPlannerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("📚 Student Study Planner")
        self.geometry("1100x700")
        self.minsize(900, 580)
        self.configure(fg_color=BG_PANEL)
        init_db()
        self._nlp_thread: Optional[threading.Thread] = None
        self._build_ui()
        self.refresh_dashboard()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, height=60, fg_color=BG_CARD, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📚 Study Planner",
            font=FONT_TITLE, text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=24, pady=12)

        ctk.CTkButton(
            header, text="⚙ Subjects", width=110,
            command=self._open_subject_manager,
            fg_color=BG_INPUT, hover_color="#2E2E4E",
        ).pack(side="right", padx=12)

        self.avoidance_btn = ctk.CTkButton(
            header, text="✅ All Clear", width=120,
            fg_color="#1A2B1A", hover_color="#1A2B1A",
            text_color="#4CAF50",
            state="disabled",
        )
        self.avoidance_btn.pack(side="right", padx=4)

        input_panel = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, height=70)
        input_panel.pack(fill="x", side="top")
        input_panel.pack_propagate(False)

        ctk.CTkLabel(
            input_panel, text="Add Task:",
            font=FONT_SMALL, text_color=TEXT_MUTED,
        ).pack(side="left", padx=(24, 8))

        self.nlp_entry = ctk.CTkEntry(
            input_panel,
            placeholder_text='e.g. "Physics assignment due next Friday" or "Math exam in 3 days"',
            width=600, font=FONT_BODY,
        )
        self.nlp_entry.pack(side="left", padx=(0, 10))
        self.nlp_entry.bind("<Return>", lambda _: self._on_nlp_submit())

        self.parse_btn = ctk.CTkButton(
            input_panel, text="Parse & Add ➜", width=130,
            command=self._on_nlp_submit,
            fg_color=ACCENT, hover_color="#5A4FD1",
        )
        self.parse_btn.pack(side="left")

        self.parse_status = ctk.CTkLabel(
            input_panel, text="", font=FONT_SMALL, text_color=TEXT_MUTED
        )
        self.parse_status.pack(side="left", padx=10)

        stats_bar = ctk.CTkFrame(self, height=32, fg_color=BG_PANEL, corner_radius=0)
        stats_bar.pack(fill="x", side="top")
        stats_bar.pack_propagate(False)

        self.stats_lbl = ctk.CTkLabel(
            stats_bar, text="Loading…",
            font=FONT_SMALL, text_color=TEXT_MUTED,
        )
        self.stats_lbl.pack(side="left", padx=24)

        ctk.CTkLabel(
            stats_bar,
            text="🟥 High  🟧 Medium  🟩 Low priority",
            font=FONT_SMALL, text_color=TEXT_MUTED,
        ).pack(side="right", padx=24)

        self.dashboard = ctk.CTkScrollableFrame(
            self, fg_color=BG_PANEL, corner_radius=0,
        )
        self.dashboard.pack(fill="both", expand=True, padx=16, pady=(8, 12))

    def refresh_dashboard(self) -> None:
        for widget in self.dashboard.winfo_children():
            widget.destroy()

        pending_rows = get_pending_tasks()
        ranked: list[TaskRecord] = rank_tasks(pending_rows)

        if not ranked:
            ctk.CTkLabel(
                self.dashboard,
                text="🎉  No pending tasks. Add one above!",
                font=FONT_HEAD, text_color=TEXT_MUTED,
            ).pack(pady=80)
        else:
            for record in ranked:
                card = TaskCard(
                    self.dashboard, record, refresh_cb=self.refresh_dashboard
                )
                card.pack(fill="x", padx=8, pady=4)

        total = len(ranked)
        overdue = sum(1 for r in ranked if r.is_overdue)
        self.stats_lbl.configure(
            text=f"{total} pending  •  {overdue} overdue"
        )

        recent_done = get_recently_completed_tasks(limit=5)
        alert = check_avoidance(recent_done, pending_rows)
        if alert:
            self.avoidance_btn.configure(
                text="⚠️ Avoidance!", state="normal",
                fg_color="#2B1A0A", text_color=COLOUR_MEDIUM,
                command=lambda: self._show_avoidance_alert(alert.message),
                hover_color="#3D2510",
            )
        else:
            self.avoidance_btn.configure(
                text="✅ All Clear", state="disabled",
                fg_color="#1A2B1A", text_color="#4CAF50",
                command=None,
            )

    def _show_avoidance_alert(self, message: str) -> None:
        messagebox.showwarning("Smart Reminder — Avoidance Detected", message)

    def _on_nlp_submit(self) -> None:
        raw = self.nlp_entry.get().strip()
        if not raw:
            return
        if self._nlp_thread and self._nlp_thread.is_alive():
            return

        self.parse_btn.configure(state="disabled", text="Parsing…")
        self.parse_status.configure(text="⏳ Analysing input…", text_color=TEXT_MUTED)

        self._nlp_thread = threading.Thread(
            target=self._nlp_worker, args=(raw,), daemon=True
        )
        self._nlp_thread.start()

    def _nlp_worker(self, raw: str) -> None:
        subjects = get_all_subjects()
        subject_names = [s["name"] for s in subjects]
        try:
            parsed = parse_task_input(raw, subject_names)
        except Exception as exc:
            self.after(0, self._nlp_error, str(exc))
            return
        self.after(0, self._nlp_done, parsed, subjects)

    def _nlp_done(self, parsed, subjects) -> None:
        self.parse_btn.configure(state="normal", text="Parse & Add ➜")
        if not parsed.is_complete():
            missing = []
            if not parsed.subject:
                missing.append("subject (add it in ⚙ Subjects first?)")
            if not parsed.deadline:
                missing.append("deadline date")
            self.parse_status.configure(
                text=f"⚠ Could not extract: {', '.join(missing)}",
                text_color=COLOUR_MEDIUM,
            )
        else:
            self.parse_status.configure(text="✔ Parsed!", text_color=COLOUR_LOW)

        self.nlp_entry.delete(0, "end")
        dlg = AddTaskDialog(self, parsed, subjects, refresh_cb=self.refresh_dashboard)
        dlg.wait_window()
        self.parse_status.configure(text="")

    def _nlp_error(self, msg: str) -> None:
        self.parse_btn.configure(state="normal", text="Parse & Add ➜")
        self.parse_status.configure(text=f"❌ Error: {msg}", text_color=COLOUR_HIGH)

    def _open_subject_manager(self) -> None:
        dlg = SubjectManager(self, refresh_cb=self.refresh_dashboard)
        dlg.wait_window()

def main() -> None:
    app = StudyPlannerApp()
    app.mainloop()

if __name__ == "__main__":
    main()