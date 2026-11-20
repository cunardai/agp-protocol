"""
AGP SDK — the hub operator (AGP 1.0, §4.4): a credential not tied to an org (scope agp.operator only) that lists
read-only orgs and decides the hub's half of reinstating one, naming the hub's person.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .http import Transport


class OperatorClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def read_only_orgs(self, prefix: str | None = None) -> dict[str, Any]:
        return self._t.get("/agp/operator/orgs", params={"prefix": prefix} if prefix else None)

    def decide(self, org_id: str, request_id: str, *, approver: str, decision: str, reason: str | None = None) -> dict[str, Any]:
        return self._t.post(f"/agp/operator/orgs/{quote(org_id, safe='')}/approval-requests/{request_id}/decisions",
                            {"approver": approver, "decision": decision, **({"reason": reason} if reason else {})})
