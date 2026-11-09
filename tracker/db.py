"""Tiny client for the Supabase REST interface (no extra library needed)."""
from __future__ import annotations

import requests


class Supabase:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        # Older keys are JWTs and must also be sent as a bearer token.
        # Newer "sb_secret_..." keys go in the apikey header only.
        if not key.startswith("sb_"):
            self.headers["Authorization"] = f"Bearer {key}"
        self.http = requests.Session()

    def _req(self, method: str, table: str, params=None, json=None, prefer: str | None = None,
             extra_headers: dict | None = None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        if extra_headers:
            headers.update(extra_headers)
        r = self.http.request(method, f"{self.base}/{table}", params=params, json=json,
                              headers=headers, timeout=60)
        if not r.ok:
            raise RuntimeError(f"Supabase {method} {table} failed ({r.status_code}): {r.text[:300]}")
        return r

    def select(self, table: str, params: dict) -> list[dict]:
        rows, offset, page = [], 0, 1000
        while True:
            r = self._req("GET", table, params=params,
                          extra_headers={"Range-Unit": "items", "Range": f"{offset}-{offset + page - 1}"})
            batch = r.json()
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page

    def insert(self, table: str, rows: list[dict]) -> None:
        for i in range(0, len(rows), 200):
            self._req("POST", table, json=rows[i:i + 200], prefer="return=minimal")

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        for i in range(0, len(rows), 200):
            self._req("POST", table, params={"on_conflict": on_conflict}, json=rows[i:i + 200],
                      prefer="resolution=merge-duplicates,return=minimal")

    def update(self, table: str, filters: dict, values: dict) -> None:
        self._req("PATCH", table, params=filters, json=values, prefer="return=minimal")

    def delete(self, table: str, filters: dict) -> int:
        r = self._req("DELETE", table, params=filters, prefer="return=representation")
        return len(r.json())
