from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.heritage.contracts import HeritageCatalogItem, HeritageConnectionStatus

DEFAULT_HERITAGE_CATALOG_URL = ''
DEFAULT_HERITAGE_LOCAL_CATALOG_PATH = ''


class HeritageAPIError(RuntimeError):
    pass


class HeritageClient:
    def __init__(
        self,
        *,
        account_id: str,
        api_key: str,
        branch_id: str = '',
        catalog_url: str = DEFAULT_HERITAGE_CATALOG_URL,
        local_catalog_path: str = DEFAULT_HERITAGE_LOCAL_CATALOG_PATH,
        auth_mode: str = 'header',
    ) -> None:
        self.account_id = account_id.strip()
        self.api_key = api_key.strip()
        self.branch_id = branch_id.strip()
        self.catalog_url = catalog_url.strip()
        self.local_catalog_path = local_catalog_path.strip()
        self.auth_mode = auth_mode.strip() or 'header'
        if not self.account_id:
            raise ValueError('Heritage account id is required')
        if not self.api_key:
            raise ValueError('Heritage API key is required')
        if not self.catalog_url and not self.local_catalog_path:
            raise ValueError('Heritage catalog source is required')

    def _headers(self) -> dict[str, str]:
        headers = {'Accept': 'application/json'}
        if self.auth_mode == 'header':
            headers['X-API-Key'] = self.api_key
            headers['X-Account-Id'] = self.account_id
            if self.branch_id:
                headers['X-Branch-Id'] = self.branch_id
        return headers

    def _load_local_catalog(self) -> list[dict[str, Any]]:
        path = Path(self.local_catalog_path)
        if not path.exists():
            raise HeritageAPIError(f'Heritage local catalog file not found: {self.local_catalog_path}')
        payload = json.loads(path.read_text(encoding='utf-8') or '[]')
        return self._extract_items(payload)

    def _request_remote_catalog(self) -> list[dict[str, Any]]:
        if not self.catalog_url:
            return []
        request = Request(self.catalog_url, headers=self._headers(), method='GET')
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode('utf-8') or '[]'
                payload = json.loads(raw)
        except HTTPError as exc:
            message = exc.read().decode('utf-8', errors='replace')
            raise HeritageAPIError(f'Heritage HTTP {exc.code}: {message}') from exc
        except URLError as exc:
            raise HeritageAPIError(f'Heritage connection failed: {exc.reason}') from exc
        return self._extract_items(payload)

    @staticmethod
    def _extract_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ('items', 'results', 'products', 'catalog', 'data'):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = HeritageClient._extract_items(value)
                if nested:
                    return nested
        return []

    @staticmethod
    def _normalize_item(raw_item: dict[str, Any]) -> HeritageCatalogItem | None:
        sku = str(raw_item.get('sku') or raw_item.get('item_code') or raw_item.get('itemCode') or raw_item.get('id') or '').strip()
        model_name = str(raw_item.get('model_name') or raw_item.get('name') or raw_item.get('description') or raw_item.get('title') or '').strip()
        brand_name = str(raw_item.get('brand_name') or raw_item.get('brand') or raw_item.get('manufacturer') or '').strip()
        heater_kind = str(raw_item.get('heater_kind') or raw_item.get('category') or raw_item.get('type_name') or '').strip().lower()
        fuel_type = str(raw_item.get('fuel_type') or raw_item.get('fuel') or '').strip().lower()
        capacity = raw_item.get('capacity_btu_per_hr') or raw_item.get('btu') or raw_item.get('btu_output') or raw_item.get('capacity') or 0
        price = raw_item.get('price')
        if price in ('', None):
            price = raw_item.get('unit_price') or raw_item.get('net_price')
        availability = str(raw_item.get('availability_status') or raw_item.get('availability') or raw_item.get('status') or '').strip()
        branch_name = str(raw_item.get('branch_name') or raw_item.get('branch') or '').strip()
        currency_code = str(raw_item.get('currency_code') or raw_item.get('currency') or 'USD').strip() or 'USD'
        try:
            capacity_value = float(capacity or 0)
        except (TypeError, ValueError):
            capacity_value = 0.0
        try:
            price_value = float(price) if price not in ('', None) else None
        except (TypeError, ValueError):
            price_value = None
        if not model_name and not sku:
            return None
        return HeritageCatalogItem(
            sku=sku,
            model_name=model_name or sku,
            brand_name=brand_name,
            heater_kind=heater_kind,
            fuel_type=fuel_type,
            capacity_btu_per_hr=capacity_value,
            price=price_value,
            currency_code=currency_code,
            availability_status=availability,
            branch_name=branch_name,
            payload=raw_item,
        )

    def fetch_catalog(self) -> list[dict[str, Any]]:
        if self.local_catalog_path:
            raw_items = self._load_local_catalog()
        else:
            raw_items = self._request_remote_catalog()
        normalized: list[dict[str, Any]] = []
        for raw_item in raw_items:
            item = self._normalize_item(raw_item)
            if item is not None:
                normalized.append(item.to_dict())
        return normalized


def get_heritage_client(
    *,
    account_id: str | None = None,
    api_key: str | None = None,
    branch_id: str | None = None,
    catalog_url: str | None = None,
    local_catalog_path: str | None = None,
    auth_mode: str | None = None,
) -> HeritageClient | None:
    resolved_account_id = (account_id or os.getenv('HERITAGE_ACCOUNT_ID', '')).strip()
    resolved_api_key = (api_key or os.getenv('HERITAGE_API_KEY', '')).strip()
    if not resolved_account_id or not resolved_api_key:
        return None
    resolved_branch = (branch_id or os.getenv('HERITAGE_DEFAULT_BRANCH', '')).strip()
    resolved_catalog_url = (catalog_url or os.getenv('HERITAGE_CATALOG_URL', DEFAULT_HERITAGE_CATALOG_URL)).strip()
    resolved_local_catalog_path = (local_catalog_path or os.getenv('HERITAGE_LOCAL_CATALOG_PATH', DEFAULT_HERITAGE_LOCAL_CATALOG_PATH)).strip()
    resolved_auth_mode = (auth_mode or os.getenv('HERITAGE_AUTH_MODE', 'header')).strip() or 'header'
    return HeritageClient(
        account_id=resolved_account_id,
        api_key=resolved_api_key,
        branch_id=resolved_branch,
        catalog_url=resolved_catalog_url,
        local_catalog_path=resolved_local_catalog_path,
        auth_mode=resolved_auth_mode,
    )


def get_heritage_connection_status(sync_mode: str = 'dry_run') -> dict[str, Any]:
    account_id = (os.getenv('HERITAGE_ACCOUNT_ID', '') or '').strip()
    api_key = (os.getenv('HERITAGE_API_KEY', '') or '').strip()
    branch_id = (os.getenv('HERITAGE_DEFAULT_BRANCH', '') or '').strip()
    catalog_url = (os.getenv('HERITAGE_CATALOG_URL', DEFAULT_HERITAGE_CATALOG_URL) or '').strip()
    local_catalog_path = (os.getenv('HERITAGE_LOCAL_CATALOG_PATH', DEFAULT_HERITAGE_LOCAL_CATALOG_PATH) or '').strip()
    auth_mode = (os.getenv('HERITAGE_AUTH_MODE', 'header') or 'header').strip()
    status = HeritageConnectionStatus(
        catalog_url=catalog_url,
        local_catalog_path=local_catalog_path,
        auth_mode=auth_mode,
        has_account_id=bool(account_id),
        has_api_key=bool(api_key),
        has_branch_id=bool(branch_id),
        has_catalog_source=bool(catalog_url or local_catalog_path),
        configured=bool(account_id and api_key and (catalog_url or local_catalog_path)),
        live_catalog_enabled=sync_mode == 'live' and bool(account_id and api_key and (catalog_url or local_catalog_path)),
        sync_mode=sync_mode,
    )
    payload = asdict(status)
    if branch_id:
        payload['default_branch'] = branch_id
    return payload
