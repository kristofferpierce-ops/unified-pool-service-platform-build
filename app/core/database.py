from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import event
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


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Session:
    with Session(engine) as session:
        yield session
