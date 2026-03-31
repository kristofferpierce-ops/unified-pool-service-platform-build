from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.freshbooks.contracts import FreshBooksConnectionStatus

DEFAULT_FRESHBOOKS_API_BASE_URL = 'https://api.freshbooks.com'
DEFAULT_FRESHBOOKS_API_VERSION = 'alpha'


class FreshBooksAPIError(RuntimeError):
    pass


class FreshBooksClient:
    def __init__(self, access_token: str, account_id: str = '', api_base_url: str = DEFAULT_FRESHBOOKS_API_BASE_URL, api_version: str = DEFAULT_FRESHBOOKS_API_VERSION) -> None:
        self.access_token = access_token.strip()
        self.account_id = account_id.strip()
        self.api_base_url = api_base_url.strip() or DEFAULT_FRESHBOOKS_API_BASE_URL
        self.api_version = api_version.strip() or DEFAULT_FRESHBOOKS_API_VERSION
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]
        if not self.access_token:
            raise ValueError('FreshBooks OAuth access token is required')

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        include_api_version: bool = False,
    ) -> dict[str, Any]:
        url = f"{self.api_base_url}{path if path.startswith('/') else '/' + path}"
        if query:
            filtered = {key: value for key, value in query.items() if value is not None and value != ''}
            if filtered:
                url = f"{url}?{urlencode(filtered, doseq=True)}"
        body = None
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
        }
        if include_api_version:
            headers['Api-Version'] = self.api_version
        if payload is not None:
            body = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        request = Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode('utf-8') or '{}'
                return json.loads(raw)
        except HTTPError as exc:
            payload = exc.read().decode('utf-8', errors='replace')
            raise FreshBooksAPIError(f'FreshBooks HTTP {exc.code}: {payload}') from exc
        except URLError as exc:
            raise FreshBooksAPIError(f'FreshBooks connection failed: {exc.reason}') from exc

    @staticmethod
    def _unwrap(payload: dict[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return {}
            current = current.get(key, {})
        return current

    def get_identity_info(self) -> dict[str, Any]:
        return self._request('GET', '/auth/api/v1/users/me', include_api_version=True)

    def resolve_first_account_id(self) -> str:
        payload = self.get_identity_info()
        response = payload.get('response', payload)
        memberships = response.get('business_memberships', []) if isinstance(response, dict) else []
        for membership in memberships:
            business = membership.get('business', {}) if isinstance(membership, dict) else {}
            account_id = str(business.get('account_id', '')).strip()
            if account_id:
                return account_id
        return ''

    def _account_path(self, suffix: str, account_id: str | None = None) -> str:
        resolved_account_id = (account_id or self.account_id).strip()
        if not resolved_account_id:
            raise FreshBooksAPIError('FreshBooks account id is required for accounting and events endpoints.')
        return f"/accounting/account/{resolved_account_id}{suffix}"

    def _events_path(self, suffix: str, account_id: str | None = None) -> str:
        resolved_account_id = (account_id or self.account_id).strip()
        if not resolved_account_id:
            raise FreshBooksAPIError('FreshBooks account id is required for events endpoints.')
        return f"/events/account/{resolved_account_id}{suffix}"

    def list_clients(self, *, email: str | None = None, organization: str | None = None, page: int = 1, per_page: int = 15, account_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {'page': page, 'per_page': per_page}
        if email:
            query['search[email]'] = email
        if organization:
            query['search[organization]'] = organization
        payload = self._request('GET', self._account_path('/users/clients', account_id), query=query)
        result = self._unwrap(payload, 'response', 'result')
        return list(result.get('clients', [])) if isinstance(result, dict) else []

    def get_client(self, client_id: str, *, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('GET', self._account_path(f'/users/clients/{client_id}', account_id))
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('client', {})) if isinstance(result, dict) else {}

    def create_client(self, client_payload: dict[str, Any], *, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('POST', self._account_path('/users/clients', account_id), payload={'client': client_payload})
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('client', {})) if isinstance(result, dict) else {}

    def create_estimate(self, estimate_payload: dict[str, Any], *, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('POST', self._account_path('/estimates/estimates', account_id), payload={'estimate': estimate_payload})
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('estimate', {})) if isinstance(result, dict) else {}

    def update_estimate(self, estimate_id: str, estimate_payload: dict[str, Any], *, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('PUT', self._account_path(f'/estimates/estimates/{estimate_id}', account_id), payload={'estimate': estimate_payload})
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('estimate', {})) if isinstance(result, dict) else {}

    def get_estimate(self, estimate_id: str, *, includes: list[str] | None = None, account_id: str | None = None) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if includes:
            query['include[]'] = includes
        payload = self._request('GET', self._account_path(f'/estimates/estimates/{estimate_id}', account_id), query=query)
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('estimate', {})) if isinstance(result, dict) else {}

    def list_webhook_callbacks(self, *, account_id: str | None = None) -> list[dict[str, Any]]:
        payload = self._request('GET', self._events_path('/events/callbacks', account_id))
        result = self._unwrap(payload, 'response', 'result')
        return list(result.get('callbacks', [])) if isinstance(result, dict) else []

    def create_webhook_callback(self, *, event: str, uri: str, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('POST', self._events_path('/events/callbacks', account_id), payload={'callback': {'event': event, 'uri': uri}})
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('callback', {})) if isinstance(result, dict) else {}

    def verify_webhook_callback(self, callback_id: str, verifier: str, *, account_id: str | None = None) -> dict[str, Any]:
        payload = self._request('PUT', self._events_path(f'/events/callbacks/{callback_id}', account_id), payload={'callback': {'verifier': verifier}})
        result = self._unwrap(payload, 'response', 'result')
        return dict(result.get('callback', {})) if isinstance(result, dict) else {}


def get_freshbooks_client(access_token: str | None = None, account_id: str | None = None, api_base_url: str | None = None) -> FreshBooksClient | None:
    resolved_access_token = (access_token or os.getenv('FRESHBOOKS_ACCESS_TOKEN', '')).strip()
    if not resolved_access_token:
        return None
    resolved_account_id = (account_id or os.getenv('FRESHBOOKS_ACCOUNT_ID', '')).strip()
    resolved_base_url = (api_base_url or os.getenv('FRESHBOOKS_API_BASE_URL', DEFAULT_FRESHBOOKS_API_BASE_URL)).strip() or DEFAULT_FRESHBOOKS_API_BASE_URL
    resolved_api_version = (os.getenv('FRESHBOOKS_API_VERSION', DEFAULT_FRESHBOOKS_API_VERSION)).strip() or DEFAULT_FRESHBOOKS_API_VERSION
    return FreshBooksClient(access_token=resolved_access_token, account_id=resolved_account_id, api_base_url=resolved_base_url, api_version=resolved_api_version)


def get_freshbooks_connection_status(sync_mode: str = 'dry_run') -> dict[str, Any]:
    client = get_freshbooks_client()
    has_token = client is not None
    account_id = (os.getenv('FRESHBOOKS_ACCOUNT_ID', '') or '').strip()
    status = FreshBooksConnectionStatus(
        api_base_url=(os.getenv('FRESHBOOKS_API_BASE_URL', DEFAULT_FRESHBOOKS_API_BASE_URL) or DEFAULT_FRESHBOOKS_API_BASE_URL).strip(),
        auth_mode='oauth2',
        has_access_token=has_token,
        has_account_id=bool(account_id),
        configured=has_token and bool(account_id),
        live_write_enabled=sync_mode == 'live' and has_token and bool(account_id),
        sync_mode=sync_mode,
    )
    return asdict(status)
