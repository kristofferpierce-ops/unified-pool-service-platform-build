import base64
import difflib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# -----------------------------
# Config
# -----------------------------
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "bridge.db"))

RC_SERVER_URL = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip("/")
RC_CLIENT_ID = os.getenv("RC_CLIENT_ID", "")
RC_CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET", "")
RC_JWT = os.getenv("RC_JWT", "")
RC_WEBHOOK_PUBLIC_URL = os.getenv("RC_WEBHOOK_PUBLIC_URL", "")
RC_VALIDATION_TOKEN = os.getenv("RC_VALIDATION_TOKEN", "change-me")
RC_WEBHOOK_SHARED_SECRET = os.getenv("RC_WEBHOOK_SHARED_SECRET", "")
ENABLE_CALL_SUBSCRIPTION = os.getenv("ENABLE_CALL_SUBSCRIPTION", "true").lower() == "true"
ENABLE_SMS_SUBSCRIPTION = os.getenv("ENABLE_SMS_SUBSCRIPTION", "true").lower() == "true"
ENABLE_VOICEMAIL_SUBSCRIPTION = os.getenv("ENABLE_VOICEMAIL_SUBSCRIPTION", "true").lower() == "true"
ENABLE_RINGSENSE_SUBSCRIPTION = os.getenv("ENABLE_RINGSENSE_SUBSCRIPTION", "false").lower() == "true"
CALLS_REQUIRE_RECORDINGS = os.getenv("CALLS_REQUIRE_RECORDINGS", "false").lower() == "true"
SMS_BATCH_HOUR_LOCAL = int(os.getenv("SMS_BATCH_HOUR_LOCAL", "17"))
SMS_BATCH_MINUTE_LOCAL = int(os.getenv("SMS_BATCH_MINUTE_LOCAL", "30"))

LACRM_API_URL = os.getenv("LACRM_API_URL", "https://api.lessannoyingcrm.com/v2/")
LACRM_API_KEY = os.getenv("LACRM_API_KEY", "")
LACRM_ADDRESS_FIELD_HINTS = [
    f.strip() for f in os.getenv(
        "LACRM_ADDRESS_FIELD_HINTS",
        "Address,Property Address,Service Address,Street Address,Company Name,Name",
    ).split(",") if f.strip()
]

app = FastAPI(title="RingCentral → LACRM Bridge")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
RC_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}
HUD_CONTEXT_CACHE: Dict[str, Any] = {}
DB_WRITE_LOCK = threading.Lock()


# -----------------------------
# Database helpers
# -----------------------------
def get_db() -> sqlite3.Connection:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=30.0,
    )
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return conn


def run_db_write(callback, *, retries: int = 8, sleep_base: float = 0.15):
    last_exc = None
    for attempt in range(retries):
        conn = None
        try:
            with DB_WRITE_LOCK:
                conn = get_db()
                result = callback(conn)
                conn.commit()
                return result
        except sqlite3.OperationalError as exc:
            last_exc = exc
            if "locked" not in str(exc).lower():
                raise
            time.sleep(sleep_base * (attempt + 1))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    raise last_exc


def ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        conn.commit()


def init_db() -> None:
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY,
            rc_event_uuid TEXT,
            telephony_session_id TEXT,
            source_record_id TEXT,
            caller_phone TEXT,
            internal_phone TEXT,
            agent_extension_id TEXT,
            direction TEXT,
            call_time TEXT,
            summary TEXT,
            next_steps TEXT,
            transcript TEXT,
            extracted_address TEXT,
            extracted_names TEXT,
            status TEXT,
            raw_json TEXT,
            attached_contact_ids TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_calls_session ON calls(telephony_session_id)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS caller_relationships (
            phone TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 1,
            last_selected_at TEXT,
            PRIMARY KEY (phone, contact_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_event_uuids (
            event_uuid TEXT PRIMARY KEY,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sms_batches (
            id TEXT PRIMARY KEY,
            batch_date TEXT NOT NULL,
            external_phone TEXT NOT NULL,
            internal_phone TEXT,
            latest_message_at TEXT,
            status TEXT,
            summary TEXT,
            next_steps TEXT,
            transcript TEXT,
            extracted_address TEXT,
            extracted_names TEXT,
            attached_contact_ids TEXT,
            auto_attached INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sms_batches_phone_date ON sms_batches(external_phone, batch_date)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sms_messages (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            message_time TEXT,
            direction TEXT,
            from_phone TEXT,
            to_phone TEXT,
            body TEXT,
            raw_json TEXT,
            created_at TEXT,
            FOREIGN KEY(batch_id) REFERENCES sms_batches(id)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sms_messages_batch ON sms_messages(batch_id, message_time)")
    ensure_column(conn, "calls", "hidden", "INTEGER DEFAULT 0")
    ensure_column(conn, "calls", "trashed_at", "TEXT")
    ensure_column(conn, "calls", "trash_reason", "TEXT")
    ensure_column(conn, "calls", "hud_dismissed_at", "TEXT")
    ensure_column(conn, "calls", "last_status_code", "TEXT")
    ensure_column(conn, "calls", "item_type", "TEXT DEFAULT 'call'")
    ensure_column(conn, "calls", "voicemail_message_id", "TEXT")
    ensure_column(conn, "calls", "voicemail_transcription_status", "TEXT")
    ensure_column(conn, "calls", "voicemail_duration", "INTEGER")
    ensure_column(conn, "calls", "voicemail_recording_uri", "TEXT")
    ensure_column(conn, "calls", "voicemail_transcription_uri", "TEXT")
    ensure_column(conn, "calls", "caller_name", "TEXT")
    ensure_column(conn, "sms_batches", "hidden", "INTEGER DEFAULT 0")
    ensure_column(conn, "sms_batches", "trashed_at", "TEXT")
    ensure_column(conn, "sms_batches", "trash_reason", "TEXT")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS routing_rules (
            phone TEXT PRIMARY KEY,
            label TEXT,
            mode TEXT NOT NULL DEFAULT 'manual',
            owner_type TEXT NOT NULL DEFAULT 'unknown',
            default_contact_ids TEXT,
            notes TEXT,
            updated_at TEXT
        )
        """
    )
    # Message Sync state (used to pull both inbound and outbound SMS via message-sync)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message_sync_state (
            scope TEXT PRIMARY KEY,
            sync_token TEXT,
            sync_time TEXT,
            updated_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# -----------------------------
# Utility helpers
# -----------------------------
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_now() -> datetime:
    return datetime.now().astimezone()


def local_date_string(dt_str: Optional[str] = None) -> str:
    if dt_str:
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone().date().isoformat()
        except Exception:
            pass
    return local_now().date().isoformat()


def normalize_digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def normalize_phone(value: Optional[str]) -> str:
    digits = normalize_digits(value)
    if not digits:
        return ""
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if value and value.startswith("+"):
        return value
    return "+" + digits


def phone_search_variants(value: Optional[str]) -> List[str]:
    """Return common search/display variants for the same phone number."""
    digits = normalize_digits(value)
    if not digits:
        return []

    national = ""
    variants: List[str] = []

    if len(digits) >= 11 and digits.startswith("1"):
        national = digits[1:11]
        variants.append("+" + digits[:11])
        variants.append(digits[:11])
    elif len(digits) == 10:
        national = digits
        variants.append("+1" + digits)
        variants.append("1" + digits)
    else:
        national = digits[-10:] if len(digits) >= 10 else digits
        variants.append(normalize_phone(value))

    if national:
        variants.append(national)
        if len(national) == 10:
            area, prefix, line = national[:3], national[3:6], national[6:]
            variants.append(f"({area}) {prefix}-{line}")
            variants.append(f"{area}-{prefix}-{line}")
            variants.append(f"{area}.{prefix}.{line}")
            variants.append(f"{area} {prefix} {line}")

    output: List[str] = []
    seen = set()
    for item in variants:
        if item and item not in seen:
            output.append(item)
            seen.add(item)
    return output


def phones_match(left: Optional[str], right: Optional[str]) -> bool:
    left_digits = normalize_digits(left)
    right_digits = normalize_digits(right)
    if not left_digits or not right_digits:
        return False
    if left_digits == right_digits:
        return True
    if len(left_digits) >= 10 and len(right_digits) >= 10:
        return left_digits[-10:] == right_digits[-10:]
    return False


def safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return "{}"


def parse_json_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if str(x).strip()]
        except Exception:
            pass
        return [x.strip() for x in value.split(',') if x.strip()]
    return []


def recursive_collect_strings(value: Any) -> List[str]:
    items: List[str] = []
    if isinstance(value, str):
        items.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                items.append(k)
            items.extend(recursive_collect_strings(v))
    elif isinstance(value, list):
        for item in value:
            items.extend(recursive_collect_strings(item))
    return items


def flatten_contact_text(contact: Dict[str, Any]) -> str:
    values = recursive_collect_strings(contact)
    return " | ".join(v for v in values if isinstance(v, str))


def _stringify_lacrm_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("Text", "Name", "Company Name", "CompanyName", "FirstName", "LastName", "Value", "Label"):
            if value.get(key):
                return str(value.get(key)).strip()
        return " ".join(str(v).strip() for v in value.values() if str(v).strip())
    if isinstance(value, list):
        return ", ".join(filter(None, (_stringify_lacrm_value(v) for v in value)))
    return str(value).strip()


def get_display_name(contact: Dict[str, Any]) -> str:
    candidates = [
        contact.get("Name"),
        contact.get("Company Name"),
        contact.get("CompanyName"),
        contact.get("FirstName"),
        contact.get("LastName"),
    ]
    for candidate in candidates:
        text = _stringify_lacrm_value(candidate)
        if text:
            return text
    return f"LACRM {contact.get('ContactId', '')}"


def get_best_address_display(contact: Dict[str, Any]) -> str:
    for field in LACRM_ADDRESS_FIELD_HINTS:
        val = contact.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, dict):
                for key in ("Text", "Phone", "Email"):
                    if first.get(key):
                        return str(first.get(key))
            if isinstance(first, str):
                return first
    for key, val in contact.items():
        if "address" in key.lower() and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def get_contact_phones(contact: Dict[str, Any]) -> List[str]:
    phones = []
    for item in contact.get("Phone", []) or []:
        if isinstance(item, dict):
            if item.get("Text"):
                phones.append(str(item["Text"]))
            elif item.get("Phone"):
                phones.append(str(item["Phone"]))
    return phones


def ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100)


def maybe_parse_datetime(dt: Optional[str]) -> str:
    if not dt:
        return utcnow_iso()
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except Exception:
        return utcnow_iso()


ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.'-]+(?:\s+[A-Za-z0-9.'-]+){0,5}\s(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl|Circle|Cir|Terrace|Ter|Highway|Hwy)\b(?:\s+(?:Unit|Apt|Apartment|Suite|Ste|#)\s*\w+)?",
    re.IGNORECASE,
)
NAME_RE = re.compile(r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Owner|Customer|Guest|Manager)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})")


def extract_entities(text: str) -> Dict[str, str]:
    address = ""
    names: List[str] = []
    if text:
        address_match = ADDRESS_RE.search(text)
        if address_match:
            address = address_match.group(0).strip()
        for m in NAME_RE.finditer(text):
            names.append(m.group(1).strip())
    return {"address": address, "names": ", ".join(dict.fromkeys(names))[:500]}


def strip_html_to_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# -----------------------------
# RingCentral auth + API
# -----------------------------
def rc_access_token() -> str:
    if RC_TOKEN_CACHE["access_token"] and time.time() < RC_TOKEN_CACHE["expires_at"] - 60:
        return RC_TOKEN_CACHE["access_token"]
    if not RC_CLIENT_ID or not RC_CLIENT_SECRET or not RC_JWT:
        raise RuntimeError("Missing RingCentral credentials in .env")
    basic = base64.b64encode(f"{RC_CLIENT_ID}:{RC_CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        f"{RC_SERVER_URL}/restapi/oauth/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": RC_JWT,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    RC_TOKEN_CACHE["access_token"] = data["access_token"]
    RC_TOKEN_CACHE["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return RC_TOKEN_CACHE["access_token"]


def build_rc_webhook_address() -> str:
    if not RC_WEBHOOK_PUBLIC_URL:
        raise RuntimeError("RC_WEBHOOK_PUBLIC_URL is missing")
    address = RC_WEBHOOK_PUBLIC_URL if RC_WEBHOOK_PUBLIC_URL.endswith("/webhooks/ringcentral") else f"{RC_WEBHOOK_PUBLIC_URL.rstrip('/')}/webhooks/ringcentral"
    if RC_WEBHOOK_SHARED_SECRET:
        sep = "&" if "?" in address else "?"
        address = f"{address}{sep}secret={RC_WEBHOOK_SHARED_SECRET}"
    return address


def build_rc_event_filters(mode: str = "configured") -> List[str]:
    mode = (mode or "configured").lower()
    filters: List[str] = []

    include_calls = ENABLE_CALL_SUBSCRIPTION
    include_sms = ENABLE_SMS_SUBSCRIPTION
    include_voicemail = ENABLE_VOICEMAIL_SUBSCRIPTION
    include_ringsense = ENABLE_RINGSENSE_SUBSCRIPTION

    if mode == "calls":
        include_calls, include_sms, include_voicemail, include_ringsense = True, False, False, False
    elif mode == "sms":
        include_calls, include_sms, include_voicemail, include_ringsense = False, True, False, False
    elif mode == "voicemail":
        include_calls, include_sms, include_voicemail, include_ringsense = False, False, True, False
    elif mode == "ringsense":
        include_calls, include_sms, include_voicemail, include_ringsense = False, False, False, True
    elif mode == "core":
        include_calls, include_sms, include_voicemail, include_ringsense = True, True, True, False
    elif mode == "all":
        include_calls, include_sms, include_voicemail, include_ringsense = True, True, True, True

    if include_calls:
        telephony_filter = "/restapi/v1.0/account/~/telephony/sessions"
        if CALLS_REQUIRE_RECORDINGS:
            telephony_filter += "?withRecordings=true"
        filters.append(telephony_filter)

    if include_sms:
        filters.append("/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS")

    if include_voicemail:
        filters.append("/restapi/v1.0/account/~/extension/~/voicemail")

    if include_ringsense:
        filters.append("/ai/ringsense/v1/public/accounts/~/domains/pbx/insights")

    return filters


def rc_create_subscription(mode: str = "configured") -> Dict[str, Any]:
    token = rc_access_token()
    event_filters = build_rc_event_filters(mode)
    if not event_filters:
        raise RuntimeError("No RingCentral event filters are enabled. Check your .env toggles or requested mode.")
    body = {
        "eventFilters": event_filters,
        "deliveryMode": {
            "transportType": "WebHook",
            "address": build_rc_webhook_address(),
            "validationToken": RC_VALIDATION_TOKEN,
        },
    }
    resp = requests.post(
        f"{RC_SERVER_URL}/restapi/v1.0/subscription",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=body,
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        body_text = resp.text.strip()
        raise RuntimeError(
            f"RingCentral subscription failed ({resp.status_code}). mode={mode}. "
            f"filters={json.dumps(event_filters)}. response={body_text}"
        ) from exc
    return resp.json()


def rc_fetch_insights(source_record_id: str) -> Dict[str, Any]:
    token = rc_access_token()
    resp = requests.get(
        f"{RC_SERVER_URL}/ai/ringsense/v1/public/accounts/~/domains/pbx/records/{source_record_id}/insights",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

# -----------------------------
# ACE/RingSense enrichment (telephonySessionId -> recordingId -> insights)
# -----------------------------

ACE_RETRY_MAX_ATTEMPTS = int(os.getenv("ACE_RETRY_MAX_ATTEMPTS", "10"))
ACE_RETRY_INITIAL_SECONDS = int(os.getenv("ACE_RETRY_INITIAL_SECONDS", "10"))
ACE_LOOKBACK_DAYS_DEFAULT = int(os.getenv("ACE_LOOKBACK_DAYS_DEFAULT", "3"))

def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def rc_iter_company_call_log_with_recordings(date_from_iso: str, date_to_iso: str, per_page: int = 250, max_pages: int = 4) -> List[Dict[str, Any]]:
    """Fetches call log records that have recordings (recordingType=All) within a time window.
    We intentionally *do not* rely on telephonySessionId being a supported filter; instead we fetch a small window and match in code.
    """
    token = rc_access_token()
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/call-log"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    records: List[Dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        params = {
            "view": "Simple",
            "recordingType": "All",
            "dateFrom": date_from_iso,
            "dateTo": date_to_iso,
            "perPage": str(per_page),
            "page": str(page),
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json() if resp.text else {}
        batch = data.get("records") or []
        if not isinstance(batch, list):
            batch = []
        records.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return records

def rc_find_recording_id_for_session(telephony_session_id: str, call_time_iso: Optional[str] = None) -> str:
    """Resolve a call recording id using telephonySessionId by scanning call logs with recordings.

    RingCentral call log records include telephonySessionId; calls with recordings include a 'recording' metadata object with an 'id'.
    We search a small date window around call_time to find the matching record.
    """
    telephony_session_id = str(telephony_session_id or "").strip()
    if not telephony_session_id:
        return ""

    now = datetime.now(timezone.utc)
    if call_time_iso:
        dt = maybe_parse_datetime(call_time_iso)
        if isinstance(dt, datetime):
            start = dt - timedelta(days=1)
            end = dt + timedelta(days=2)
        else:
            start = now - timedelta(days=ACE_LOOKBACK_DAYS_DEFAULT)
            end = now + timedelta(days=1)
    else:
        start = now - timedelta(days=ACE_LOOKBACK_DAYS_DEFAULT)
        end = now + timedelta(days=1)

    records = rc_iter_company_call_log_with_recordings(_iso_z(start), _iso_z(end), per_page=250, max_pages=6)
    # Prefer the most recent matching record with a recording id
    for rec in sorted(records, key=lambda r: (r.get("startTime") or ""), reverse=True):
        if str(rec.get("telephonySessionId") or "") != telephony_session_id:
            continue
        recording = rec.get("recording") or {}
        rid = str(recording.get("id") or "").strip()
        if rid:
            return rid
    return ""

def _call_has_transcript_or_summary(call_id: str) -> bool:
    row = get_call_by_id(call_id)
    if not row:
        return False
    return bool((row["summary"] or "").strip() or (row["transcript"] or "").strip() or (row["next_steps"] or "").strip())

def ace_enrich_call_from_session_async(call_id: str, telephony_session_id: str, call_time_iso: Optional[str] = None) -> None:
    """Background: resolve recording id and fetch ACE insights with retries."""
    def worker():
        delay = max(1, ACE_RETRY_INITIAL_SECONDS)
        for attempt in range(1, ACE_RETRY_MAX_ATTEMPTS + 1):
            try:
                if _call_has_transcript_or_summary(call_id):
                    return
                row = get_call_by_id(call_id)
                if not row:
                    return

                # If we already have a recording id, use it. Otherwise resolve via call log.
                recording_id = str(row["source_record_id"] or "").strip()
                if not recording_id:
                    recording_id = rc_find_recording_id_for_session(telephony_session_id, call_time_iso)
                    if recording_id:
                        conn = get_db()
                        cur = conn.cursor()
                        cur.execute("UPDATE calls SET source_record_id = ?, updated_at = ? WHERE id = ?", (recording_id, utcnow_iso(), call_id))
                        conn.commit()
                        conn.close()

                if recording_id:
                    insights = rc_fetch_insights(recording_id)
                    summary, next_steps, transcript = parse_ringsense_payload(insights)
                    if summary or next_steps or transcript:
                        entities = extract_entities("\n".join([summary or "", next_steps or "", transcript or ""]))
                        upsert_call({
                            "id": call_id,
                            "telephony_session_id": telephony_session_id,
                            "source_record_id": recording_id,
                            "summary": summary,
                            "next_steps": next_steps,
                            "transcript": transcript,
                            "extracted_address": entities["address"],
                            "extracted_names": entities["names"],
                            "status": "PENDING_REVIEW",
                            "updated_at": utcnow_iso(),
                        })
                        return
            except Exception as exc:
                # Typical failures early on: call log not updated yet, insights not ready yet, etc.
                # Keep retrying for a short period.
                pass

            time.sleep(delay)
            # backoff, cap at 90s
            delay = min(int(delay * 1.6), 90)

    threading.Thread(target=worker, daemon=True).start()


def rc_fetch_text_attachment(uri: str) -> str:
    if not uri:
        return ""
    token = rc_access_token()
    resp = requests.get(
        uri,
        headers={"Authorization": f"Bearer {token}", "Accept": "text/plain, application/json, */*"},
        timeout=30,
    )
    resp.raise_for_status()
    content_type = (resp.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        try:
            data = resp.json()
            if isinstance(data, dict):
                return strip_html_to_text(data.get("subject") or data.get("text") or safe_json(data))
            return strip_html_to_text(safe_json(data))
        except Exception:
            pass
    return strip_html_to_text(resp.text or "")


# -----------------------------
# LACRM API
# -----------------------------

def voicemail_transcription_retry_async(message_id: str, attachment_uri: str) -> None:
    """Background retry for voicemail transcription attachment."""
    def worker():
        delay = 8
        for _ in range(6):
            try:
                if not attachment_uri:
                    return
                t = rc_fetch_text_attachment(attachment_uri)
                if t and t.strip():
                    try:
                        update_voicemail_transcript_and_clues(message_id, t.strip(), transcription_status="Completed", transcription_uri=attachment_uri)
                    except Exception:
                        # Fallback: minimal update
                        conn = get_db()
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE calls SET transcript = ?, summary = COALESCE(NULLIF(summary,''), ?), updated_at = ? WHERE (voicemail_message_id = ? OR source_record_id = ?) AND item_type = 'voicemail'",
                            (t.strip()[:40000], t.strip()[:12000], utcnow_iso(), str(message_id), str(message_id)),
                        )
                        conn.commit()
                        conn.close()
                    return
            except Exception:
                pass
            time.sleep(delay)
            delay = min(int(delay * 1.5), 45)
    threading.Thread(target=worker, daemon=True).start()



# -----------------------------
# Voicemail transcription polling (message-store refresh)
# -----------------------------
_voicemail_poll_lock = threading.Lock()
_voicemail_poll_inflight: set[str] = set()

def rc_get_message_store_item(message_id: str) -> Dict[str, Any]:
    """Fetch a message-store item for the JWT-authenticated extension."""
    if not message_id:
        return {}
    token = rc_access_token()
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/extension/~/message-store/{message_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    return resp.json() if resp.content else {}

def update_voicemail_transcript_and_clues(message_id: str, transcript_text: str, transcription_status: Optional[str] = None, transcription_uri: Optional[str] = None) -> None:
    """Update voicemail call row with transcript + recomputed summary/next steps/entities."""
    if not message_id:
        return
    transcript_text = (transcript_text or "").strip()
    if not transcript_text:
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM calls WHERE item_type='voicemail' AND (voicemail_message_id=? OR source_record_id=?) ORDER BY updated_at DESC LIMIT 1",
        (str(message_id), str(message_id)),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return

    caller_phone = row["caller_phone"] or ""
    caller_name = row["caller_name"] or ""
    created_time = row["call_time"] or utcnow_iso()
    duration = int(row["voicemail_duration"] or 0) if "voicemail_duration" in row.keys() else 0
    # Use existing transcript as subject fallback if present
    subject_text = ""
    try:
        raw = json.loads(row["raw_json"] or "{}")
        body = raw.get("body") if isinstance(raw.get("body"), dict) else raw
        subject_text = strip_html_to_text((body or {}).get("subject") or "")
    except Exception:
        subject_text = ""

    summary, next_steps, entities = summarize_voicemail(caller_phone, caller_name, created_time, duration, transcript_text, subject_text)
    cur.execute(
        """
        UPDATE calls
        SET transcript = ?,
            summary = ?,
            next_steps = ?,
            extracted_address = ?,
            extracted_names = ?,
            voicemail_transcription_status = COALESCE(?, voicemail_transcription_status),
            voicemail_transcription_uri = COALESCE(?, voicemail_transcription_uri),
            updated_at = ?
        WHERE id = ?
        """,
        (
            transcript_text[:40000],
            (summary or "")[:6000],
            (next_steps or "")[:2000],
            (entities.get("address") or "")[:500],
            (entities.get("names") or "")[:500],
            transcription_status,
            transcription_uri,
            utcnow_iso(),
            row["id"],
        ),
    )
    conn.commit()
    conn.close()

def voicemail_transcription_poll_async(message_id: str) -> None:
    """Poll message-store until voicemail transcription attachment appears, then fetch and update."""
    if not message_id:
        return
    with _voicemail_poll_lock:
        if message_id in _voicemail_poll_inflight:
            return
        _voicemail_poll_inflight.add(message_id)

    def worker():
        delay = int(os.getenv("VOICEMAIL_TRANSCRIPT_INITIAL_SECONDS", "10"))
        max_attempts = int(os.getenv("VOICEMAIL_TRANSCRIPT_MAX_ATTEMPTS", "18"))
        try:
            for _ in range(max_attempts):
                try:
                    msg = rc_get_message_store_item(message_id)
                    if not isinstance(msg, dict):
                        msg = {}
                    status = str(msg.get("vmTranscriptionStatus") or "")
                    attachments = msg.get("attachments") or []
                    if not isinstance(attachments, list):
                        attachments = [attachments]
                    transcription_attachment = get_attachment_by_type(attachments, "AudioTranscription")
                    if transcription_attachment and transcription_attachment.get("uri") and str(status).lower() == "completed":
                        t = rc_fetch_text_attachment(transcription_attachment.get("uri") or "")
                        if t and t.strip():
                            update_voicemail_transcript_and_clues(message_id, t.strip(), transcription_status=status, transcription_uri=transcription_attachment.get("uri"))
                            return
                    # Some accounts return transcription without setting status cleanly; accept if attachment exists and has content.
                    if transcription_attachment and transcription_attachment.get("uri"):
                        t = rc_fetch_text_attachment(transcription_attachment.get("uri") or "")
                        if t and t.strip():
                            update_voicemail_transcript_and_clues(message_id, t.strip(), transcription_status=status or "Completed", transcription_uri=transcription_attachment.get("uri"))
                            return
                except Exception:
                    pass
                time.sleep(delay)
                delay = min(int(delay * 1.5), 60)
        finally:
            with _voicemail_poll_lock:
                _voicemail_poll_inflight.discard(message_id)

    threading.Thread(target=worker, daemon=True).start()
def lacrm_call(function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
    if not LACRM_API_KEY:
        raise RuntimeError("Missing LACRM_API_KEY in .env")
    resp = requests.post(
        LACRM_API_URL,
        headers={
            "Authorization": LACRM_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={"Function": function_name, "Parameters": params or {}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("Error"):
        raise RuntimeError(str(data["Error"]))
    return data


def lacrm_get_contacts(search_terms: str) -> List[Dict[str, Any]]:
    data = lacrm_call("GetContacts", {"SearchTerms": search_terms})
    if isinstance(data, dict) and "Results" in data:
        return data["Results"] or []
    if isinstance(data, list):
        return data
    return []


def lacrm_create_note(contact_id: str, note: str, event_time: str) -> Dict[str, Any]:
    payload = {
        "ContactId": str(contact_id),
        "Note": note,
        "DateDisplayedInHistory": maybe_parse_datetime(event_time),
    }
    data = lacrm_call("CreateNote", payload)
    return data if isinstance(data, dict) else {"result": data}


def lacrm_get_users() -> List[Dict[str, Any]]:
    data = lacrm_call("GetUsers")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "Results" in data:
        return data["Results"] or []
    return []


def lacrm_create_task(name: str, contact_id: str, due_date: Optional[str] = None, assigned_to: Optional[str] = None, description: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "Name": name,
        "ContactId": str(contact_id),
    }
    if due_date:
        payload["DueDate"] = due_date
    if assigned_to:
        payload["AssignedTo"] = str(assigned_to)
    if description:
        payload["Description"] = description
    data = lacrm_call("CreateTask", payload)
    return data if isinstance(data, dict) else {"result": data}


def lacrm_get_notes_attached(contact_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    data = lacrm_call("GetNotesAttachedToContact", {"ContactId": str(contact_id), "MaxNumberOfResults": max(limit, 5)})
    if isinstance(data, dict):
        return data.get("Results", []) or []
    return []


def lacrm_get_tasks_attached(contact_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    data = lacrm_call("GetTasksAttachedToContact", {"ContactId": str(contact_id), "MaxNumberOfResults": max(limit, 5)})
    if isinstance(data, dict):
        return data.get("Results", []) or []
    return []


def lacrm_get_events_attached(contact_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    data = lacrm_call("GetEventsAttachedToContact", {"ContactId": str(contact_id), "MaxNumberOfResults": max(limit, 5)})
    if isinstance(data, dict):
        return data.get("Results", []) or []
    return []


def lacrm_get_pipeline_items_attached(contact_id: str) -> List[Dict[str, Any]]:
    data = lacrm_call("GetPipelineItemsAttachedToContact", {"ContactId": str(contact_id)})
    if isinstance(data, list):
        items: List[Dict[str, Any]] = []
        for pipeline in data:
            if isinstance(pipeline, dict):
                for item in pipeline.get("PipelineItems", []) or []:
                    if isinstance(item, dict):
                        items.append(item)
        return items
    return []


def build_lacrm_timeline(contact_id: str, limit: int = 5) -> Dict[str, Any]:
    notes: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    pipeline_items: List[Dict[str, Any]] = []
    try:
        notes = lacrm_get_notes_attached(contact_id, limit=limit)
    except Exception:
        notes = []
    try:
        tasks = lacrm_get_tasks_attached(contact_id, limit=limit)
    except Exception:
        tasks = []
    try:
        events = lacrm_get_events_attached(contact_id, limit=limit)
    except Exception:
        events = []
    try:
        pipeline_items = lacrm_get_pipeline_items_attached(contact_id)[:limit]
    except Exception:
        pipeline_items = []

    entries: List[Dict[str, Any]] = []
    open_task_count = 0

    for note in notes:
        when = note.get("DateDisplayedInHistory") or note.get("DateCreated") or utcnow_iso()
        entries.append({
            "type": "Note",
            "title": truncate_sentence(note.get("Note") or "CRM note", 110),
            "details": truncate_sentence(note.get("Note") or "", 220),
            "when": when,
            "sort_time": maybe_parse_datetime(when),
            "status": "History note",
        })

    for task in tasks:
        when = task.get("DueDate") or task.get("DateCreated") or utcnow_iso()
        is_complete = bool(task.get("IsCompleted") or task.get("IsComplete"))
        if not is_complete:
            open_task_count += 1
        entries.append({
            "type": "Task",
            "title": truncate_sentence(task.get("Name") or "CRM task", 110),
            "details": truncate_sentence(task.get("Description") or "", 220),
            "when": when,
            "sort_time": maybe_parse_datetime(when),
            "status": "Completed" if is_complete else "Open task",
        })

    for event in events:
        when = event.get("StartDate") or event.get("DateUpdated") or event.get("DateCreated") or utcnow_iso()
        entries.append({
            "type": "Event",
            "title": truncate_sentence(event.get("Name") or "Calendar event", 110),
            "details": truncate_sentence(event.get("Description") or event.get("Location") or "", 220),
            "when": when,
            "sort_time": maybe_parse_datetime(when),
            "status": "Scheduled event",
        })

    for item in pipeline_items:
        when = item.get("LastUpdate") or item.get("DateCreated") or utcnow_iso()
        pipeline_name = (((item.get("PipelineMetaData") or {}).get("Name")) or "Pipeline").strip()
        status_name = (((item.get("StatusMetaData") or {}).get("Name")) or "").strip()
        details = item.get("LastNote") or ""
        entries.append({
            "type": "Pipeline",
            "title": truncate_sentence(f"{pipeline_name}: {status_name}".strip(": "), 110),
            "details": truncate_sentence(details, 220),
            "when": when,
            "sort_time": maybe_parse_datetime(when),
            "status": status_name or pipeline_name,
        })

    entries.sort(key=lambda x: x.get("sort_time") or "", reverse=True)
    trimmed = []
    for entry in entries[:limit]:
        entry = dict(entry)
        entry.pop("sort_time", None)
        trimmed.append(entry)
    return {"entries": trimmed, "open_task_count": open_task_count}


# -----------------------------
# Parsing RingSense responses
# -----------------------------
def find_values_by_key(obj: Any, key_names: List[str]) -> List[Any]:
    matches: List[Any] = []
    lowered = [name.lower() for name in key_names]
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in lowered:
                matches.append(v)
            matches.extend(find_values_by_key(v, key_names))
    elif isinstance(obj, list):
        for item in obj:
            matches.extend(find_values_by_key(item, key_names))
    return matches


def stringify_insight_items(value: Any) -> str:
    lines: List[str] = []
    if isinstance(value, str):
        lines.append(value)
    elif isinstance(value, dict):
        if "value" in value and isinstance(value["value"], str):
            lines.append(value["value"])
        else:
            for item in value.values():
                lines.extend([x for x in stringify_insight_items(item).splitlines() if x.strip()])
    elif isinstance(value, list):
        for item in value:
            lines.extend([x for x in stringify_insight_items(item).splitlines() if x.strip()])
    cleaned = []
    for line in lines:
        line = strip_html_to_text(line)
        if line and line not in cleaned:
            cleaned.append(line)
    return "\n".join(cleaned)


def parse_ringsense_payload(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    summary = ""
    next_steps = ""
    transcript = ""
    summary_candidates = find_values_by_key(payload, ["Summary", "summary"])
    if summary_candidates:
        summary = "\n".join([stringify_insight_items(x) for x in summary_candidates if stringify_insight_items(x).strip()]).strip()
    next_candidates = find_values_by_key(payload, ["NextSteps", "nextSteps", "ActionItems", "actionItems"])
    if next_candidates:
        next_steps = "\n".join([stringify_insight_items(x) for x in next_candidates if stringify_insight_items(x).strip()]).strip()
    transcript_candidates = find_values_by_key(payload, ["Transcript", "transcript", "Transcription", "transcription", "Utterances", "utterances", "sentences"])
    if transcript_candidates:
        transcript = "\n".join([stringify_insight_items(x) for x in transcript_candidates if stringify_insight_items(x).strip()]).strip()
    return summary[:12000], next_steps[:8000], transcript[:40000]


# -----------------------------
# Relationships and routing rules
# -----------------------------
def mark_event_processed(event_uuid: str) -> bool:
    if not event_uuid:
        return True

    try:
        def _write(conn):
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO processed_event_uuids(event_uuid, created_at) VALUES(?, ?)",
                (event_uuid, utcnow_iso()),
            )
            return True

        return run_db_write(_write)
    except sqlite3.IntegrityError:
        return False


def record_relationship(phone: str, contact_id: str) -> None:
    phone = normalize_phone(phone)
    if not phone or not contact_id:
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO caller_relationships(phone, contact_id, score, last_selected_at)
        VALUES(?,?,1,?)
        ON CONFLICT(phone, contact_id) DO UPDATE SET
            score = caller_relationships.score + 1,
            last_selected_at = excluded.last_selected_at
        """,
        (phone, str(contact_id), utcnow_iso()),
    )
    conn.commit()
    conn.close()


def get_relationship_boost(phone: str, contact_id: str) -> int:
    phone = normalize_phone(phone)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT score FROM caller_relationships WHERE phone = ? AND contact_id = ?", (phone, str(contact_id)))
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0
    return min(int(row[0]) * 8, 30)


def get_routing_rule(phone: str) -> Dict[str, Any]:
    phone = normalize_phone(phone)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM routing_rules WHERE phone = ?", (phone,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {
            "phone": phone,
            "label": "",
            "mode": "manual",
            "owner_type": "unknown",
            "default_contact_ids": [],
            "notes": "",
            "updated_at": None,
        }
    data = dict(row)
    try:
        data["default_contact_ids"] = json.loads(data.get("default_contact_ids") or "[]")
    except Exception:
        data["default_contact_ids"] = []
    return data


def upsert_routing_rule(phone: str, mode: str, owner_type: str, default_contact_ids: List[str], label: str = "", notes: str = "") -> Dict[str, Any]:
    phone = normalize_phone(phone)
    if not phone:
        raise ValueError("Phone is required")
    mode = mode if mode in {"manual", "auto"} else "manual"
    owner_type = owner_type if owner_type in {"homeowner", "property_manager", "general", "unknown"} else "unknown"
    payload_ids = [str(x) for x in default_contact_ids if str(x).strip()]
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO routing_rules(phone, label, mode, owner_type, default_contact_ids, notes, updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(phone) DO UPDATE SET
            label = excluded.label,
            mode = excluded.mode,
            owner_type = excluded.owner_type,
            default_contact_ids = excluded.default_contact_ids,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (phone, label, mode, owner_type, json.dumps(payload_ids), notes, utcnow_iso()),
    )
    conn.commit()
    conn.close()
    return get_routing_rule(phone)


# -----------------------------
# Call persistence and scoring
# -----------------------------
def get_call_by_session_id(session_id: str) -> Optional[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM calls WHERE telephony_session_id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_call_by_source_record_id(source_record_id: str) -> Optional[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM calls WHERE source_record_id = ? ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 1", (source_record_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_call_by_id(call_id: str) -> Optional[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
    row = cur.fetchone()
    conn.close()
    return row


def upsert_call(data: Dict[str, Any]) -> str:
    conn = get_db()
    cur = conn.cursor()
    existing_id = data.get("id")
    if not existing_id and data.get("telephony_session_id"):
        cur.execute("SELECT id FROM calls WHERE telephony_session_id = ?", (data["telephony_session_id"],))
        row = cur.fetchone()
        if row:
            existing_id = row[0]
    if not existing_id and data.get("source_record_id"):
        cur.execute("SELECT id FROM calls WHERE source_record_id = ? ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 1", (data["source_record_id"],))
        row = cur.fetchone()
        if row:
            existing_id = row[0]
    call_id = existing_id or str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO calls(
            id, rc_event_uuid, telephony_session_id, source_record_id, caller_phone, internal_phone,
            agent_extension_id, direction, call_time, summary, next_steps, transcript,
            extracted_address, extracted_names, status, raw_json, attached_contact_ids,
            created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            rc_event_uuid=excluded.rc_event_uuid,
            telephony_session_id=COALESCE(excluded.telephony_session_id, calls.telephony_session_id),
            source_record_id=COALESCE(excluded.source_record_id, calls.source_record_id),
            caller_phone=COALESCE(excluded.caller_phone, calls.caller_phone),
            internal_phone=COALESCE(excluded.internal_phone, calls.internal_phone),
            agent_extension_id=COALESCE(excluded.agent_extension_id, calls.agent_extension_id),
            direction=COALESCE(excluded.direction, calls.direction),
            call_time=COALESCE(excluded.call_time, calls.call_time),
            summary=COALESCE(NULLIF(excluded.summary,''), calls.summary),
            next_steps=COALESCE(NULLIF(excluded.next_steps,''), calls.next_steps),
            transcript=COALESCE(NULLIF(excluded.transcript,''), calls.transcript),
            extracted_address=COALESCE(NULLIF(excluded.extracted_address,''), calls.extracted_address),
            extracted_names=COALESCE(NULLIF(excluded.extracted_names,''), calls.extracted_names),
            status=COALESCE(excluded.status, calls.status),
            raw_json=COALESCE(excluded.raw_json, calls.raw_json),
            attached_contact_ids=COALESCE(excluded.attached_contact_ids, calls.attached_contact_ids),
            updated_at=excluded.updated_at
        """,
        (
            call_id,
            data.get("rc_event_uuid"),
            data.get("telephony_session_id"),
            data.get("source_record_id"),
            data.get("caller_phone"),
            data.get("internal_phone"),
            data.get("agent_extension_id"),
            data.get("direction"),
            data.get("call_time"),
            data.get("summary"),
            data.get("next_steps"),
            data.get("transcript"),
            data.get("extracted_address"),
            data.get("extracted_names"),
            data.get("status"),
            data.get("raw_json"),
            data.get("attached_contact_ids"),
            data.get("created_at") or utcnow_iso(),
            utcnow_iso(),
        ),
    )
    conn.commit()
    conn.close()
    return call_id


def get_calls_for_view(view: str = "active") -> List[Dict[str, Any]]:
    view = (view or "active").lower()
    conn = get_db()
    cur = conn.cursor()
    if view == "processed":
        cur.execute(
            "SELECT * FROM calls WHERE COALESCE(hidden,0)=0 AND status IN ('ATTACHED','AUTO_ATTACHED') ORDER BY COALESCE(updated_at, call_time, created_at) DESC"
        )
    else:
        cur.execute(
            "SELECT * FROM calls WHERE COALESCE(hidden,0)=0 AND status IN ('PENDING_REVIEW','PENDING_INSIGHTS') ORDER BY call_time DESC, created_at DESC"
        )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# -----------------------------
# SMS batching and summaries
# -----------------------------
def get_sms_batch_by_id(batch_id: str) -> Optional[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sms_batches WHERE id = ?", (batch_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_or_create_sms_batch(external_phone: str, internal_phone: str, batch_date: str, message_time: str) -> str:
    external_phone = normalize_phone(external_phone)
    internal_phone = normalize_phone(internal_phone)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sms_batches WHERE external_phone = ? AND batch_date = ? ORDER BY created_at DESC LIMIT 1",
        (external_phone, batch_date),
    )
    row = cur.fetchone()
    if row:
        batch_id = row[0]
        cur.execute(
            "UPDATE sms_batches SET internal_phone = COALESCE(NULLIF(?,''), internal_phone), latest_message_at = ?, status = CASE WHEN status = 'ATTACHED' THEN 'OPEN' ELSE status END, updated_at = ? WHERE id = ?",
            (internal_phone, message_time, utcnow_iso(), batch_id),
        )
    else:
        batch_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO sms_batches(id, batch_date, external_phone, internal_phone, latest_message_at, status, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (batch_id, batch_date, external_phone, internal_phone, message_time, "OPEN", utcnow_iso(), utcnow_iso()),
        )
    conn.commit()
    conn.close()
    return batch_id


def append_sms_message(external_phone: str, internal_phone: str, direction: str, body: str, message_time: str, raw_json: Optional[Dict[str, Any]] = None, message_id: Optional[str] = None) -> str:
    batch_date = local_date_string(message_time)
    batch_id = get_or_create_sms_batch(external_phone, internal_phone, batch_date, maybe_parse_datetime(message_time))
    conn = get_db()
    cur = conn.cursor()
    msg_id = str(message_id or uuid.uuid4())
    cur.execute(
        """
        INSERT OR REPLACE INTO sms_messages(id, batch_id, message_time, direction, from_phone, to_phone, body, raw_json, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            msg_id,
            batch_id,
            maybe_parse_datetime(message_time),
            direction,
            normalize_phone(external_phone if direction == "Inbound" else internal_phone),
            normalize_phone(internal_phone if direction == "Inbound" else external_phone),
            body or "",
            safe_json(raw_json or {}),
            utcnow_iso(),
        ),
    )
    conn.commit()
    conn.close()
    return batch_id


def get_sms_messages(batch_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sms_messages WHERE batch_id = ? ORDER BY message_time ASC, created_at ASC", (batch_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def summarize_sms_messages(messages: List[Dict[str, Any]], external_phone: str) -> Tuple[str, str, str, Dict[str, str]]:
    if not messages:
        return "", "", "", {"address": "", "names": ""}
    lines = []
    inbound = []
    outbound = []
    for msg in messages:
        timestamp = fmt_api_time(msg.get("message_time"))
        direction = msg.get("direction") or "Unknown"
        speaker = "Customer" if direction.lower() == "inbound" else "Office"
        body = (msg.get("body") or "").strip()
        lines.append(f"[{timestamp}] {speaker}: {body}")
        if direction.lower() == "inbound":
            inbound.append(body)
        else:
            outbound.append(body)
    transcript = "\n".join(lines)
    entities = extract_entities(transcript)
    first_time = fmt_api_time(messages[0].get("message_time"))
    last_time = fmt_api_time(messages[-1].get("message_time"))
    summary_bits = [
        f"Daily SMS summary for {external_phone}.",
        f"{len(messages)} total messages between {first_time} and {last_time}.",
    ]
    if entities["address"]:
        summary_bits.append(f"Address clue mentioned: {entities['address']}.")
    if entities["names"]:
        summary_bits.append(f"Name clue(s): {entities['names']}.")
    if inbound:
        summary_bits.append(f"Customer topics: {truncate_sentence(' '.join(inbound), 220)}")
    if outbound:
        summary_bits.append(f"Office replies: {truncate_sentence(' '.join(outbound), 220)}")
    next_steps = ""
    last_inbound = inbound[-1] if inbound else ""
    if last_inbound:
        next_steps = f"Latest customer text: {truncate_sentence(last_inbound, 240)}"
    elif outbound:
        next_steps = f"Latest office text: {truncate_sentence(outbound[-1], 240)}"
    summary = " ".join(summary_bits)
    return summary[:6000], next_steps[:2000], transcript[:32000], entities


def fmt_api_time(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return value


def truncate_sentence(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def build_sms_note(batch_row: sqlite3.Row) -> str:
    parts = ["RingCentral Daily SMS Summary", ""]
    parts.append(f"Phone: {batch_row['external_phone']}")
    parts.append(f"Batch date: {batch_row['batch_date']}")
    if batch_row["latest_message_at"]:
        parts.append(f"Latest message: {batch_row['latest_message_at']}")
    if batch_row["extracted_address"]:
        parts.append(f"Extracted address clue: {batch_row['extracted_address']}")
    if batch_row["extracted_names"]:
        parts.append(f"Extracted name clue(s): {batch_row['extracted_names']}")
    if batch_row["summary"]:
        parts.extend(["", "Summary:", batch_row["summary"]])
    if batch_row["next_steps"]:
        parts.extend(["", "Next steps:", batch_row["next_steps"]])
    if batch_row["transcript"]:
        parts.extend(["", "Transcript:", batch_row["transcript"][:12000]])
    return "\n".join(parts).strip()


def finalize_sms_batch(batch_id: str, forced: bool = False) -> Dict[str, Any]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    messages = get_sms_messages(batch_id)
    summary, next_steps, transcript, entities = summarize_sms_messages(messages, row["external_phone"])
    rule = get_routing_rule(row["external_phone"])
    status = "PENDING_REVIEW"
    auto_attached = 0
    attached_ids: List[str] = []
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sms_batches SET summary = ?, next_steps = ?, transcript = ?, extracted_address = ?, extracted_names = ?, status = ?, auto_attached = ?, updated_at = ? WHERE id = ?",
        (summary, next_steps, transcript, entities["address"], entities["names"], status, 0, utcnow_iso(), batch_id),
    )
    conn.commit()
    conn.close()

    if rule["mode"] == "auto" and rule["default_contact_ids"]:
        fresh = get_sms_batch_by_id(batch_id)
        note = build_sms_note(fresh)
        for contact_id in rule["default_contact_ids"]:
            lacrm_create_note(contact_id, note, fresh["latest_message_at"] or fresh["created_at"])
            attached_ids.append(str(contact_id))
            record_relationship(fresh["external_phone"] or "", str(contact_id))
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE sms_batches SET status = ?, attached_contact_ids = ?, auto_attached = 1, updated_at = ? WHERE id = ?",
            ("AUTO_ATTACHED", json.dumps(attached_ids), utcnow_iso(), batch_id),
        )
        conn.commit()
        conn.close()
        auto_attached = 1
        status = "AUTO_ATTACHED"
    result = dict(get_sms_batch_by_id(batch_id))
    result["rule"] = rule
    result["forced"] = forced
    result["auto_attached"] = auto_attached
    return result


def get_sms_batches(view: str = "active", statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if statuses is None:
        statuses = ["ATTACHED", "AUTO_ATTACHED"] if (view or "active").lower() == "processed" else ["OPEN", "PENDING_REVIEW"]
    placeholders = ",".join(["?" for _ in statuses])
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM sms_batches WHERE COALESCE(hidden,0)=0 AND status IN ({placeholders}) ORDER BY COALESCE(updated_at, latest_message_at, created_at) DESC",
        tuple(statuses),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for row in rows:
        row["routing_rule"] = get_routing_rule(row.get("external_phone") or "")
    return rows


def run_end_of_day_batches(target_date: Optional[str] = None) -> Dict[str, Any]:
    target_date = target_date or local_now().date().isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM sms_batches WHERE batch_date <= ? AND status = 'OPEN'", (target_date,))
    batch_ids = [r[0] for r in cur.fetchall()]
    conn.close()
    finalized = []
    for batch_id in batch_ids:
        finalized.append(finalize_sms_batch(batch_id, forced=False)["id"])
    return {"ok": True, "target_date": target_date, "finalized_batch_ids": finalized, "count": len(finalized)}


def sms_scheduler_loop() -> None:
    while True:
        try:
            now = local_now()
            if now.hour > SMS_BATCH_HOUR_LOCAL or (now.hour == SMS_BATCH_HOUR_LOCAL and now.minute >= SMS_BATCH_MINUTE_LOCAL):
                run_end_of_day_batches(now.date().isoformat())
        except Exception as exc:
            print("SMS scheduler error:", exc)
        time.sleep(300)


# -----------------------------
# Message Sync (SMS inbound + outbound)
# -----------------------------
ENABLE_SMS_SYNC = os.getenv("ENABLE_SMS_SYNC", "true").strip().lower() in ("1", "true", "yes", "y", "on")
SMS_SYNC_POLL_SECONDS = int(os.getenv("SMS_SYNC_POLL_SECONDS", "20"))
SMS_SYNC_LOOKBACK_DAYS = int(os.getenv("SMS_SYNC_LOOKBACK_DAYS", "7"))

def get_message_sync_state(scope: str = "sms") -> Dict[str, str]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM message_sync_state WHERE scope = ?", (scope,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"scope": scope, "sync_token": "", "sync_time": ""}

def set_message_sync_state(scope: str, sync_token: str, sync_time: str) -> None:
    def _write(conn):
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO message_sync_state(scope, sync_token, sync_time, updated_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(scope) DO UPDATE SET
                sync_token=excluded.sync_token,
                sync_time=excluded.sync_time,
                updated_at=excluded.updated_at
            """,
            (scope, sync_token, sync_time, utcnow_iso()),
        )

    run_db_write(_write)

def rc_message_sync(sync_type: str, sync_token: Optional[str] = None, date_from: Optional[str] = None) -> Dict[str, Any]:
    """RingCentral Message Sync API.
    We use it to pull BOTH inbound and outbound SMS so the UI shows the full conversation thread.
    """
    token = rc_access_token()
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/extension/~/message-sync"
    params: Dict[str, Any] = {"syncType": sync_type, "messageType": "SMS"}
    if sync_type == "FSync":
        if date_from:
            params["dateFrom"] = date_from
    else:
        if not sync_token:
            raise RuntimeError("ISync requires sync_token")
        params["syncToken"] = sync_token
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def _rc_extract_phone(p: Any) -> str:
    if isinstance(p, dict):
        return p.get("phoneNumber") or p.get("phone") or ""
    if isinstance(p, str):
        return p
    return ""

def ingest_sms_records(records: List[Dict[str, Any]]) -> int:
    ingested = 0
    for rec in records or []:
        try:
            # Deleted/purged messages may only contain id + availability
            if (rec.get("availability") or "Alive") != "Alive":
                continue
            if (rec.get("type") or "").upper() != "SMS":
                continue

            direction = rec.get("direction") or ""
            direction = "Outbound" if direction.lower() == "outbound" else "Inbound"

            from_phone = _rc_extract_phone(rec.get("from") or {})
            to_list = rec.get("to") or []
            to_phone = _rc_extract_phone(to_list[0]) if to_list else ""

            # SMS body is stored in `subject` in RingCentral message records
            body = (rec.get("subject") or "").strip()
            if not body:
                # nothing to display
                continue

            message_time = rec.get("creationTime") or rec.get("lastModifiedTime") or utcnow_iso()
            msg_id = str(rec.get("id") or "")

            if direction == "Outbound":
                internal_phone = from_phone or ""
                # find a recipient that isn't the internal phone
                external_phone = ""
                for t in to_list:
                    pn = _rc_extract_phone(t)
                    if pn and normalize_phone(pn) != normalize_phone(internal_phone):
                        external_phone = pn
                        break
                if not external_phone:
                    external_phone = to_phone
            else:
                external_phone = from_phone
                internal_phone = to_phone

            if not external_phone or not internal_phone:
                continue

            append_sms_message(
                external_phone=external_phone,
                internal_phone=internal_phone,
                direction=direction,
                body=body,
                message_time=message_time,
                raw_json=rec,
                message_id=msg_id or None,
            )
            ingested += 1
        except Exception:
            continue
    return ingested

def sms_message_sync_loop() -> None:
    """Continuously sync SMS (inbound + outbound) using Message Sync API.
    This fills in outbound messages that do NOT trigger the inbound-only instant SMS event.
    """
    if not ENABLE_SMS_SYNC:
        return
    scope = "sms"
    while True:
        try:
            state = get_message_sync_state(scope)
            token = (state.get("sync_token") or "").strip()
            if not token:
                date_from = (datetime.now(timezone.utc) - timedelta(days=SMS_SYNC_LOOKBACK_DAYS)).isoformat().replace("+00:00", "Z")
                resp = rc_message_sync("FSync", date_from=date_from)
            else:
                resp = rc_message_sync("ISync", sync_token=token)

            records = resp.get("records") or []
            ingested = ingest_sms_records(records)

            sync_info = resp.get("syncInfo") or {}
            new_token = sync_info.get("syncToken") or token
            sync_time = sync_info.get("syncTime") or utcnow_iso()
            if new_token:
                set_message_sync_state(scope, new_token, sync_time)

            if ingested:
                print(f"[SMS-SYNC] ingested {ingested} message(s)")
        except Exception as exc:
            print("[SMS-SYNC] error:", exc)

        time.sleep(max(5, SMS_SYNC_POLL_SECONDS))

# -----------------------------
# Scoring shared by calls and sms
# -----------------------------
def build_search_terms(phone: str, address: str, names: str) -> List[Tuple[str, str]]:
    terms: List[Tuple[str, str]] = []
    if phone:
        for variant in phone_search_variants(phone):
            terms.append(("phone", variant))
    if address:
        terms.append(("address", address))
    if names:
        for name in [n.strip() for n in names.split(",") if n.strip()][:3]:
            terms.append(("name", name))
    dedup = []
    seen = set()
    for t in terms:
        if t[1] and t not in seen:
            dedup.append(t)
            seen.add(t)
    return dedup


def score_contacts_from_signals(phone: str, address: str, names: str) -> List[Dict[str, Any]]:
    scored: Dict[str, Dict[str, Any]] = {}
    rule = get_routing_rule(phone)
    default_ids = [str(x) for x in rule.get("default_contact_ids", [])]
    phone_variants = phone_search_variants(phone)
    for term_type, term in build_search_terms(phone, address, names):
        search_term = term
        if not search_term:
            continue
        try:
            contacts = lacrm_get_contacts(search_term)
        except Exception:
            contacts = []
        for contact in contacts:
            contact_id = str(contact.get("ContactId") or "")
            if not contact_id:
                continue
            if contact_id not in scored:
                scored[contact_id] = {"contact": contact, "score": 0, "reasons": []}
            blob = flatten_contact_text(contact)
            if term_type == "phone":
                scored[contact_id]["score"] += 30
                scored[contact_id]["reasons"].append(f"phone search hit on {term}")
                for p in get_contact_phones(contact):
                    if any(phones_match(p, variant) for variant in phone_variants):
                        scored[contact_id]["score"] += 45
                        scored[contact_id]["reasons"].append("exact phone variation matched")
                        break
            elif term_type == "address":
                addr_ratio = ratio(address, blob)
                add_score = 25 if addr_ratio >= 45 else 10
                scored[contact_id]["score"] += add_score
                scored[contact_id]["reasons"].append(f"address clue ({addr_ratio}% similarity)")
            elif term_type == "name":
                name_ratio = ratio(term, blob)
                add_score = 18 if name_ratio >= 45 else 8
                scored[contact_id]["score"] += add_score
                scored[contact_id]["reasons"].append(f"name clue {term}")

    for contact_id, data in scored.items():
        boost = get_relationship_boost(phone, contact_id)
        if boost:
            data["score"] += boost
            data["reasons"].append("prior manual selections from this caller")
        if contact_id in default_ids:
            data["score"] += 35 if rule["mode"] == "manual" else 60
            data["reasons"].append("saved routing preference for this number")

    output: List[Dict[str, Any]] = []
    for contact_id, data in scored.items():
        contact = data["contact"]
        output.append(
            {
                "contact_id": contact_id,
                "name": get_display_name(contact),
                "address": get_best_address_display(contact),
                "phones": get_contact_phones(contact),
                "score": data["score"],
                "reasons": list(dict.fromkeys(data["reasons"]))[:5],
                "raw": contact,
            }
        )
    output.sort(key=lambda x: (-x["score"], str(x.get("name") or "")))
    return output[:12]


def search_candidates_for_call(call_row: sqlite3.Row) -> List[Dict[str, Any]]:
    return score_contacts_from_signals(call_row["caller_phone"] or "", call_row["extracted_address"] or "", call_row["extracted_names"] or "")


def search_candidates_for_sms(batch_row: sqlite3.Row) -> List[Dict[str, Any]]:
    return score_contacts_from_signals(batch_row["external_phone"] or "", batch_row["extracted_address"] or "", batch_row["extracted_names"] or "")


def build_call_note(call_row: sqlite3.Row) -> str:
    row = dict(call_row) if not isinstance(call_row, dict) else call_row
    is_voicemail = str(row.get("item_type") or "call").lower() == "voicemail"
    parts = ["RingCentral Voicemail Summary" if is_voicemail else "RingCentral AI Call Summary", ""]
    if row.get("call_time"):
        parts.append(f"{'Voicemail time' if is_voicemail else 'Call time'} (UTC): {row['call_time']}")
    if row.get("direction"):
        parts.append(f"Direction: {row['direction']}")
    if row.get("caller_phone"):
        parts.append(f"Caller: {row['caller_phone']}")
    if row.get("caller_name"):
        parts.append(f"Caller name: {row['caller_name']}")
    if row.get("internal_phone"):
        parts.append(f"Internal line: {row['internal_phone']}")
    if not is_voicemail and row.get("telephony_session_id"):
        parts.append(f"Telephony session: {row['telephony_session_id']}")
    if row.get("source_record_id"):
        parts.append(f"RingSense record: {row['source_record_id']}")
    if is_voicemail and row.get("voicemail_message_id"):
        parts.append(f"Voicemail message ID: {row['voicemail_message_id']}")
    if is_voicemail and row.get("voicemail_duration"):
        parts.append(f"Voicemail duration: {row['voicemail_duration']} second(s)")
    if is_voicemail and row.get("voicemail_transcription_status"):
        parts.append(f"Voicemail transcription status: {row['voicemail_transcription_status']}")
    if row.get("extracted_address"):
        parts.append(f"Extracted address clue: {row['extracted_address']}")
    if row.get("extracted_names"):
        parts.append(f"Extracted name clue(s): {row['extracted_names']}")
    if row.get("summary"):
        parts.extend(["", "Summary:", row["summary"]])
    if row.get("next_steps"):
        parts.extend(["", "Next steps:", row["next_steps"]])
    if row.get("transcript"):
        parts.extend(["", "Transcript:", row["transcript"][:12000]])
    return "\n".join(parts).strip()


# -----------------------------
# Incoming ringing HUD helpers
# -----------------------------
def extract_status_values(value: Any) -> List[str]:
    found: List[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("statusCode"), str):
            found.append(value["statusCode"])
        status = value.get("status")
        if isinstance(status, dict) and isinstance(status.get("code"), str):
            found.append(status["code"])
        if isinstance(status, str):
            found.append(status)
        for item in value.values():
            found.extend(extract_status_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(extract_status_values(item))
    return list(dict.fromkeys([x for x in found if x]))


def extract_session_status_code(body: Dict[str, Any]) -> str:
    values = [x.lower() for x in extract_status_values(body)]
    priorities = [
        ("disconnected", "Disconnected"),
        ("proceeding", "Proceeding"),
        ("setup", "Setup"),
        ("answered", "Answered"),
        ("connected", "Connected"),
        ("hold", "Hold"),
    ]
    for needle, label in priorities:
        if any(needle in value for value in values):
            return label
    return values[0].title() if values else "Unknown"


def get_active_hud_call_row() -> Optional[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM calls
        WHERE COALESCE(hidden,0)=0
          AND COALESCE(hud_dismissed_at,'') = ''
          AND status IN ('RINGING', 'LIVE')
        ORDER BY COALESCE(updated_at, call_time, created_at) DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    return row


def dismiss_hud_call(call_id: str) -> None:
    def _write(conn):
        cur = conn.cursor()
        cur.execute(
            "UPDATE calls SET hud_dismissed_at = ?, updated_at = ? WHERE id = ?",
            (utcnow_iso(), utcnow_iso(), call_id),
        )

    run_db_write(_write)


def build_hud_payload() -> Optional[Dict[str, Any]]:
    row = get_active_hud_call_row()
    if not row:
        return None
    row_dict = dict(row)
    cache_key = f"hud::{row_dict.get('id')}::{row_dict.get('updated_at')}"
    cached = HUD_CONTEXT_CACHE.get(cache_key)
    if cached and cached.get("expires_at", 0) > time.time():
        return cached.get("payload")

    phone = row_dict.get("caller_phone") or ""
    candidates = score_contacts_from_signals(phone, row_dict.get("extracted_address") or "", row_dict.get("extracted_names") or "")
    top_candidate = candidates[0] if candidates else None
    history = []
    open_task_count = 0
    if top_candidate and top_candidate.get("contact_id"):
        timeline = build_lacrm_timeline(str(top_candidate["contact_id"]), limit=5)
        history = timeline.get("entries", [])
        open_task_count = timeline.get("open_task_count", 0)

    payload = {
        "id": row_dict.get("id"),
        "telephony_session_id": row_dict.get("telephony_session_id"),
        "caller_phone": phone,
        "internal_phone": row_dict.get("internal_phone"),
        "call_time": row_dict.get("call_time"),
        "direction": row_dict.get("direction"),
        "status": row_dict.get("status"),
        "last_status_code": row_dict.get("last_status_code") or row_dict.get("status"),
        "candidates": candidates[:5],
        "top_contact": top_candidate,
        "history": history,
        "open_task_count": open_task_count,
        "routing_rule": get_routing_rule(phone),
    }
    HUD_CONTEXT_CACHE[cache_key] = {"expires_at": time.time() + 45, "payload": payload}
    return payload


# -----------------------------
# Event handlers
# -----------------------------
def get_attachment_by_type(attachments: List[Dict[str, Any]], desired_type: str) -> Optional[Dict[str, Any]]:
    for attachment in attachments or []:
        if str((attachment or {}).get("type") or "").lower() == desired_type.lower():
            return attachment
    return None


def summarize_voicemail(caller_phone: str, caller_name: str, created_time: str, duration: int, transcript_text: str, subject_text: str) -> Tuple[str, str, Dict[str, str]]:
    text_blob = "\n".join([transcript_text or "", subject_text or "", caller_name or "", caller_phone or ""]).strip()
    entities = extract_entities(text_blob)
    who = caller_name or caller_phone or "unknown caller"
    bits = [f"Voicemail from {who}."]
    if created_time:
        bits.append(f"Received {fmt_api_time(created_time)}.")
    if duration:
        bits.append(f"Duration: {duration} seconds.")
    if entities["address"]:
        bits.append(f"Address clue mentioned: {entities['address']}.")
    if entities["names"]:
        bits.append(f"Name clue(s): {entities['names']}.")
    preview_source = transcript_text or subject_text
    if preview_source:
        bits.append(f"Message preview: {truncate_sentence(preview_source, 260)}")
    next_steps = "Review and return the voicemail."
    if entities["address"]:
        next_steps = f"Review voicemail and follow up on {entities['address']}."
    elif entities["names"]:
        next_steps = f"Review voicemail and follow up with {entities['names']}."
    return " ".join(bits)[:6000], next_steps[:2000], entities


def should_auto_attach_voicemail(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    top = candidates[0]
    second_score = int((candidates[1] or {}).get("score") or 0) if len(candidates) > 1 else 0
    reasons = " | ".join(top.get("reasons") or []).lower()
    exact_phone = "exact phone variation matched" in reasons
    strong = int(top.get("score") or 0) >= 95 or (exact_phone and int(top.get("score") or 0) >= 75)
    if len(candidates) == 1 and strong:
        return top
    if strong and int(top.get("score") or 0) >= second_score + 25:
        return top
    return None


def attach_call_record(call_id: str, contact_ids: List[str], auto: bool = False) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise RuntimeError("Call record not found")
    attached_ids = parse_json_list(row["attached_contact_ids"])
    if attached_ids:
        return {"ok": True, "attached": [{"contact_id": cid} for cid in attached_ids], "already_attached": True}
    note = build_call_note(row)
    results = []
    for contact_id in contact_ids:
        result = lacrm_create_note(contact_id, note, row["call_time"] or utcnow_iso())
        results.append({"contact_id": contact_id, "result": result})
        record_relationship(row["caller_phone"] or "", contact_id)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE calls SET status = ?, attached_contact_ids = ?, updated_at = ? WHERE id = ?",
        ("AUTO_ATTACHED" if auto else "ATTACHED", json.dumps(contact_ids), utcnow_iso(), call_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "attached": results, "auto": auto}


def handle_voicemail_event(payload: Dict[str, Any]) -> None:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
    if not body:
        return
    message_id = str(body.get("id") or "")
    from_ep = body.get("from") or {}
    to_eps = body.get("to") or []
    if not isinstance(to_eps, list):
        to_eps = [to_eps]
    caller_phone = normalize_phone(from_ep.get("phoneNumber") or "")
    caller_name = (from_ep.get("name") or "").strip()
    internal_phone = normalize_phone((to_eps[0] or {}).get("phoneNumber") or "") if to_eps else ""
    event_time = body.get("creationTime") or payload.get("timestamp") or utcnow_iso()
    transcription_status = str(body.get("vmTranscriptionStatus") or "Unknown")
    subject_text = strip_html_to_text(body.get("subject") or "")
    attachments = body.get("attachments") or []
    recording_attachment = get_attachment_by_type(attachments, "AudioRecording")
    transcription_attachment = get_attachment_by_type(attachments, "AudioTranscription")
    duration = int((recording_attachment or {}).get("vmDuration") or 0)
    transcript_text = ""
    if transcription_attachment and str(transcription_status).lower() in {"completed", "completedpartially", "notavailable", "failed", "timedout", "unknown"}:
        try:
            transcript_text = rc_fetch_text_attachment(transcription_attachment.get("uri") or "")
        except Exception as exc:
            print("Voicemail transcription fetch failed:", exc)
    if not transcript_text:
        transcript_text = subject_text

    # If transcription is not ready yet (often arrives later), poll message-store until the AudioTranscription attachment appears.
    if str(transcription_status).lower() in {"inprogress", "in_progress", "processing"} or not transcription_attachment:
        try:
            voicemail_transcription_poll_async(message_id)
        except Exception:
            pass

    # If voicemail transcription exists but wasn't available yet, retry a few times in the background.

    if transcription_attachment and (not transcript_text or transcript_text == subject_text):
        try:
            voicemail_transcription_retry_async(message_id, transcription_attachment.get("uri") or "")
        except Exception:
            pass

    summary, next_steps, entities = summarize_voicemail(caller_phone, caller_name, event_time, duration, transcript_text, subject_text)
    call_id = upsert_call({
        "rc_event_uuid": payload.get("uuid"),
        "source_record_id": message_id,
        "caller_phone": caller_phone,
        "internal_phone": internal_phone,
        "direction": body.get("direction") or "Inbound",
        "call_time": maybe_parse_datetime(event_time),
        "summary": summary,
        "next_steps": next_steps,
        "transcript": transcript_text,
        "extracted_address": entities["address"],
        "extracted_names": entities["names"],
        "status": "PENDING_REVIEW",
        "raw_json": safe_json(payload),
    })

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE calls
        SET item_type = 'voicemail',
            caller_name = ?,
            voicemail_message_id = ?,
            voicemail_transcription_status = ?,
            voicemail_duration = ?,
            voicemail_recording_uri = ?,
            voicemail_transcription_uri = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (caller_name, message_id, transcription_status, duration or None, (recording_attachment or {}).get("uri"), (transcription_attachment or {}).get("uri"), utcnow_iso(), call_id),
    )
    conn.commit()
    conn.close()

    row = get_call_by_id(call_id)
    if not row or parse_json_list(row["attached_contact_ids"]):
        return

    rule = get_routing_rule(caller_phone)
    if rule["mode"] == "auto" and rule["default_contact_ids"]:
        try:
            attach_call_record(call_id, [str(x) for x in rule["default_contact_ids"]], auto=True)
        except Exception as exc:
            print("Voicemail auto-attach failed via routing rule:", exc)
        return

    candidates = search_candidates_for_call(row)
    top = should_auto_attach_voicemail(candidates)
    if top:
        try:
            attach_call_record(call_id, [str(top["contact_id"])], auto=True)
        except Exception as exc:
            print("Voicemail auto-attach failed via score:", exc)


def extract_external_and_internal(body: Dict[str, Any]) -> Tuple[str, str, str]:
    caller_phone = ""
    internal_phone = ""
    agent_extension_id = ""
    parties = body.get("parties", []) or []
    for party in parties:
        to_ep = party.get("to") or {}
        from_ep = party.get("from") or {}
        if not caller_phone and from_ep.get("phoneNumber") and not from_ep.get("extensionId"):
            caller_phone = normalize_phone(from_ep.get("phoneNumber"))
        if not caller_phone and to_ep.get("phoneNumber") and not to_ep.get("extensionId"):
            caller_phone = normalize_phone(to_ep.get("phoneNumber"))
        if not internal_phone and to_ep.get("phoneNumber") and to_ep.get("extensionId"):
            internal_phone = normalize_phone(to_ep.get("phoneNumber"))
            agent_extension_id = str(to_ep.get("extensionId"))
        if not internal_phone and from_ep.get("phoneNumber") and from_ep.get("extensionId"):
            internal_phone = normalize_phone(from_ep.get("phoneNumber"))
            agent_extension_id = str(from_ep.get("extensionId"))
        if not agent_extension_id and party.get("extensionId"):
            agent_extension_id = str(party.get("extensionId"))
    return caller_phone, internal_phone, agent_extension_id


def handle_telephony_event(payload: Dict[str, Any]) -> None:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
    session_id = body.get("telephonySessionId")
    if not session_id:
        return
    caller_phone, internal_phone, agent_extension_id = extract_external_and_internal(body)
    call_time = body.get("eventTime") or payload.get("timestamp") or utcnow_iso()
    session_status = extract_session_status_code(body)
    direction = body.get("direction") or ""
    is_inbound = str(direction).lower() == "inbound"

    live_status = "RINGING"
    if session_status in {"Answered", "Connected", "Hold"}:
        live_status = "LIVE"

    status = live_status if session_status != "Disconnected" else "PENDING_INSIGHTS"
    call_id = upsert_call(
        {
            "rc_event_uuid": payload.get("uuid"),
            "telephony_session_id": session_id,
            "caller_phone": caller_phone,
            "internal_phone": internal_phone,
            "agent_extension_id": agent_extension_id,
            "direction": direction,
            "call_time": maybe_parse_datetime(call_time),
            "status": status,
            "raw_json": safe_json(payload),
        }
    )

    conn = get_db()
    cur = conn.cursor()
    if session_status == "Disconnected":
        cur.execute(
            "UPDATE calls SET item_type = 'call', last_status_code = ?, updated_at = ? WHERE id = ?",
            (session_status, utcnow_iso(), call_id),
        )
    else:
        # keep ringing HUD available until the call ends or the user dismisses it
        cur.execute(
            "UPDATE calls SET item_type = 'call', last_status_code = ?, hud_dismissed_at = CASE WHEN status IN ('RINGING','LIVE') THEN COALESCE(hud_dismissed_at,'') ELSE hud_dismissed_at END, updated_at = ? WHERE id = ?",
            (session_status, utcnow_iso(), call_id),
        )
        if not is_inbound and not caller_phone:
            cur.execute(
                "UPDATE calls SET status = ?, updated_at = ? WHERE id = ?",
                ("PENDING_INSIGHTS", utcnow_iso(), call_id),
            )
    conn.commit()
    conn.close()

    # If RingSense insights event is delayed/missing, proactively resolve ACE transcript/summary via call log + insights.
    if session_status == "Disconnected":
        try:
            ace_enrich_call_from_session_async(call_id, session_id, str(call_time))
        except Exception:
            pass


def handle_ringsense_event(payload: Dict[str, Any]) -> None:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
    source_session_id = body.get("sourceSessionId")
    source_record_id = body.get("sourceRecordId")
    summary, next_steps, transcript = parse_ringsense_payload(body)
    if source_record_id and (not summary or not transcript):
        try:
            fetched = rc_fetch_insights(source_record_id)
            f_summary, f_next_steps, f_transcript = parse_ringsense_payload(fetched)
            summary = f_summary or summary
            next_steps = f_next_steps or next_steps
            transcript = f_transcript or transcript
        except Exception:
            pass
    entities = extract_entities("\n".join([summary or "", next_steps or "", transcript or ""]))
    existing = get_call_by_session_id(source_session_id) if source_session_id else None
    upsert_call(
        {
            "id": str(existing["id"]) if existing else None,
            "rc_event_uuid": payload.get("uuid"),
            "telephony_session_id": source_session_id,
            "source_record_id": source_record_id,
            "call_time": maybe_parse_datetime(body.get("recordingStartTime") or payload.get("timestamp")),
            "direction": body.get("callDirection"),
            "summary": summary,
            "next_steps": next_steps,
            "transcript": transcript,
            "extracted_address": entities["address"],
            "extracted_names": entities["names"],
            "status": "PENDING_REVIEW",
            "raw_json": safe_json(payload),
        }
    )


def handle_sms_event(payload: Dict[str, Any]) -> None:
    body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
    subject = body.get("subject") or body.get("body") or ""
    from_ep = body.get("from") or {}
    to_eps = body.get("to") or []
    if not isinstance(to_eps, list):
        to_eps = [to_eps]
    external_phone = normalize_phone(from_ep.get("phoneNumber") if from_ep.get("phoneNumber") else "")
    internal_phone = ""
    direction = body.get("direction") or "Inbound"
    if direction.lower() == "outbound":
        internal_phone = normalize_phone(from_ep.get("phoneNumber") or "")
        if to_eps:
            external_phone = normalize_phone((to_eps[0] or {}).get("phoneNumber") or "")
    else:
        if to_eps:
            internal_phone = normalize_phone((to_eps[0] or {}).get("phoneNumber") or "")
    if not external_phone:
        return
    batch_id = append_sms_message(
        external_phone=external_phone,
        internal_phone=internal_phone,
        direction=direction,
        body=subject,
        message_time=body.get("creationTime") or payload.get("timestamp") or utcnow_iso(),
        raw_json=payload,
        message_id=str(body.get("id") or uuid.uuid4()),
    )
    row = get_sms_batch_by_id(batch_id)
    if row and get_routing_rule(external_phone)["mode"] == "auto":
        finalize_sms_batch(batch_id, forced=True)


def process_ringcentral_payload(payload: Dict[str, Any]) -> None:
    event_uuid = payload.get("uuid") or ""
    if event_uuid and not mark_event_processed(event_uuid):
        return
    event_name = str(payload.get("event") or "")
    try:
        if "/telephony/sessions" in event_name:
            handle_telephony_event(payload)
        elif "/ai/ringsense/" in event_name and event_name.endswith("/insights"):
            handle_ringsense_event(payload)
        elif "/message-store" in event_name and ("SMS" in event_name or "SMS" in safe_json(payload) or '"type": "SMS"' in safe_json(payload)):
            handle_sms_event(payload)
        elif "/voicemail" in event_name or '"type": "VoiceMail"' in safe_json(payload) or '"type":"VoiceMail"' in safe_json(payload):
            handle_voicemail_event(payload)
    except Exception as exc:
        print("Error processing webhook:", exc)


# -----------------------------
# API models
# -----------------------------
class AttachRequest(BaseModel):
    contact_ids: List[str]


class TrashRequest(BaseModel):
    reason: str = "Spam / promotional / not useful"


class TaskCreateRequest(BaseModel):
    contact_id: str
    name: str
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    description: str = ""


class RoutingRuleUpdate(BaseModel):
    phone: str
    mode: str = "manual"
    owner_type: str = "unknown"
    default_contact_ids: List[str] = []
    label: str = ""
    notes: str = ""


class DemoSmsRequest(BaseModel):
    external_phone: str
    internal_phone: str = ""
    messages: List[Dict[str, str]]


# -----------------------------
# Web routes
# -----------------------------
@app.on_event("startup")
def startup_event() -> None:
    init_db()
    threading.Thread(target=sms_scheduler_loop, daemon=True).start()
    threading.Thread(target=sms_message_sync_loop, daemon=True).start()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "time": utcnow_iso()}


@app.post("/webhooks/ringcentral")
async def ringcentral_webhook(request: Request):
    validation_header = request.headers.get("Validation-Token") or request.headers.get("validation-token")
    if RC_WEBHOOK_SHARED_SECRET:
        provided_secret = request.query_params.get("secret", "")
        if provided_secret != RC_WEBHOOK_SHARED_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized")
    # RingCentral webhook verification expects the exact Validation-Token header
    # to be echoed back; it is not a pre-shared secret and should not be compared
    # to a configured env value.
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if payload:
        threading.Thread(target=process_ringcentral_payload, args=(payload,), daemon=True).start()
    response = JSONResponse({"accepted": True})
    if validation_header:
        response.headers["Validation-Token"] = validation_header
    return response


@app.get("/api/calls")
def api_calls(view: str = "active") -> List[Dict[str, Any]]:
    return get_calls_for_view(view=view)


@app.get("/api/calls/{call_id}")
def api_call_detail(call_id: str) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    return dict(row)


@app.get("/api/calls/{call_id}/candidates")
def api_call_candidates(call_id: str) -> List[Dict[str, Any]]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    return search_candidates_for_call(row)


@app.get("/api/sms/batches")
def api_sms_batches(view: str = "active") -> List[Dict[str, Any]]:
    return get_sms_batches(view=view)


@app.get("/api/sms/batches/{batch_id}")
def api_sms_batch_detail(batch_id: str) -> Dict[str, Any]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    data = dict(row)
    data["messages"] = get_sms_messages(batch_id)
    data["routing_rule"] = get_routing_rule(row["external_phone"] or "")
    return data


@app.get("/api/sms/batches/{batch_id}/candidates")
def api_sms_batch_candidates(batch_id: str) -> List[Dict[str, Any]]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    return search_candidates_for_sms(row)


@app.post("/api/sms/batches/{batch_id}/force_batch")
def api_sms_force_batch(batch_id: str) -> Dict[str, Any]:
    return finalize_sms_batch(batch_id, forced=True)


@app.post("/api/sms/batches/{batch_id}/attach")
def api_sms_attach(batch_id: str, payload: AttachRequest) -> Dict[str, Any]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    if not payload.contact_ids:
        raise HTTPException(status_code=400, detail="No contact_ids supplied")
    fresh = finalize_sms_batch(batch_id, forced=True)
    row = get_sms_batch_by_id(batch_id)
    note = build_sms_note(row)
    results = []
    for contact_id in payload.contact_ids:
        result = lacrm_create_note(contact_id, note, row["latest_message_at"] or row["created_at"])
        results.append({"contact_id": contact_id, "result": result})
        record_relationship(row["external_phone"] or "", contact_id)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sms_batches SET status = ?, attached_contact_ids = ?, updated_at = ? WHERE id = ?",
        ("ATTACHED", json.dumps(payload.contact_ids), utcnow_iso(), batch_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "attached": results, "batch": fresh}


@app.post("/api/calls/{call_id}/trash")
def api_trash_call(call_id: str, payload: TrashRequest) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE calls SET hidden = 1, status = ?, trash_reason = ?, trashed_at = ?, updated_at = ? WHERE id = ?",
        ("TRASHED", payload.reason, utcnow_iso(), utcnow_iso(), call_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "id": call_id, "reason": payload.reason}


@app.post("/api/sms/batches/{batch_id}/trash")
def api_trash_sms(batch_id: str, payload: TrashRequest) -> Dict[str, Any]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sms_batches SET hidden = 1, status = ?, trash_reason = ?, trashed_at = ?, updated_at = ? WHERE id = ?",
        ("TRASHED", payload.reason, utcnow_iso(), utcnow_iso(), batch_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "id": batch_id, "reason": payload.reason}


@app.get("/api/lacrm/users")
def api_lacrm_users() -> List[Dict[str, Any]]:
    users = lacrm_get_users()
    out = []
    for user in users:
        first = (user.get("FirstName") or "").strip()
        last = (user.get("LastName") or "").strip()
        full = (first + " " + last).strip() or (user.get("Email") or user.get("UserId") or "User")
        out.append({
            "user_id": str(user.get("UserId") or ""),
            "name": full,
            "email": user.get("Email") or "",
            "raw": user,
        })
    return out


@app.post("/api/calls/{call_id}/task")
def api_create_call_task(call_id: str, payload: TaskCreateRequest) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    task = lacrm_create_task(payload.name, payload.contact_id, payload.due_date, payload.assigned_to, payload.description)
    return {"ok": True, "task": task}


@app.post("/api/sms/batches/{batch_id}/task")
def api_create_sms_task(batch_id: str, payload: TaskCreateRequest) -> Dict[str, Any]:
    row = get_sms_batch_by_id(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="SMS batch not found")
    task = lacrm_create_task(payload.name, payload.contact_id, payload.due_date, payload.assigned_to, payload.description)
    return {"ok": True, "task": task}


@app.get("/api/routing-rules")
def api_get_routing_rule(phone: str) -> Dict[str, Any]:
    return get_routing_rule(phone)


@app.post("/api/routing-rules")
def api_upsert_routing_rule(payload: RoutingRuleUpdate) -> Dict[str, Any]:
    try:
        return upsert_routing_rule(payload.phone, payload.mode, payload.owner_type, payload.default_contact_ids, payload.label, payload.notes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/hud/incoming-call")
def api_hud_incoming_call() -> Dict[str, Any]:
    payload = build_hud_payload()
    return {"active": bool(payload), "item": payload}


@app.post("/api/hud/incoming-call/{call_id}/dismiss")
def api_hud_dismiss(call_id: str) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Incoming call not found")
    dismiss_hud_call(call_id)
    return {"ok": True, "id": call_id}


@app.get("/api/lacrm/search")
def api_lacrm_search(q: str) -> List[Dict[str, Any]]:
    if not q.strip():
        return []
    results = lacrm_get_contacts(q.strip())
    output = []
    for item in results[:15]:
        output.append(
            {
                "contact_id": str(item.get("ContactId") or ""),
                "name": get_display_name(item),
                "address": get_best_address_display(item),
                "phones": get_contact_phones(item),
                "raw": item,
            }
        )
    return output


@app.post("/api/calls/{call_id}/attach")
def api_attach(call_id: str, payload: AttachRequest) -> Dict[str, Any]:
    row = get_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    if not payload.contact_ids:
        raise HTTPException(status_code=400, detail="No contact_ids supplied")
    return attach_call_record(call_id, payload.contact_ids, auto=False)


@app.post("/api/admin/create_subscription")
def api_create_subscription(mode: str = "configured") -> Dict[str, Any]:
    try:
        return rc_create_subscription(mode=mode)
    except Exception as exc:
        message = str(exc)
        status = 400 if "RingCentral subscription failed" in message or "No RingCentral event filters" in message else 500
        raise HTTPException(status_code=status, detail=message)


@app.post("/api/admin/run_sms_eod")
def api_run_sms_eod() -> Dict[str, Any]:
    return run_end_of_day_batches()


@app.get("/api/admin/subscription_preview")
def api_subscription_preview(mode: str = "configured") -> Dict[str, Any]:
    return {
        "mode": mode,
        "address": build_rc_webhook_address(),
        "eventFilters": build_rc_event_filters(mode),
        "config": {
            "ENABLE_CALL_SUBSCRIPTION": ENABLE_CALL_SUBSCRIPTION,
            "ENABLE_SMS_SUBSCRIPTION": ENABLE_SMS_SUBSCRIPTION,
            "ENABLE_VOICEMAIL_SUBSCRIPTION": ENABLE_VOICEMAIL_SUBSCRIPTION,
            "ENABLE_RINGSENSE_SUBSCRIPTION": ENABLE_RINGSENSE_SUBSCRIPTION,
            "CALLS_REQUIRE_RECORDINGS": CALLS_REQUIRE_RECORDINGS,
        },
    }


@app.post("/api/test/sms_seed")
def api_test_sms_seed(payload: DemoSmsRequest) -> Dict[str, Any]:
    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages are required")
    batch_id = ""
    for msg in payload.messages:
        batch_id = append_sms_message(
            payload.external_phone,
            payload.internal_phone,
            msg.get("direction", "Inbound"),
            msg.get("body", ""),
            msg.get("message_time") or utcnow_iso(),
            {"seeded": True, **msg},
        )
    finalize_sms_batch(batch_id, forced=True)
    return {"ok": True, "batch_id": batch_id}


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
