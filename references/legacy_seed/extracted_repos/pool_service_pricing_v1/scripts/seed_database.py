import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import create_db_and_tables, get_session
from app.services.bootstrap import seed_defaults


def main() -> None:
    create_db_and_tables()
    with get_session() as session:
        seed_defaults(session)
    print("Database created and default data seeded.")


if __name__ == "__main__":
    main()
