import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend import ai_service, auth
from backend.routes import router


PLAN_CONTENT = {
    "goal": "Explore Toronto on a budget",
    "overview": "A relaxed set of suggested stops based on your interests and budget.",
    "steps": [
        {"title": "Stop 1: Visit a public park", "details": "Spend about an hour here; estimated cost: free. Walk or use local transit. This suits your interest in outdoor sightseeing."},
        {"title": "Stop 2: Browse a library program", "details": "Allow about an hour; check current costs and availability. Consider walking or transit. This adds a cultural activity."},
        {"title": "Stop 3: Choose an affordable meal", "details": "Allow about an hour; check current menu prices. Choose a nearby option within your budget."},
    ],
    "practical_tips": ["Check current details before heading out."],
    "resources": [
        {"title": "City of Toronto: Explore and enjoy", "url": "https://www.toronto.ca/explore-enjoy/"}
    ],
    "verify_before_you_go": ["Verify current costs, opening hours, and transit details with official sources."],
}


def test_generate_plan_sends_preferences_to_groq_and_returns_structured_plan(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    original_async_client = httpx.AsyncClient
    captured = {}

    def handle_request(request):
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(PLAN_CONTENT)}}]},
        )

    transport = httpx.MockTransport(handle_request)
    monkeypatch.setattr(
        ai_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[auth.require_user] = lambda: {"uid": "test-user", "email": ""}

    with TestClient(app) as client:
        response = client.post(
            "/api/plans/generate",
            json={
                "mission_id": "toronto-on-a-budget",
                "preferences": {
                    "interests": "food, culture, sightseeing",
                    "budget": "under $30",
                    "available_time": "an afternoon",
                    "transportation": "walking and TTC",
                    "starting_location": "Downtown Toronto",
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["content"]["steps"][0]["title"] == PLAN_CONTENT["steps"][0]["title"]
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-groq-key"
    assert captured["payload"]["model"] == "openai/gpt-oss-120b"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    prompt = captured["payload"]["messages"][1]["content"]
    assert "Downtown Toronto" in prompt
    assert "under $30" in prompt
    assert "walking and TTC" in prompt


def test_groq_rate_limit_error_is_safe_and_actionable(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    original_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429,
            json={"error": {"message": "provider-internal-detail"}},
        )
    )
    monkeypatch.setattr(
        ai_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(ai_service._request_plan("test request"))

    assert error.value.status_code == 503
    assert "usage limit" in error.value.detail
    assert "Limits page" in error.value.detail
    assert "provider-internal-detail" not in error.value.detail


def test_groq_server_error_is_reported_as_temporary_instability(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    original_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"error": {"message": "provider-internal-detail"}})
    )
    monkeypatch.setattr(
        ai_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(ai_service._request_plan("test request"))

    assert error.value.status_code == 503
    assert "temporarily unstable" in error.value.detail
    assert "provider-internal-detail" not in error.value.detail


def test_invalid_groq_json_response_returns_safe_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    original_async_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not valid json"}}]},
        )
    )
    monkeypatch.setattr(
        ai_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(transport=transport, **kwargs),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(ai_service._request_plan("test request"))

    assert error.value.status_code == 502
    assert "invalid JSON" in error.value.detail
    assert "not valid json" not in error.value.detail


def test_groq_key_is_required(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "old-provider-key")

    with pytest.raises(HTTPException) as error:
        ai_service._settings()

    assert error.value.status_code == 503
    assert "GROQ_API_KEY" in error.value.detail
