import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "productivity.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'normal',
            created_at TEXT DEFAULT (datetime('now')),
            due_date TEXT
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            purpose TEXT,
            meeting_time TEXT,
            participants TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

# ── Task helpers ──────────────────────────────────────────
def db_add_task(task: str, priority: str = "normal", due_date: str = None) -> dict:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (task, priority, due_date) VALUES (?, ?, ?)",
        (task, priority, due_date)
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return {"id": task_id, "task": task, "priority": priority, "due_date": due_date}

def db_get_tasks(status: str = None) -> list:
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_complete_task(task_id: int) -> dict:
    conn = get_conn()
    conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"message": f"Task {task_id} marked as done"}

def db_delete_task(task_id: int) -> dict:
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"message": f"Task {task_id} deleted"}

# ── Note helpers ──────────────────────────────────────────
def db_save_note(content: str, title: str = None, tags: str = None) -> dict:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
        (title, content, tags)
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return {"id": note_id, "title": title, "content": content}

def db_get_notes(search: str = None) -> list:
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT * FROM notes WHERE content LIKE ? OR title LIKE ? ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Meeting helpers ───────────────────────────────────────
def db_save_meeting(title: str, purpose: str = None, meeting_time: str = None, participants: str = None) -> dict:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO meetings (title, purpose, meeting_time, participants) VALUES (?, ?, ?, ?)",
        (title, purpose, meeting_time, participants)
    )
    conn.commit()
    meeting_id = cur.lastrowid
    conn.close()
    return {"id": meeting_id, "title": title, "meeting_time": meeting_time}

def db_get_meetings() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM meetings ORDER BY meeting_time ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
