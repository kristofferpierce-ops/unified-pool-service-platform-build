from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/connectors/freshbooks/oauth", tags=["freshbooks-oauth"])

APP_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = APP_ROOT / "data"
STATE_PATH = DATA_DIR / "freshbooks_oauth_state.json"
TOKENS_PATH = DATA_DIR / "freshbooks_oauth_tokens.json"

AUTH_URL = "https://auth.freshbooks.com/oauth/authorize/"
TOKEN_URL = "https://api.freshbooks.com/auth/oauth/token"
IDENTITY_URL = "https://api.freshbooks.com/auth/api/v1/users/me"

DEFAULT_SCOPES = [
    "user:profile:read",
    "user:clients:read",
    "user:clients:write",
    "user:estimates:read",
    "user:estimates:write",
    "user:invoices:read",
    "user:payments:read",
]


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def require_env(name: str) -> str:
    value = (os.getenv(name, "") or "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing required environment variable: {name}")
    return value


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return value[:4] + "..." if len(value) > 4 else "****"
    return value[:6] + "..." + value[-4:]


def freshbooks_token_call(payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8") or "{}"
            return json.loads(raw)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"FreshBooks token exchange failed: {raw}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"FreshBooks token exchange connection failed: {exc.reason}") from exc


def freshbooks_me_call(access_token: str) -> dict:
    request = Request(
        IDENTITY_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Api-Version": "alpha",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8") or "{}"
            return json.loads(raw)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"FreshBooks identity lookup failed: {raw}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"FreshBooks identity lookup connection failed: {exc.reason}") from exc


def first_account_id(identity_payload: dict) -> str:
    response = identity_payload.get("response", identity_payload)
    memberships = response.get("business_memberships", [])
    for membership in memberships:
        business = membership.get("business", {}) if isinstance(membership, dict) else {}
        account_id = str(business.get("account_id", "")).strip()
        if account_id:
            return account_id
    return ""


@router.get("/start")
def start_oauth():
    client_id = require_env("FRESHBOOKS_CLIENT_ID")
    redirect_uri = require_env("FRESHBOOKS_REDIRECT_URI")

    state = secrets.token_urlsafe(32)
    write_json(
        STATE_PATH,
        {
            "state": state,
            "created_at": utcnow_iso(),
            "redirect_uri": redirect_uri,
        },
    )

    params = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "scope": " ".join(DEFAULT_SCOPES),
        "state": state,
    }
    authorize_url = f"{AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/callback")
def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if error:
        raise HTTPException(status_code=400, detail=f"FreshBooks returned error={error} description={error_description or ''}")

    if not code:
        raise HTTPException(status_code=400, detail="FreshBooks callback did not include a code parameter.")

    client_id = require_env("FRESHBOOKS_CLIENT_ID")
    client_secret = require_env("FRESHBOOKS_CLIENT_SECRET")
    redirect_uri = require_env("FRESHBOOKS_REDIRECT_URI")

    saved_state = read_json(STATE_PATH).get("state", "")
    if saved_state and state != saved_state:
        raise HTTPException(status_code=400, detail="FreshBooks OAuth state mismatch. Start the auth flow again.")

    token_payload = freshbooks_token_call(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
    )

    access_token = str(token_payload.get("access_token", "")).strip()
    refresh_token = str(token_payload.get("refresh_token", "")).strip()
    if not access_token:
        raise HTTPException(status_code=502, detail="FreshBooks token response did not include an access token.")

    identity_payload = freshbooks_me_call(access_token)
    account_id = first_account_id(identity_payload)

    saved_payload = {
        "saved_at": utcnow_iso(),
        "redirect_uri": redirect_uri,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_payload.get("token_type", ""),
        "expires_in": token_payload.get("expires_in", ""),
        "scope": token_payload.get("scope", ""),
        "account_id": account_id,
        "identity": identity_payload,
    }
    write_json(TOKENS_PATH, saved_payload)

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 24px;">
        <h1>FreshBooks OAuth Connected</h1>
        <p><strong>Account ID:</strong> {account_id or 'Not found'}</p>
        <p><strong>Access Token:</strong> {mask(access_token)}</p>
        <p><strong>Refresh Token:</strong> {mask(refresh_token)}</p>
        <p><strong>Saved To:</strong> {TOKENS_PATH}</p>
        <p>Next step: load the saved values into your environment for live estimate work.</p>
      </body>
    </html>
    """
    return HTMLResponse(html)


@router.post("/refresh")
def refresh_tokens():
    client_id = require_env("FRESHBOOKS_CLIENT_ID")
    client_secret = require_env("FRESHBOOKS_CLIENT_SECRET")

    current = read_json(TOKENS_PATH)
    refresh_token = str(current.get("refresh_token", "")).strip()
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No saved FreshBooks refresh token was found.")

    token_payload = freshbooks_token_call(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    )

    access_token = str(token_payload.get("access_token", "")).strip()
    new_refresh_token = str(token_payload.get("refresh_token", "")).strip()
    if not access_token:
        raise HTTPException(status_code=502, detail="FreshBooks refresh response did not include an access token.")

    identity_payload = freshbooks_me_call(access_token)
    account_id = first_account_id(identity_payload)

    updated = {
        "saved_at": utcnow_iso(),
        "redirect_uri": current.get("redirect_uri", ""),
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": token_payload.get("token_type", ""),
        "expires_in": token_payload.get("expires_in", ""),
        "scope": token_payload.get("scope", ""),
        "account_id": account_id,
        "identity": identity_payload,
    }
    write_json(TOKENS_PATH, updated)

    return {
        "ok": True,
        "account_id": account_id,
        "access_token": mask(access_token),
        "refresh_token": mask(new_refresh_token),
        "saved_to": str(TOKENS_PATH),
    }
