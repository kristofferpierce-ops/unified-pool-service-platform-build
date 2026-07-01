from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.freshbooks.contracts import FreshBooksConnectionStatus

DEFAULT_FRESHBOOKS_API_BASE_URL = 'https://api.freshbooks.com'
DEFAULT_FRESHBOOKS_API_VERSION = 'alpha'
FRESHBOOKS_TOKEN_URL = 'https://api.freshbooks.com/auth/oauth/token'
_TOKENS_PATH = Path(__file__).resolve().parents[3] / 'data' / 'freshbooks_oauth_tokens.json'


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

    def list_invoices(self, *, page: int = 1, per_page: int = 100, include: list[str] | None = None,
                      account_id: str | None = None) -> tuple[list[dict[str, Any]], int]:
        """Return (invoices, total_pages) for one page of the account's invoices."""
        query: dict[str, Any] = {'page': page, 'per_page': per_page}
        if include:
            query['include[]'] = include
        payload = self._request('GET', self._account_path('/invoices/invoices', account_id), query=query)
        result = self._unwrap(payload, 'response', 'result')
        if not isinstance(result, dict):
            return [], 1
        invoices = list(result.get('invoices', []))
        pages = int(result.get('pages', 1) or 1)
        return invoices, pages

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


def _load_token_store() -> dict[str, Any]:
    try:
        return json.loads(_TOKENS_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_token_store(data: dict[str, Any]) -> None:
    try:
        _TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TOKENS_PATH.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except OSError:
        pass


def refresh_access_token(*, refresh_token: str | None = None, client_id: str | None = None,
                         client_secret: str | None = None) -> str:
    """Mint a fresh access token from the rotating refresh token, persisting the
    new tokens to the store (FreshBooks refresh tokens are single-use). Returns
    the new access token, or '' if refresh credentials are missing / it fails."""
    store = _load_token_store()
    refresh_token = (refresh_token or store.get('refresh_token') or os.getenv('FRESHBOOKS_REFRESH_TOKEN', '')).strip()
    client_id = (client_id or os.getenv('FRESHBOOKS_CLIENT_ID', '')).strip()
    client_secret = (client_secret or os.getenv('FRESHBOOKS_CLIENT_SECRET', '')).strip()
    if not (refresh_token and client_id and client_secret):
        return ''
    body = json.dumps({
        'grant_type': 'refresh_token', 'client_id': client_id,
        'client_secret': client_secret, 'refresh_token': refresh_token,
    }).encode('utf-8')
    request = Request(FRESHBOOKS_TOKEN_URL, data=body,
                      headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode('utf-8') or '{}')
    except (HTTPError, URLError):
        return ''
    access_token = str(payload.get('access_token', '')).strip()
    if access_token:
        store.update({
            'access_token': access_token,
            'refresh_token': str(payload.get('refresh_token', '')).strip() or refresh_token,
            'token_type': payload.get('token_type', ''),
            'expires_in': payload.get('expires_in', ''),
            'scope': payload.get('scope', ''),
        })
        _save_token_store(store)
    return access_token


def get_refreshed_freshbooks_client(account_id: str | None = None, api_base_url: str | None = None) -> FreshBooksClient | None:
    """A client using a freshly-refreshed access token (env/store refresh creds).
    Returns None if refresh isn't possible; callers can fall back to the env token."""
    access_token = refresh_access_token()
    if not access_token:
        return None
    resolved_account_id = (account_id or os.getenv('FRESHBOOKS_ACCOUNT_ID', '')).strip()
    resolved_base_url = (api_base_url or os.getenv('FRESHBOOKS_API_BASE_URL', DEFAULT_FRESHBOOKS_API_BASE_URL)).strip() or DEFAULT_FRESHBOOKS_API_BASE_URL
    return FreshBooksClient(access_token=access_token, account_id=resolved_account_id, api_base_url=resolved_base_url)


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
