"""Provider-agnostic LLM client for the platform (Claude / Anthropic by default).

Reads its key from the platform's own .env (loaded here, isolated per project).
Used by the invoice extractor to read *any* vendor's PDF layout -- the general
path behind the deterministic Heritage/Ace parsers.

Quality-first for financial extraction: Sonnet is the default. Swap providers or
models via env (UPS_LLM_MODEL) without touching callers.
"""
from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    envf = _ROOT / '.env'
    if not envf.exists():
        return
    for line in envf.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DEFAULT_MODEL = os.environ.get('UPS_LLM_MODEL', 'claude-sonnet-5')


def available() -> bool:
    return bool(os.environ.get('ANTHROPIC_API_KEY'))


def _client():
    from anthropic import Anthropic
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('ANTHROPIC_API_KEY not set (put it in .env)')
    return Anthropic(api_key=key)


def _json_from_text(text: str) -> dict:
    """Extract the first JSON object from an LLM reply. Tolerates a ```json fence
    and any trailing prose after the object (raw_decode stops at the object's end,
    so a model that appends an explanation no longer causes an 'Extra data' error)."""
    fence = re.search(r'```(?:json)?\s*(.+?)```', text, re.S)
    body = fence.group(1) if fence else text
    start = body.find('{')
    if start < 0:
        raise ValueError('no JSON object in LLM response')
    obj, _ = json.JSONDecoder().raw_decode(body[start:])
    return obj


def complete_json(system: str, user_text: str, pdf_bytes: bytes | None = None,
                  model: str | None = None, max_tokens: int = 4096) -> dict:
    """Send a prompt (optionally with a PDF document) and parse the JSON reply.
    Claude reads the PDF natively (layout preserved), so jumbled text extraction
    is not a concern."""
    content: list = []
    if pdf_bytes is not None:
        content.append({
            'type': 'document',
            'source': {'type': 'base64', 'media_type': 'application/pdf',
                       'data': base64.b64encode(pdf_bytes).decode('ascii')},
        })
    content.append({'type': 'text', 'text': user_text})

    resp = _client().messages.create(
        model=model or DEFAULT_MODEL, max_tokens=max_tokens, system=system,
        messages=[{'role': 'user', 'content': content}],
    )
    text = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text')
    return _json_from_text(text)
