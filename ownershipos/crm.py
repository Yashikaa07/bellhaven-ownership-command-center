from __future__ import annotations

import json
import re
import ssl
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


class CRMClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        raw = token.strip()
        # Accept a raw token, a Bearer value, an Authorization header, or the
        # complete curl example supplied by the assessment workspace.
        match = re.search(r"Authorization:\s*(Bearer\s+[^\s\"']+)", raw, re.I)
        if match:
            raw = match.group(1)
        elif raw.lower().startswith("authorization:"):
            raw = raw.split(":", 1)[1].strip().strip("\"'")
        raw = raw.strip().strip("\"'")
        if not raw.lower().startswith("bearer "):
            raw = "Bearer " + raw
        self.token = raw

    def _request(self, method: str, path: str, payload: dict | None = None):
        headers = {"Authorization": self.token, "Accept": "application/json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode()
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(req, timeout=30, context=context) as response:
                return json.loads(response.read().decode())
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"CRM {method} {path} failed ({exc.code}): {detail}") from exc

    def list_accounts(self) -> list[dict]:
        records: list[dict] = []
        for page in range(1, 100):
            result = self._request("GET", "/accounts?" + urlencode({"page": page, "page_size": 100}))
            batch = result if isinstance(result, list) else next(
                (result[k] for k in ("accounts", "items", "results", "data") if isinstance(result.get(k), list)), []
            )
            for account in batch:
                normalized = dict(account)
                if not normalized.get("id"):
                    normalized["id"] = normalized.get("account_id") or normalized.get("accountId")
                records.append(normalized)
            if len(batch) < 100:
                break
        return records

    def create_account(self, payload: dict) -> dict:
        result = self._request("POST", "/accounts", payload)
        if isinstance(result, dict) and not result.get("id"):
            result["id"] = result.get("account_id") or result.get("accountId")
        return result

    def update_account(self, account_id: str, payload: dict) -> dict:
        return self._request("PATCH", f"/accounts/{account_id}", payload)
