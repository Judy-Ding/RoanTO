import base64
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.auth.exceptions import GoogleAuthError

from backend import auth
from backend.routes import router

PROJECT = "demo-roamto"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.db"))
    for key in ("FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID",
                "FIREBASE_APP_ID", "FIREBASE_AUTH_EMULATOR_HOST"):
        monkeypatch.delenv(key, raising=False)
    from backend.database import initialize_database
    initialize_database()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def configure(monkeypatch):
    monkeypatch.setenv("FIREBASE_API_KEY", "key")
    monkeypatch.setenv("FIREBASE_AUTH_DOMAIN", f"{PROJECT}.firebaseapp.com")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", PROJECT)
    monkeypatch.setenv("FIREBASE_APP_ID", "1:1:web:1")


def claims(uid="u1", **over):
    return {"sub": uid, "email": f"{uid}@x.com", "aud": PROJECT,
            "iss": f"https://securetoken.google.com/{PROJECT}",
            "exp": time.time() + 600, **over}


def fake_token(c):
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{enc({'alg': 'none'})}.{enc(c)}."


def test_config_503_when_unconfigured(client):
    r = client.get("/api/auth/config")
    assert r.status_code == 503 and "FIREBASE_API_KEY" in r.json()["detail"]


def test_config_returns_public_fields_only(client, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "secret")
    body = client.get("/api/auth/config").json()
    assert set(body) == {"apiKey", "authDomain", "projectId", "appId"}


def test_missing_token_401(client, monkeypatch):
    configure(monkeypatch)
    assert client.get("/api/plans").status_code == 401


def test_unconfigured_project_503(client):
    assert client.get("/api/plans", headers={"Authorization": "Bearer x"}).status_code == 503


def test_invalid_token_401(client, monkeypatch):
    configure(monkeypatch)
    def boom(*a, **k): raise ValueError("bad")
    monkeypatch.setattr(auth.id_token, "verify_firebase_token", boom)
    assert client.get("/api/plans", headers={"Authorization": "Bearer x"}).status_code == 401
    def boom2(*a, **k): raise GoogleAuthError("bad")
    monkeypatch.setattr(auth.id_token, "verify_firebase_token", boom2)
    assert client.get("/api/plans", headers={"Authorization": "Bearer x"}).status_code == 401


def test_valid_token_ok_and_audience_passed(client, monkeypatch):
    configure(monkeypatch)
    seen = {}
    def ok(token, request, audience=None, **k):
        seen["aud"] = audience
        return claims()
    monkeypatch.setattr(auth.id_token, "verify_firebase_token", ok)
    r = client.get("/api/plans", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200 and r.json() == [] and seen["aud"] == PROJECT


def test_wrong_issuer_rejected(client, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(auth.id_token, "verify_firebase_token",
                        lambda *a, **k: claims(iss="https://evil.example"))
    assert client.get("/api/plans", headers={"Authorization": "Bearer t"}).status_code == 401


def test_token_without_uid_rejected(client, monkeypatch):
    configure(monkeypatch)
    c = claims(); c.pop("sub")
    monkeypatch.setattr(auth.id_token, "verify_firebase_token", lambda *a, **k: c)
    assert client.get("/api/plans", headers={"Authorization": "Bearer t"}).status_code == 401


def test_emulator_token_paths(client, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    assert client.get("/api/auth/config").json()["authEmulatorUrl"] == "http://127.0.0.1:9099"
    h = lambda c: {"Authorization": f"Bearer {fake_token(c)}"}
    assert client.get("/api/plans", headers=h(claims())).status_code == 200
    assert client.get("/api/plans", headers=h(claims(aud="other"))).status_code == 401
    assert client.get("/api/plans", headers=h(claims(exp=1))).status_code == 401
    assert client.get("/api/plans", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_users_cannot_see_each_others_plans(client, monkeypatch):
    configure(monkeypatch)
    users = {"a": claims("a"), "b": claims("b")}
    monkeypatch.setattr(auth.id_token, "verify_firebase_token", lambda t, *a, **k: users[t])
    draft = {"mission_id": "custom", "custom_goal": "Find a library card", "preferences": {},
             "content": {"goal": "Library card", "overview": "Get a library card soon.",
                         "steps": [{"title": f"s{i}", "details": "d"} for i in range(3)],
                         "practical_tips": ["t"], "resources": [], "verify_before_you_go": ["v"]}}
    r = client.post("/api/plans", json=draft, headers={"Authorization": "Bearer a"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.get(f"/api/plans/{pid}", headers={"Authorization": "Bearer b"}).status_code == 404
    assert client.get("/api/plans", headers={"Authorization": "Bearer b"}).json() == []
    assert client.get(f"/api/plans/{pid}", headers={"Authorization": "Bearer a"}).status_code == 200
