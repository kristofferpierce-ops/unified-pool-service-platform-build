"""Skimmer Public API client.

Auth is an API key sent in the `skimmer-api-key` header. Supports a fixture mode
so the whole connector is testable before live credentials exist -- when no
SKIMMER_API_KEY is configured, the client serves the bundled sample payloads
(app/connectors/skimmer/fixtures.py) instead of hitting the network. Drop in the
key and it goes live with no other change.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.skimmer.fixtures import SAMPLE

DEFAULT_SKIMMER_BASE_URL = 'https://api.skimmer.com/v1'

# Entity -> API path (relative to base url). Kept in one place so live wiring is
# a single edit if Skimmer's paths differ from the documented ones.
ENTITY_PATHS = {
    'customers': 'customers',
    'service_locations': 'service-locations',
    'bodies_of_water': 'bodies-of-water',
    'work_orders': 'work-orders',
    'routes': 'routes',
}


class SkimmerAPIError(RuntimeError):
    pass


class SkimmerClient:
    def __init__(
        self,
        *,
        api_key: str = '',
        base_url: str = DEFAULT_SKIMMER_BASE_URL,
        use_fixtures: bool = False,
        fixtures: dict[str, list[dict]] | None = None,
    ) -> None:
        self.api_key = (api_key or '').strip()
        self.base_url = (base_url or DEFAULT_SKIMMER_BASE_URL).strip().rstrip('/')
        self.use_fixtures = use_fixtures or not self.api_key
        self.fixtures = fixtures if fixtures is not None else SAMPLE

    @property
    def mode(self) -> str:
        return 'fixtures' if self.use_fixtures else 'live'

    def _headers(self) -> dict[str, str]:
        return {'Accept': 'application/json', 'skimmer-api-key': self.api_key}

    @staticmethod
    def _extract_items(payload: Any) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            for key in ('data', 'items', 'results', 'records'):
                value = payload.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
        return []

    def _get(self, entity: str) -> list[dict]:
        if self.use_fixtures:
            return list(self.fixtures.get(entity, []))
        path = ENTITY_PATHS.get(entity, entity)
        url = f'{self.base_url}/{path}'
        request = Request(url, headers=self._headers(), method='GET')
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode('utf-8') or '[]'
        except HTTPError as exc:
            message = exc.read().decode('utf-8', errors='replace')
            raise SkimmerAPIError(f'Skimmer HTTP {exc.code}: {message}') from exc
        except URLError as exc:
            raise SkimmerAPIError(f'Skimmer connection failed: {exc.reason}') from exc
        return self._extract_items(json.loads(raw))

    def customers(self) -> list[dict]:
        return self._get('customers')

    def service_locations(self) -> list[dict]:
        return self._get('service_locations')

    def bodies_of_water(self) -> list[dict]:
        return self._get('bodies_of_water')

    def work_orders(self) -> list[dict]:
        return self._get('work_orders')

    def routes(self) -> list[dict]:
        return self._get('routes')


def get_skimmer_client(api_key: str | None = None, use_fixtures: bool | None = None) -> SkimmerClient:
    """Build a client. Falls back to fixture mode when no API key is configured,
    so the connector works in development without live Skimmer access."""
    key = (api_key if api_key is not None else os.getenv('SKIMMER_API_KEY', '')).strip()
    fixtures_flag = (use_fixtures if use_fixtures is not None else not key)
    return SkimmerClient(api_key=key, use_fixtures=fixtures_flag)


def skimmer_connection_status() -> dict[str, Any]:
    key = (os.getenv('SKIMMER_API_KEY', '') or '').strip()
    return {
        'has_api_key': bool(key),
        'mode': 'live' if key else 'fixtures',
        'base_url': (os.getenv('SKIMMER_BASE_URL', DEFAULT_SKIMMER_BASE_URL) or '').strip(),
        'configured': bool(key),
    }
