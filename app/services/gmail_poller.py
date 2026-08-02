"""Read-only Gmail invoice poller.

Uses the per-mailbox refresh tokens saved by ``authorize_gmail.py`` to pull PDF
attachments (invoices) from every label/folder into the invoice drop zone. It
NEVER sends, moves, reads-as-read, or deletes anything -- the OAuth scope is
gmail.readonly, so it physically cannot. Idempotent: a message+attachment already
downloaded (same filename) is skipped, and the invoice importer dedups again by
(vendor, invoice #).

After a poll, the PDFs land in data/imports/invoices/ and are processed by the
invoice importer (parse_ace_pdf for Ace, the LLM extractor for other layouts).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
DROP = ROOT / 'data' / 'imports' / 'invoices'

# Broad but invoice-relevant: any message that carries a PDF attachment. The
# downstream parser decides what is actually an invoice; non-invoice PDFs simply
# do not parse and are ignored.
DEFAULT_QUERY = 'has:attachment filename:pdf'


def _env(name: str, default: str = '') -> str:
    envf = ROOT / '.env'
    if envf.exists():
        for line in envf.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return os.environ.get(name, default)


def _token_path(mailbox: str) -> Path:
    return ROOT / '.secrets' / f"gmail_token_{mailbox.split('@')[0]}.json"


def _service(token_path: Path):
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def _iter_parts(payload: dict):
    yield payload
    for part in payload.get('parts', []) or []:
        yield from _iter_parts(part)


def _safe(name: str) -> str:
    return ''.join(c if c.isalnum() or c in ('.', '-', '_') else '_' for c in name)


def pull_mailbox_pdfs(mailbox: str, query: str = DEFAULT_QUERY, max_messages: int = 1000) -> list:
    """Download new PDF attachments from one mailbox into the drop zone. Returns
    the list of newly-saved file paths (already-present files are skipped)."""
    token = _token_path(mailbox)
    if not token.exists():
        raise FileNotFoundError(f'{mailbox} not authorized; run authorize_gmail.py first ({token.name} missing)')
    svc = _service(token)
    DROP.mkdir(parents=True, exist_ok=True)

    saved: list = []
    page = None
    fetched = 0
    prefix = _safe(mailbox.split('@')[0])
    while fetched < max_messages:
        resp = svc.users().messages().list(userId='me', q=query, pageToken=page, maxResults=100).execute()
        for meta in resp.get('messages', []):
            fetched += 1
            msg = svc.users().messages().get(userId='me', id=meta['id'], format='full').execute()
            for part in _iter_parts(msg.get('payload', {})):
                fn = part.get('filename', '')
                att_id = (part.get('body') or {}).get('attachmentId')
                if not (fn.lower().endswith('.pdf') and att_id):
                    continue
                out = DROP / f"{prefix}_{meta['id']}_{_safe(fn)}"
                if out.exists():
                    continue
                att = svc.users().messages().attachments().get(
                    userId='me', messageId=meta['id'], id=att_id).execute()
                out.write_bytes(base64.urlsafe_b64decode(att['data']))
                saved.append(str(out))
        page = resp.get('nextPageToken')
        if not page:
            break
    return saved


def poll_all(query: str = DEFAULT_QUERY, max_messages: int = 1000) -> dict:
    """Poll every configured mailbox. Returns {mailbox: [new_file_paths]}."""
    mailboxes = [m.strip() for m in _env('GMAIL_MAILBOXES').split(',') if m.strip()]
    return {mb: pull_mailbox_pdfs(mb, query=query, max_messages=max_messages) for mb in mailboxes}
