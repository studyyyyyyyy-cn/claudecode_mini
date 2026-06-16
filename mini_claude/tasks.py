"""Task tracking system — create, list, update tasks with JSON file persistence.
Mirrors Claude Code's TaskCreate/TaskList/TaskUpdate tools."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

# ─── Types ──────────────────────────────────────────────────

VALID_STATUSES = {"pending", "in_progress", "completed", "deleted"}


class TaskEntry:
    __slots__ = ("id", "subject", "description", "status", "created_at", "updated_at")

    def __init__(
        self,
        id: str,
        subject: str,
        description: str = "",
        status: str = "pending",
        created_at: str = "",
        updated_at: str = "",
    ):
        self.id = id
        self.subject = subject
        self.description = description
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at


# ─── Paths ──────────────────────────────────────────────────


def _project_hash() -> str:
    return hashlib.sha256(str(Path.cwd()).encode()).hexdigest()[:16]


def get_tasks_dir() -> Path:
    d = Path.home() / ".mini-claude" / "projects" / _project_hash() / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _task_path(task_id: str) -> Path:
    return get_tasks_dir() / f"{task_id}.json"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ─── CRUD ───────────────────────────────────────────────────


def create_task(subject: str, description: str = "") -> str:
    """Create a new task. Returns the task ID."""
    task_id = uuid.uuid4().hex[:8]
    now = _now_iso()
    entry = TaskEntry(
        id=task_id,
        subject=subject,
        description=description,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    _save_entry(entry)
    return task_id


def list_tasks(include_deleted: bool = False) -> list[TaskEntry]:
    """List all tasks, sorted by creation time (newest first)."""
    d = get_tasks_dir()
    entries: list[TaskEntry] = []
    for f in sorted(d.glob("*.json")):
        try:
            entry = _load_entry(f)
            if entry and (include_deleted or entry.status != "deleted"):
                entries.append(entry)
        except Exception:
            pass
    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    subject: str | None = None,
    description: str | None = None,
) -> bool:
    """Update a task's fields. Returns True if the task was found and updated."""
    path = _task_path(task_id)
    if not path.exists():
        return False

    entry = _load_entry(path)
    if not entry:
        return False

    if status is not None:
        if status not in VALID_STATUSES:
            return False
        entry.status = status
    if subject is not None:
        entry.subject = subject
    if description is not None:
        entry.description = description

    entry.updated_at = _now_iso()
    _save_entry(entry)
    return True


# ─── Internal helpers ────────────────────────────────────────


def _save_entry(entry: TaskEntry) -> None:
    data = {
        "id": entry.id,
        "subject": entry.subject,
        "description": entry.description,
        "status": entry.status,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    _task_path(entry.id).write_text(json.dumps(data, indent=2))


def _load_entry(path: Path) -> TaskEntry | None:
    try:
        data = json.loads(path.read_text())
        return TaskEntry(
            id=data["id"],
            subject=data["subject"],
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
    except Exception:
        return None
