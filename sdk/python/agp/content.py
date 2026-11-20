"""
AGP SDK — kept content: prompts and answers apart from the ledger (which keeps their hashes), with the org's
retention. Every read is on the ledger first.
"""
from __future__ import annotations

from typing import Any

from .http import Transport


class ContentClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def store(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._t.post("/agp/content", {"items": items})

    def get(self, content_id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/content/{content_id}")

    def retention(self) -> dict[str, Any]:
        return self._t.get("/agp/content-retention")

    def set_retention(self, days: int) -> dict[str, Any]:
        return self._t.put("/agp/content-retention", {"days": days})
