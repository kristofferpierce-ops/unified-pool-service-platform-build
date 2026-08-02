"""One-time Gmail authorize for the read-only invoice poller.

Run ONCE (a browser opens for each mailbox):

    .venv\\Scripts\\python.exe authorize_gmail.py

Sign in AS each mailbox (accounting@, then service@) and approve READ-ONLY Gmail.
A refresh token per mailbox is saved in .secrets/ (gitignored). After that the
poller runs on its own -- no more logins. Scope is gmail.readonly only, so this
can never send, move, or delete mail.
"""
from __future__ import annotations

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def _env(name: str, default: str = '') -> str:
    envf = ROOT / '.env'
    if envf.exists():
        for line in envf.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith(name + '='):
                return line.split('=', 1)[1].strip()
    return os.environ.get(name, default)


def token_path_for(mailbox: str) -> Path:
    return ROOT / '.secrets' / f"gmail_token_{mailbox.split('@')[0]}.json"


def main() -> None:
    client = ROOT / _env('GMAIL_OAUTH_CLIENT', '.secrets/gmail_oauth_client.json')
    mailboxes = [m.strip() for m in _env('GMAIL_MAILBOXES').split(',') if m.strip()]
    if not client.exists():
        raise SystemExit(f'OAuth client file not found: {client}')
    if not mailboxes:
        raise SystemExit('Set GMAIL_MAILBOXES in .env')

    (ROOT / '.secrets').mkdir(exist_ok=True)
    for mb in mailboxes:
        tp = token_path_for(mb)
        if tp.exists():
            print(f'[skip] {mb} already authorized -> {tp.name}')
            continue
        print(f'\n=== Authorize {mb} ===')
        print(f'A browser will open. SIGN IN AS {mb} and approve read-only Gmail.')
        flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
        creds = flow.run_local_server(port=0, prompt='consent', login_hint=mb)
        tp.write_text(creds.to_json(), encoding='utf-8')
        print(f'[ok] saved {tp.name}')
    print('\nAll mailboxes authorized. You can now run the poller.')


if __name__ == '__main__':
    main()
