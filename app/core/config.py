from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv('UPS_DATA_DIR', BASE_DIR / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / 'unified_pool_service_platform.db'
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DEFAULT_DB_PATH}')

EXPORT_DIR = Path(os.getenv('UPS_EXPORT_DIR', DATA_DIR / 'exports'))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = Path(os.getenv('UPS_UPLOAD_DIR', DATA_DIR / 'uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = BASE_DIR / 'app' / 'static'
STATIC_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = os.getenv('APP_NAME', 'Unified Pool Service Operations Core')
APP_ENV = os.getenv('APP_ENV', 'development')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
