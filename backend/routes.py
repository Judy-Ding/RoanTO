from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from backend import ai_service, auth, database
from backend.schemas import (
    MISSIONS,
    MISSION_BY_ID,
    GenerateRequest,
    MissionCompletion,
    ModifyRequest,
    PlanDraft,
    PlanRecord,
    StepCompletion,
)


router = APIRouter()
CurrentUser = Annotated[dict[str, Any], Depends(auth.require_user)]


@router.get("/api/missions")
def list_missions():
    return MISSIONS


@router.get("/api/auth/config")
def get_auth_config():
    return auth.firebase_client_config()


@router.post("/api/plans/generate", response_model=PlanDraft)
async def generate_plan(request: GenerateRequest, _: CurrentUser):
    if request.mission_id != "custom" and request.mission_id not in MISSION_BY_ID:
        raise HTTPException(status_code=404, detail="Mission not found.")
    if request.mission_id == "custom" and not request.custom_goal:
        raise HTTPException(status_code=422, detail="Enter a goal for your custom plan.")
    if request.mission_id != "custom" and request.custom_goal:
        raise HTTPException(status_code=422, detail="Custom goals require the custom mission option.")
    return await ai_service.generate_plan(
        request.mission_id,
        request.preferences,
        request.custom_goal,
    )


@router.post("/api/plans/modify", response_model=PlanDraft)
async def modify_plan(request: ModifyRequest, _: CurrentUser):
    if request.plan.mission_id != "custom" and request.plan.mission_id not in MISSION_BY_ID:
        raise HTTPException(status_code=404, detail="Mission not found.")
    if request.plan.mission_id == "custom" and not request.plan.custom_goal:
        raise HTTPException(status_code=422, detail="The custom plan is missing its goal.")
    return await ai_service.modify_plan(request.plan, request.request)


@router.post("/api/plans", response_model=PlanRecord, status_code=201)
def save_plan(plan: PlanDraft, user: CurrentUser):
    if plan.mission_id != "custom" and plan.mission_id not in MISSION_BY_ID:
        raise HTTPException(status_code=404, detail="Mission not found.")
    if plan.mission_id == "custom" and not plan.custom_goal:
        raise HTTPException(status_code=422, detail="The custom plan is missing its goal.")
    return database.create_plan(plan, user["uid"])


@router.get("/api/plans", response_model=list[PlanRecord])
def list_saved_plans(user: CurrentUser):
    return database.list_plans(user["uid"])


@router.post("/api/plans/demo-seed", response_model=list[PlanRecord])
def seed_demo_plans(user: CurrentUser):
    database.ensure_demo_plans(user["uid"])
    return database.list_plans(user["uid"])


@router.get("/api/plans/{plan_id}", response_model=PlanRecord)
def retrieve_plan(plan_id: str, user: CurrentUser):
    plan = database.get_plan(plan_id, user["uid"])
    if plan is None:
        raise HTTPException(status_code=404, detail="Saved plan not found.")
    return plan


@router.patch("/api/plans/{plan_id}/steps/{step_index}", response_model=PlanRecord)
def update_step(plan_id: str, step_index: int, request: StepCompletion, user: CurrentUser):
    try:
        plan = database.set_step_completion(plan_id, step_index, request.completed, user["uid"])
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Plan step not found.") from exc
    if plan is None:
        raise HTTPException(status_code=404, detail="Saved plan not found.")
    return plan


@router.patch("/api/plans/{plan_id}/complete", response_model=PlanRecord)
def complete_mission(plan_id: str, request: MissionCompletion, user: CurrentUser):
    plan = database.set_mission_completion(plan_id, request.completed, user["uid"])
    if plan is None:
        raise HTTPException(status_code=404, detail="Saved plan not found.")
    return plan
