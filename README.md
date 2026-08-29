# 📚 AI-Based Student Study Planner

> A smart desktop study planner that uses **Natural Language Processing (NLP)** to create tasks from natural language, dynamically prioritizes them based on difficulty and deadlines, and detects when you may be avoiding difficult tasks.

## ✨ Overview

**AI-Based Student Study Planner** is a desktop productivity application designed specifically for students.

Instead of manually entering every task detail, you can simply type something like:

```text
Physics assignment due next Friday
```

The application uses **spaCy NLP** and custom date parsing to extract:

* 📘 Subject
* 📝 Task description
* 📅 Deadline

It then calculates a **Priority Score** for each task using difficulty, urgency, and progress, allowing the most important work to appear first.

The application also includes an **Avoidance Detection** mechanism that identifies when a student repeatedly completes easy tasks while leaving difficult, high-priority tasks unfinished.

---

## 🎯 Problem Statement

Students often struggle with:

* Deciding which assignment to work on first
* Underestimating approaching deadlines
* Spending too much time on easy tasks
* Procrastinating on difficult subjects
* Manually maintaining complicated study schedules

Traditional to-do lists treat every task equally.

This project attempts to solve that problem by making the planner **deadline-aware, difficulty-aware, and behavior-aware**.

---

## 🚀 Features

### 🧠 Natural Language Task Creation

Tasks can be entered using normal language rather than filling out multiple fields.

Examples:

```text
Physics lab due next Friday
Math exam in 3 days
History essay due tomorrow
Chemistry assignment due April 25
Biology report 2026-09-15
```

The NLP pipeline extracts the relevant information and presents it for confirmation before saving.

Supported date expressions include:

* `today`
* `tomorrow`
* `next week`
* `this week`
* `next Monday`
* `this Friday`
* `in 3 days`
* `in 2 weeks`
* `April 25`
* `25 April`
* `2026-09-15`

---

### 📊 Dynamic Priority Index

Every pending task receives a priority score.

The current scoring formula is:

```text
Priority Score =
    (Difficulty × 0.4)
    + (Urgency × 0.5)
    − (Progress Ratio × 0.1)
    + Overdue Bonus
```

Where:

```text
Urgency = 10 / (Days Remaining + 1)
```

And:

```text
Progress Ratio =
    Time Spent / Expected Hours
```

The progress ratio is capped at `1.0`.

Overdue tasks receive an additional:

```text
+3.0
```

priority bonus.

### Priority colours

|    Score | Priority  |
| -------: | --------- |
|    `≥ 7` | 🔴 High   |
| `4 – <7` | 🟠 Medium |
|     `<4` | 🟢 Low    |

This means a difficult task with an approaching deadline naturally rises above less important work.

---

## 🧮 Difficulty-Based Work Estimation

Each subject has a difficulty rating from **1–10**.

The planner uses the following expected study times:

| Difficulty | Expected Hours |
| ---------: | -------------: |
|          1 |           1.0h |
|          2 |           1.5h |
|          3 |           2.0h |
|          4 |           3.0h |
|          5 |           4.0h |
|          6 |           5.0h |
|          7 |           7.0h |
|          8 |          10.0h |
|          9 |          12.0h |
|         10 |          15.0h |

These estimates are used to calculate task progress.

For example:

```text
Difficulty = 8
Expected Hours = 10
Time Spent = 4 hours

Progress Ratio = 4 / 10 = 0.4
```

---

## ⚠️ Avoidance Detection

One of the project's main features is detecting the **Comfort Zone Trap**.

The planner examines the most recently completed tasks.

An avoidance alert is triggered when:

1. At least **3 recent tasks** have been completed.
2. The recent tasks are easy (`difficulty ≤ 4`).
3. A difficult task exists (`difficulty ≥ 7`).
4. That difficult task is either:

   * Overdue, or
   * Has a priority score of at least `5`.

When detected, the application displays an:

```text
⚠️ Avoidance Alert!
```

The reminder encourages the student to tackle one of the difficult tasks instead of continuing to complete easier work.

---

## ⏱️ Time Tracking

Time can be logged against individual tasks.

For example:

```text
2.5 hours
```

The logged time is added to the task's existing `time_spent` value.

This affects the task's progress ratio and therefore its priority.

---

## 📌 Task Status

Every task can have one of three statuses:

```text
pending
in_progress
done
```

Completed tasks are removed from the active dashboard but remain stored in the database for avoidance analysis.

---

## 📚 Subject Management

Subjects can be added through the built-in subject manager.

Each subject has:

```text
Subject Name
Difficulty: 1–10
```

The application comes pre-seeded with:

* Mathematics — 9
* Physics — 8
* Chemistry — 7
* History — 5
* English — 4
* Biology — 6
* Computer Science — 8
* Geography — 4

Custom subjects can also be added.

---

## 🖥️ User Interface

The application uses a dark-themed desktop interface built with **CustomTkinter**.

The main dashboard provides:

* Pending task count
* Overdue task count
* Colour-coded priority
* Subject difficulty
* Deadline information
* Logged study time
* Priority score
* Task status controls
* Time logging
* Task deletion
* NLP task creation
* Subject management
* Avoidance alerts

---

## 🏗️ Architecture

The project follows a simple modular architecture:

```text
┌──────────────────────────────┐
│        CustomTkinter UI      │
│            app.py            │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌──────────────┐  ┌────────────────┐
│  NLP Module  │  │ Planner Logic  │
│ nlp_utils.py │  │planner_logic.py│
└──────┬───────┘  └───────┬────────┘
       │                  │
       │                  │
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │   Database Layer │
       │   database.py    │
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │     SQLite DB    │
       │    planner.db    │
       └──────────────────┘
```

### Module Responsibilities

#### `app.py`

Responsible for:

* Application window
* Dashboard
* Task cards
* Subject manager
* Add-task dialog
* User interaction
* Background NLP processing

#### `nlp_utils.py`

Responsible for:

* spaCy model loading
* Subject extraction
* Date extraction
* Relative date parsing
* Description cleaning
* Parsed task representation

#### `planner_logic.py`

Responsible for:

* Priority calculation
* Task ranking
* Progress calculation
* Difficulty classification
* Overdue detection
* Avoidance detection

#### `database.py`

Responsible for:

* SQLite connection
* Database initialization
* Subject CRUD operations
* Task CRUD operations
* Task status updates
* Time tracking
* Recently completed task retrieval

---

## 🗄️ Database Schema

The application uses SQLite and automatically creates the database on first launch.

### `subjects`

```text
subjects
├── id
├── name
└── difficulty
```

### `tasks`

```text
tasks
├── id
├── subject_id
├── description
├── deadline
├── status
├── time_spent
└── created_at
```

The relationship is:

```text
subjects
    │
    │ 1
    │
    │ N
    ▼
  tasks
```

Deleting a subject also deletes its associated tasks through SQLite's foreign-key cascade.

---

## 🛠️ Tech Stack

| Technology              | Purpose                     |
| ----------------------- | --------------------------- |
| **Python**              | Core application            |
| **CustomTkinter**       | Desktop GUI                 |
| **spaCy**               | NLP processing              |
| **SQLite**              | Local database              |
| **Threading**           | Non-blocking NLP processing |
| **Regular Expressions** | Date and subject extraction |

---

## 📁 Project Structure

```text
NLP - AI Based Study Planner/
│
├── app.py
├── database.py
├── nlp_utils.py
├── planner_logic.py
├── planner.db
├── requirements.txt
└── README.md
```

> `planner.db` is created automatically if it does not already exist.

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/ai-study-planner.git
cd ai-study-planner
```

### 2. Create a virtual environment

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install customtkinter spacy
```

Or, if `requirements.txt` is included:

```bash
pip install -r requirements.txt
```

### 4. Download the spaCy model

```bash
python -m spacy download en_core_web_sm
```

### 5. Run the application

```bash
python app.py
```

---

## 📦 Requirements

A suitable `requirements.txt` is:

```text
customtkinter
spacy
```

The spaCy English model must additionally be installed with:

```bash
python -m spacy download en_core_web_sm
```

---

## 🔄 Application Workflow

```text
User enters natural-language task
             │
             ▼
       spaCy NLP Parser
             │
       ┌─────┴─────┐
       ▼           ▼
   Subject      Deadline
       │           │
       └─────┬─────┘
             ▼
       Task Confirmation
             │
             ▼
        SQLite Storage
             │
             ▼
     Priority Calculation
             │
             ▼
       Task Ranking
             │
             ▼
       Dashboard Display
             │
             ▼
      User Logs Progress
             │
             ▼
      Priority Recalculated
```

---

## 💡 Example

Suppose the user enters:

```text
Physics assignment due tomorrow
```

The NLP system identifies:

```text
Subject: Physics
Deadline: Tomorrow
Description: assignment
```

If Physics has difficulty `8` and the task has no logged progress:

```text
Difficulty Component = 8 × 0.4 = 3.2

Urgency Component = 10 / (1 + 1) × 0.5 = 2.5

Progress Component = 0 × 0.1 = 0
```

Therefore:

```text
Priority Score = 3.2 + 2.5
               = 5.7
```

The task is consequently classified as **Medium Priority**.

As the deadline approaches, its urgency increases and the task can move into the high-priority category.

---

## 🧠 Design Goals

The project is based around two behavioural problems:

### 1. Planning Fallacy

Students often underestimate how much time difficult academic tasks require.

The planner addresses this by assigning expected study hours based on difficulty.

### 2. Comfort Zone Trap

Students may repeatedly complete easy tasks because they provide quick feelings of progress while difficult tasks remain untouched.

The avoidance detector attempts to identify this behaviour and provide a timely reminder.

---

## 🔒 Privacy

The application is designed as a **local desktop application**.

Task information is stored in a local SQLite database:

```text
planner.db
```

No external server is required for normal operation.

The NLP processing is performed locally using the installed spaCy model.

---

## ⚠️ Current Limitations

This project is intentionally lightweight and has several areas that could be improved.

### NLP limitations

Subject detection currently relies heavily on matching known subject names in the input.

For example:

```text
Physics assignment due Friday
```

works well, but unusual phrasing or synonyms may not always identify the intended subject.

### Date parsing

The application supports many common date expressions, but it is not a complete natural-language date parser.

### Study-time estimation

Expected hours are currently predefined based on difficulty rather than learned from the student's historical performance.

### Behaviour detection

Avoidance detection uses a fixed rule:

```text
3 easy completed tasks
+
critical hard pending task
```

A future version could learn individual study patterns.

---

## 🔮 Future Improvements

Potential improvements include:

* 🤖 Personalized study-time prediction
* 📈 Study productivity analytics
* 📅 Calendar integration
* 🔔 Deadline notifications
* 📊 Weekly/monthly progress charts
* 🧠 More advanced NLP task extraction
* 🎯 Personalized priority weights
* 📚 Semester/course management
* ☁️ Optional cloud synchronization
* 📱 Mobile companion application
* 🏆 Gamification and study streaks
* 📌 Recurring tasks
* 🗓️ Automatic daily study schedules
* 🧑‍🎓 Student-specific difficulty estimation
* 📉 Historical performance analysis

---

## 🎓 Academic Concepts Demonstrated

This project combines several software and AI concepts:

* Natural Language Processing
* Named Entity Recognition
* Rule-based NLP
* Priority algorithms
* Behavioural heuristics
* CRUD operations
* Relational database design
* GUI development
* Multithreading
* Data modelling
* Algorithmic task ranking

---

## 👨‍💻 Project

**AI-Based Student Study Planner**

Built as an academic/project implementation demonstrating how NLP and rule-based decision systems can be integrated into a practical student productivity application.

---

## ⭐ Contributing

Contributions and improvements are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/new-feature
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push the branch

```bash
git push origin feature/new-feature
```

5. Open a Pull Request

---

## 📄 License

Add your preferred license here, for example:

```text
MIT License
```

If this is an academic submission, make sure the license matches your institution's requirements.
