"""Scheduled invoice sync -- the hands-off pipeline.

Polls the mailboxes (READ-ONLY) for recent invoice PDFs, LLM-extracts them, and
ingests reconciled invoices into the price ledger. Idempotent: the poller skips
attachments already downloaded and the importer dedups by (vendor, invoice #), so
each run only does real work on invoices that arrived since last time.

Run by the Windows scheduled task (Sync Invoices.bat). Logs to data/logs/.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from app.core.database import create_db_and_tables, engine
from app.services.gmail_poller import _env, pull_mailbox_pdfs
from app.services.invoice_llm import ingest_invoice_pdfs

LOG = ROOT / 'data' / 'logs' / 'invoice_sync.log'
# Recent PDFs, minus the big known non-invoice sources (health dept, own outgoing,
# software receipts). New vendors are still caught; the LLM classifies the rest.
QUERY = ('has:attachment filename:pdf newer_than:14d '
         '-from:flhealth.gov -from:freshbooks.com -from:stripe.com -from:keyspoolservice.com')


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def main() -> None:
    log('=== invoice sync start ===')
    mailboxes = [m.strip() for m in _env('GMAIL_MAILBOXES').split(',') if m.strip()]
    new_files: list = []
    for mb in mailboxes:
        try:
            saved = pull_mailbox_pdfs(mb, query=QUERY, max_messages=300)
            log(f'{mb}: {len(saved)} new PDF(s)')
            new_files += saved
        except Exception as exc:  # noqa: BLE001
            log(f'{mb}: POLL ERROR {type(exc).__name__}: {exc}')

    if not new_files:
        log('no new invoices; done.')
        return

    create_db_and_tables()
    with Session(engine) as session:
        stats = ingest_invoice_pdfs(session, new_files, log=log)
    log(f'ingest stats: {stats}')
    log('=== invoice sync done ===')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        log(f'FATAL {type(exc).__name__}: {exc}')
        sys.exit(1)
