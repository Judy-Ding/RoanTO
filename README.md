# RoamTO

**Your AI Companion for Starting Life in Toronto**

A small, mobile-first prototype for newcomers to turn an everyday Toronto goal into an AI-personalized action plan. It includes 12 preset missions across four categories, custom goals, mission-specific preference questions, Firebase email/password authentication, editable plans, and saved step-by-step progress.

## Requirements

- Python 3.10+
- A GroqCloud API key
- A Firebase project with Email/Password sign-in enabled

The AI provider is GroqCloud, called from the backend using its OpenAI-compatible Chat Completions API. Create a key in [GroqCloud](https://console.groq.com/keys), copy `.env.example` to `.env`, set `GROQ_API_KEY`, and restart the server. The default model is `openai/gpt-oss-120b`; set `GROQ_MODEL` to another model enabled for your GroqCloud account if needed. The key remains on the backend and is never sent to the browser. AI generation and modification return a clear setup error if the key is missing; the app does not substitute sample AI responses.

## Firebase authentication setup

1. Create a project in the [Firebase Console](https://console.firebase.google.com/).
2. In **Authentication → Sign-in method**, enable **Email/Password**.
3. In **Project settings → General**, register a Web app and copy its `apiKey`, `authDomain`, `projectId`, and `appId`.
4. Add `localhost` and `127.0.0.1` to **Authentication → Settings → Authorized domains** if they are not listed.
5. Put those values in `.env` as `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, and `FIREBASE_APP_ID`, then restart the server.

The Firebase Web config (including its API key) is public client configuration, not a password or service-account secret. The backend verifies Firebase ID tokens against the configured project before accepting plan generation or database operations. Passwords are handled by Firebase and are never stored in RoamTO's SQLite database. Plan rows are associated with the verified Firebase user ID, so users can only access their own plans. Configure Firebase API key restrictions and authorized domains before deploying beyond local development.

## Run locally

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GroqCloud key and Firebase configuration to .env
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The FastAPI backend serves the existing frontend, so no separate frontend server is required. CORS is restricted to the local app and VS Code Live Server origins. If using Windows, activate the virtual environment with `.venv\Scripts\activate`.

The SQLite database is created as `roamto.db` in this folder on first start. Override its location with `DATABASE_PATH` if needed. Do not put secrets in frontend files.

## Screens and API

- **Home:** Start from four pillar cards. Opening a pillar shows only its own preset missions; `GET /api/missions` returns all 12 presets for the app. Choose a preset or enter a custom goal.
- **Authentication:** `/login.html` provides Firebase email/password registration and login. `GET /api/auth/config` returns the public Firebase Web config.
- **AI Personalized Plan:** `POST /api/plans/generate` sends mission and preference data to GroqCloud and validates the structured response; `POST /api/plans/modify` revises it from a natural-language request. Both require a valid Firebase ID token. Explore and outing requests ask for suggested stops, approximate activity durations, rough CAD cost estimates, transportation suggestions, and preference-based explanations; current prices, opening hours, transit schedules, and exact travel times are not claimed as verified.
- **My Plan:** `POST /api/plans/demo-seed` adds four fixed demo starter plans (one per pillar) to the authenticated user's account once; repeat requests do not create duplicates. `POST /api/plans` validates and saves an additional plan; `GET /api/plans` lists that user's plans; `GET /api/plans/{plan_id}` retrieves only that user's plan; `PATCH /api/plans/{plan_id}/steps/{step_index}` updates a step; `PATCH /api/plans/{plan_id}/complete` updates overall completion. Plans and progress persist in SQLite across server restarts.

Plans contain a goal, overview, three to five actions, practical tips, relevant official links, and details to verify. The AI is instructed not to imply live verification of transit schedules, hours, prices, eligibility, or service availability. Confirm time-sensitive information directly with the linked official source.

This is a course prototype, not a production service. Authentication is delegated to Firebase and plan ownership is enforced by the API, but the prototype does not include production account recovery, email verification, abuse prevention, or deployment hardening.
