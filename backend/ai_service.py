import json
import os
import re
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from backend.schemas import MISSION_BY_ID, PlanContent, PlanDraft, Preferences


RESOURCE_CATALOG = {
    "ttc-first-trip": [
        {"title": "Toronto Transit Commission", "url": "https://www.ttc.ca/"},
        {"title": "TTC fares and passes", "url": "https://www.ttc.ca/Fares-and-passes"},
    ],
    "library-start": [
        {"title": "Toronto Public Library", "url": "https://www.torontopubliclibrary.ca/"},
        {"title": "Library cards", "url": "https://www.torontopubliclibrary.ca/using-the-library/your-library-card/"},
    ],
    "toronto-on-a-budget": [
        {"title": "City of Toronto: Things to do", "url": "https://www.toronto.ca/explore-enjoy/"},
        {"title": "Toronto Public Library", "url": "https://www.torontopubliclibrary.ca/"},
    ],
    "community-activity": [
        {"title": "City of Toronto: Community recreation", "url": "https://www.toronto.ca/explore-enjoy/recreation/"},
        {"title": "Toronto Public Library events", "url": "https://www.torontopubliclibrary.ca/programs-and-classes/"},
    ],
    "plan-ttc-commute": [
        {"title": "TTC trip planner", "url": "https://www.ttc.ca/trip-planner"},
        {"title": "Toronto Transit Commission", "url": "https://www.ttc.ca/"},
    ],
    "presto-basics": [
        {"title": "PRESTO", "url": "https://www.prestocard.ca/"},
        {"title": "TTC fares and passes", "url": "https://www.ttc.ca/Fares-and-passes"},
    ],
    "find-health-care": [
        {"title": "Health Care Connect", "url": "https://www.ontario.ca/page/find-family-doctor-or-nurse-practitioner"},
        {"title": "211 Ontario", "url": "https://211ontario.ca/"},
    ],
    "newcomer-services": [
        {"title": "City of Toronto: Newcomer services", "url": "https://www.toronto.ca/community-people/moving-to-toronto/newcomers/"},
        {"title": "211 Ontario", "url": "https://211ontario.ca/"},
    ],
    "explore-neighbourhood": [
        {"title": "City of Toronto: Explore and enjoy", "url": "https://www.toronto.ca/explore-enjoy/"},
        {"title": "Toronto Public Library", "url": "https://www.torontopubliclibrary.ca/"},
    ],
    "free-city-activities": [
        {"title": "City of Toronto: Things to do", "url": "https://www.toronto.ca/explore-enjoy/"},
        {"title": "Toronto Public Library events", "url": "https://www.torontopubliclibrary.ca/programs-and-classes/"},
    ],
    "volunteer-toronto": [
        {"title": "Volunteer Toronto", "url": "https://www.volunteertoronto.ca/"},
        {"title": "City of Toronto: Volunteer", "url": "https://www.toronto.ca/community-people/get-involved/volunteer-with-the-city/"},
    ],
    "meet-neighbours": [
        {"title": "City of Toronto: Community recreation", "url": "https://www.toronto.ca/explore-enjoy/recreation/"},
        {"title": "Toronto Public Library events", "url": "https://www.torontopubliclibrary.ca/programs-and-classes/"},
    ],
}

SYSTEM_PROMPT = """You are RoamTO, a practical and welcoming guide for newcomers to Toronto.
Return only one JSON object with these exact keys:
goal (string), overview (string), steps (array of 3-5 objects with title and details),
practical_tips (array of strings), resources (array of 0-5 objects with title and url),
verify_before_you_go (array of strings).
Make steps specific, sequential, and actionable for this person's situation. Avoid assumptions
about immigration status, accessibility, or familiarity with Canadian systems. Use only the
official resource URLs supplied in the user message, and include relevant ones when useful.
Do not claim to have checked current transit schedules, business hours, prices, eligibility, or
service availability. Clearly tell the user what details to verify and where. Do not invent
current facts. Keep the guidance useful even if an official resource is not listed.

For Explore missions and requests for an outing or itinerary, organize the steps as a practical
sequence of suggested stops. Include an approximate activity duration (not a schedule or travel
time), a clearly labeled rough cost estimate in CAD when reasonably supportable, a transportation
suggestion, and a short reason each stop fits the user's interests. Never invent exact prices;
when uncertain, say to check the venue's current price. Treat all recommendations as suggestions.
Do not invent opening hours, transit schedules, or exact travel times."""


def _settings() -> tuple[str, str, str]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI setup required: add your GroqCloud API key as GROQ_API_KEY in the "
                "project's .env file, then restart RoamTO."
            ),
        )
    base_url = "https://api.groq.com/openai/v1"
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    if not model:
        raise HTTPException(status_code=503, detail="AI setup required: configure GROQ_MODEL.")
    return api_key, base_url, model


def _decode_content(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="The AI provider returned invalid JSON. Please try again.") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=502, detail="The AI provider returned an invalid plan. Please try again.")
    return decoded


async def _request_plan(user_prompt: str) -> PlanContent:
    api_key, base_url, model = _settings()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "temperature": 0.4,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Groq took too long to respond. Please try again.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Groq usage limit reached or requests are arriving too quickly. "
                    "Wait for the limit to refresh, then try again. Check your Groq Console "
                    "Limits page to see the current quota and reset time."
                ),
            ) from exc
        if exc.response.status_code in (401, 403):
            raise HTTPException(
                status_code=503,
                detail="Groq authentication failed. Check GROQ_API_KEY in your .env file.",
            ) from exc
        if exc.response.status_code >= 500:
            raise HTTPException(
                status_code=503,
                detail="Groq is temporarily unstable or unavailable. Please wait a moment and try again.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Groq could not process the request. Check the configured model and try again.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Could not connect to Groq. Please try again.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Groq returned an unreadable response.") from exc

    try:
        raw_content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Groq's response did not contain a plan.") from exc
    if not isinstance(raw_content, str):
        raise HTTPException(status_code=502, detail="Groq returned an invalid plan response.")
    decoded = _decode_content(raw_content)
    try:
        return PlanContent.model_validate(decoded)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq's response did not meet the required plan format. Please try again.",
        ) from exc


def _context(
    mission_id: str,
    preferences: Preferences,
    custom_goal: str | None = None,
) -> dict[str, Any]:
    if mission_id == "custom":
        if not custom_goal or not custom_goal.strip():
            raise HTTPException(status_code=422, detail="Enter a goal for your custom plan.")
        return {
            "mission": {
                "id": "custom",
                "title": custom_goal.strip(),
                "category": "Custom",
                "description": "A goal described by the user.",
            },
            "preferences": preferences.model_dump(),
            "official_resource_catalog": [],
        }
    mission = MISSION_BY_ID.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found.")
    return {
        "mission": mission,
        "preferences": preferences.model_dump(),
        "official_resource_catalog": RESOURCE_CATALOG.get(mission_id, []),
    }


async def generate_plan(
    mission_id: str,
    preferences: Preferences,
    custom_goal: str | None = None,
) -> PlanDraft:
    context = _context(mission_id, preferences, custom_goal)
    prompt = (
        "Create a personalized newcomer action plan from this context. "
        "Treat blank preferences as unknown rather than guessing.\n"
        + json.dumps(context, ensure_ascii=False)
    )
    content = await _request_plan(prompt)
    return PlanDraft(
        mission_id=mission_id,
        custom_goal=custom_goal.strip() if custom_goal else None,
        preferences=preferences,
        content=content,
    )


async def modify_plan(plan: PlanDraft, request: str) -> PlanDraft:
    context = _context(plan.mission_id, plan.preferences, plan.custom_goal)
    prompt = (
        "Revise the existing plan to honor the user's change request. Preserve useful details, "
        "update any affected steps, and return a complete valid plan in the required JSON shape.\n"
        f"Context: {json.dumps(context, ensure_ascii=False)}\n"
        f"Current plan: {plan.content.model_dump_json()}\n"
        f"User request: {request}"
    )
    content = await _request_plan(prompt)
    return PlanDraft(
        mission_id=plan.mission_id,
        custom_goal=plan.custom_goal,
        preferences=plan.preferences,
        content=content,
    )
