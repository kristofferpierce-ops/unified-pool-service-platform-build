from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LACRMClient:
    api_url: str
    api_key: str

    def search_contacts(self, query: str) -> dict[str, Any]:
        if not self.api_key:
            return {'configured': False, 'query': query, 'results': []}
        response = requests.post(self.api_url, json={'APIToken': self.api_key, 'Function': 'SearchContacts', 'Parameters': {'SearchTerm': query}}, timeout=20)
        response.raise_for_status()
        return response.json()

    def create_task(self, *, contact_id: str, title: str, due_date: str | None = None, assigned_to: str | None = None) -> dict[str, Any]:
        if not self.api_key:
            return {'configured': False, 'contact_id': contact_id, 'title': title}
        parameters = {'ContactId': contact_id, 'Title': title}
        if due_date:
            parameters['DueDate'] = due_date
        if assigned_to:
            parameters['AssignedTo'] = assigned_to
        response = requests.post(self.api_url, json={'APIToken': self.api_key, 'Function': 'CreateTask', 'Parameters': parameters}, timeout=20)
        response.raise_for_status()
        return response.json()
