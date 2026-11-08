import base64
import json
import os
import time
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token


bearer_scheme = HTTPBearer(auto_error=False)


def firebase_client_config() -> dict[str, str]:
    config = {
        "apiKey": os.getenv("FIREBASE_API_KEY", "").strip(),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", "").strip(),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", "").strip(),
        "appId": os.getenv("FIREBASE_APP_ID", "").strip(),
    }
    if not all(config.values()):
        raise HTTPException(
            status_code=503,
            detail=(
                "Firebase is not configured. Set FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, "
                "FIREBASE_PROJECT_ID, and FIREBASE_APP_ID in .env."
            ),
        )
    emulator_host = _emulator_host()
    if emulator_host:
        config["authEmulatorUrl"] = f"http://{emulator_host}"
    return config


def _emulator_host() -> str:
    """Local-development switch: Firebase Auth emulator host, e.g. 127.0.0.1:9099."""
    return os.getenv("FIREBASE_AUTH_EMULATOR_HOST", "").strip()


def _verify_emulator_token(token: str, project_id: str) -> dict[str, Any]:
    """The emulator issues unsigned tokens, so only check structure, audience and expiry."""
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError) as exc:
        raise ValueError("Malformed token") from exc
    if claims.get("aud") != project_id:
        raise ValueError("Wrong audience")
    if claims.get("exp", 0) < time.time():
        raise ValueError("Token expired")
    return claims


def require_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if not project_id:
        raise HTTPException(
            status_code=503,
            detail="Firebase is not configured. Set FIREBASE_PROJECT_ID in .env.",
        )

    try:
        if _emulator_host():
            claims = _verify_emulator_token(credentials.credentials, project_id)
        else:
            claims = id_token.verify_firebase_token(
                credentials.credentials,
                Request(),
                audience=project_id,
                clock_skew_in_seconds=10,
            )
        if claims.get("iss") != f"https://securetoken.google.com/{project_id}":
            raise ValueError("Wrong token issuer")
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Sign in again.") from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="The Firebase token has no user ID.")
    return {"uid": user_id, "email": claims.get("email", "")}

