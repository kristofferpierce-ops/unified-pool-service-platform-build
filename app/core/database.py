from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import event, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import DATABASE_URL
import app.models  # noqa: F401 ensures models are registered

_is_sqlite = DATABASE_URL.startswith('sqlite')
connect_args = {'check_same_thread': False} if _is_sqlite else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


if _is_sqlite:
    @event.listens_for(engine, 'connect')
    def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """Harden SQLite for concurrent writers (UI + connectors + jobs).

        WAL lets readers proceed during a write; busy_timeout waits on a lock
        instead of immediately raising 'database is locked'; foreign_keys enforces
        referential integrity as it gets added; synchronous=NORMAL is safe + fast
        under WAL.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=5000')
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.close()


def _add_missing_columns() -> None:
    """Lightweight additive migration: ALTER-add any NULLABLE model column missing
    from an existing table. SQLModel's create_all makes missing TABLES but never
    adds COLUMNS to a table that already exists, so adding a field to a shipped
    model would otherwise break every query on that table with 'no such column'.
    Only nullable columns are added (always safe as SQLite ADD COLUMN); anything
    else is left for an explicit migration."""
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    with engine.begin() as conn:
        for table_name, table in SQLModel.metadata.tables.items():
            if table_name not in existing:
                continue
            have = {c['name'] for c in insp.get_columns(table_name)}
            for col in table.columns:
                if not col.nullable:
                    continue
                if col.name not in have:
                    coltype = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {coltype}'))
                # Honor Field(index=True) on additive columns -- ALTER ADD COLUMN never
                # creates the index, so create it here (idempotent, backfills on re-run).
                if col.index:
                    conn.execute(text(
                        f'CREATE INDEX IF NOT EXISTS "ix_{table_name}_{col.name}" '
                        f'ON "{table_name}" ("{col.name}")'
                    ))


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    if _is_sqlite:
        _add_missing_columns()


@contextmanager
def get_session() -> Session:
    with Session(engine) as session:
        yield session
