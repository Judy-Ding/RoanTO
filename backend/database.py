import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from backend.schemas import MISSION_BY_ID, PlanDraft, PlanRecord, Preferences, SavedPlanContent, SavedStep


DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "roamto.db"
DEMO_PLAN_TEMPLATES = (
    {
        "mission_id": "ttc-first-trip",
        "goal": "Plan a first TTC trip",
        "overview": "Use official TTC tools to prepare for a trip that feels manageable.",
        "steps": [
            {"title": "Choose a destination", "details": "Pick a place you want to visit and note its address or nearest intersection."},
            {"title": "Check the route", "details": "Use the TTC trip planner or another route-planning tool to compare options from your starting point."},
            {"title": "Review trip details", "details": "Before leaving, confirm the route, service notices, fare options, and any accessibility details on official TTC pages."},
        ],
        "practical_tips": ["Save the destination and route details somewhere easy to check during your trip."],
        "resources": [
            {"title": "TTC trip planner", "url": "https://www.ttc.ca/trip-planner"},
            {"title": "TTC fares and passes", "url": "https://www.ttc.ca/Fares-and-passes"},
        ],
        "verify_before_you_go": ["Confirm current routes, service notices, fares, and accessibility details with the TTC."],
    },
    {
        "mission_id": "library-start",
        "goal": "Explore Toronto Public Library services",
        "overview": "Learn what the library offers and find out how to use services near you.",
        "steps": [
            {"title": "Explore library services", "details": "Browse the Toronto Public Library website and note the services or programs you would like to try."},
            {"title": "Find a convenient branch", "details": "Use the library's branch finder to locate a branch that works for your location and schedule."},
            {"title": "Check how to get started", "details": "Review the library card requirements and what to bring, then contact or visit a branch if you have questions."},
        ],
        "practical_tips": ["Write down any questions about membership or services before contacting the library."],
        "resources": [
            {"title": "Toronto Public Library", "url": "https://www.torontopubliclibrary.ca/"},
            {"title": "Library cards", "url": "https://www.torontopubliclibrary.ca/using-the-library/your-library-card/"},
        ],
        "verify_before_you_go": ["Confirm current library card requirements, branch hours, and service availability with the library."],
    },
    {
        "mission_id": "toronto-on-a-budget",
        "goal": "Find an activity in Toronto that fits your budget",
        "overview": "Use City of Toronto and public library resources to find an activity that suits your interests.",
        "steps": [
            {"title": "Choose an activity type", "details": "Pick something you would enjoy, such as a park visit, public event, exhibit, or library program."},
            {"title": "Search official listings", "details": "Browse the City of Toronto and Toronto Public Library websites for options in an area and time that work for you."},
            {"title": "Plan the visit", "details": "Check the activity's cost, registration details, location, hours, and how to get there before making plans."},
        ],
        "practical_tips": ["Keep a backup activity in mind in case your first choice is full or unavailable."],
        "resources": [
            {"title": "City of Toronto: Explore and enjoy", "url": "https://www.toronto.ca/explore-enjoy/"},
            {"title": "Toronto Public Library", "url": "https://www.torontopubliclibrary.ca/"},
        ],
        "verify_before_you_go": ["Confirm current costs, registration requirements, hours, and availability with the activity organizer."],
    },
    {
        "mission_id": "community-activity",
        "goal": "Explore a community activity",
        "overview": "Find a local activity that interests you and learn how to take part.",
        "steps": [
            {"title": "Pick an area of interest", "details": "Think about an activity you might enjoy, such as recreation, arts, or a library program."},
            {"title": "Browse local listings", "details": "Check City of Toronto recreation listings and Toronto Public Library programs for options."},
            {"title": "Check participation details", "details": "Review the location, schedule, cost, registration steps, and any participation requirements with the organizer."},
        ],
        "practical_tips": ["If you are unsure whether a program is a good fit, contact the organizer before registering."],
        "resources": [
            {"title": "City of Toronto: Community recreation", "url": "https://www.toronto.ca/explore-enjoy/recreation/"},
            {"title": "Toronto Public Library programs", "url": "https://www.torontopubliclibrary.ca/programs-and-classes/"},
        ],
        "verify_before_you_go": ["Confirm current schedules, costs, registration requirements, and availability with the program organizer."],
    },
)


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
                is_demo INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(plans)").fetchall()
        }
        if "is_demo" not in columns:
            connection.execute(
                "ALTER TABLE plans ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS plans_user_updated ON plans(user_id, updated_at DESC)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS demo_plan_seeds (
                user_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
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
        is_demo=bool(row["is_demo"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _insert_plan(
    connection: sqlite3.Connection,
    draft: PlanDraft,
    user_id: str,
    is_demo: bool = False,
) -> sqlite3.Row:
    plan_id = str(uuid.uuid4())
    data = draft.model_dump(mode="json")
    data["content"]["steps"] = [
        {**step, "completed": False} for step in data["content"]["steps"]
    ]
    connection.execute(
        """
        INSERT INTO plans (id, user_id, mission_id, plan_json, is_demo)
        VALUES (?, ?, ?, ?, ?)
        """,
        (plan_id, user_id, draft.mission_id, json.dumps(data), int(is_demo)),
    )
    row = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return row


def create_plan(draft: PlanDraft, user_id: str) -> PlanRecord:
    with _connect() as connection:
        row = _insert_plan(connection, draft, user_id)
    return _to_record(row)


def ensure_demo_plans(user_id: str) -> None:
    with _connect() as connection:
        inserted = connection.execute(
            "INSERT OR IGNORE INTO demo_plan_seeds (user_id) VALUES (?)",
            (user_id,),
        ).rowcount
        if not inserted:
            return
        for template in DEMO_PLAN_TEMPLATES:
            draft = PlanDraft(
                mission_id=template["mission_id"],
                preferences=Preferences(),
                content={key: value for key, value in template.items() if key != "mission_id"},
            )
            _insert_plan(connection, draft, user_id, is_demo=True)


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
