import os
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
    return config


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
        claims = id_token.verify_firebase_token(
            credentials.credentials,
            Request(),
            audience=project_id,
        )
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Sign in again.") from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="The Firebase token has no user ID.")
    return {"uid": user_id, "email": claims.get("email", "")}

