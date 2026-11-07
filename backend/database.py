import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from backend.schemas import MISSION_BY_ID, PlanDraft, PlanRecord, SavedPlanContent, SavedStep


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "roamto.db"


def _database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE))).expanduser()


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                mission_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS plans_user_updated ON plans(user_id, updated_at DESC)"
        )


def _to_record(row: sqlite3.Row) -> PlanRecord:
    data: dict[str, Any] = json.loads(row["plan_json"])
    content = data["content"]
    content["steps"] = [SavedStep.model_validate(step).model_dump() for step in content["steps"]]
    mission_title = (
        data["custom_goal"]
        if row["mission_id"] == "custom"
        else MISSION_BY_ID[row["mission_id"]]["title"]
    )
    category = "Custom" if row["mission_id"] == "custom" else MISSION_BY_ID[row["mission_id"]]["category"]
    return PlanRecord(
        id=row["id"],
        user_id=row["user_id"],
        mission_id=row["mission_id"],
        mission_title=mission_title,
        category=category,
        preferences=data["preferences"],
        content=SavedPlanContent.model_validate(content),
        mission_completed=bool(row["mission_completed"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_plan(draft: PlanDraft, user_id: str) -> PlanRecord:
    plan_id = str(uuid.uuid4())
    data = draft.model_dump(mode="json")
    data["content"]["steps"] = [
        {**step, "completed": False} for step in data["content"]["steps"]
    ]
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO plans (id, user_id, mission_id, plan_json)
            VALUES (?, ?, ?, ?)
            """,
            (plan_id, user_id, draft.mission_id, json.dumps(data)),
        )
        row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return _to_record(row)


def get_plan(plan_id: str, user_id: str) -> PlanRecord | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
        ).fetchone()
    return _to_record(row) if row else None


def list_plans(user_id: str) -> list[PlanRecord]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM plans WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
            (user_id,),
        ).fetchall()
    return [_to_record(row) for row in rows]


def set_step_completion(
    plan_id: str,
    step_index: int,
    completed: bool,
    user_id: str,
) -> PlanRecord | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row["plan_json"])
        if step_index < 0 or step_index >= len(data["content"]["steps"]):
            raise IndexError("Step index is out of range.")
        data["content"]["steps"][step_index]["completed"] = completed
        connection.execute(
            "UPDATE plans SET plan_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(data), plan_id),
        )
        updated = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return _to_record(updated)


def set_mission_completion(plan_id: str, completed: bool, user_id: str) -> PlanRecord | None:
    with _connect() as connection:
        connection.execute(
            """
            UPDATE plans
            SET mission_completed = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (int(completed), plan_id, user_id),
        )
        row = connection.execute(
            "SELECT * FROM plans WHERE id = ? AND user_id = ?",
            (plan_id, user_id),
        ).fetchone()
    return _to_record(row) if row else None
