from app.core.database import create_db_and_tables, get_session
from app.services.bootstrap import seed_defaults


if __name__ == '__main__':
    create_db_and_tables()
    with get_session() as session:
        seed_defaults(session)
    print('Database initialized and defaults seeded.')
