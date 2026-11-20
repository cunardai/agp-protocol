"""
AGP SDK — approvals bound to people (AGP 1.0, spec/studio-extensions.md §2.2): ask for an action (its name and
its parameters' hash) for a person; other people decide; a granted request issues an approval used once
(redeem), for exactly that action, those parameters and that person.
"""
from __future__ import annotations

from typing import Any

from .http import Transport


class ApprovalsClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def request(self, *, action: str, params_hash: str, requested_by: str, requested_for: str | None = None,
                task_id: str | None = None, mode: str | None = None, summary: str | None = None,
                expires_in_s: int | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {"action": action, "params_hash": params_hash, "requested_by": requested_by}
        for k, v in {"requested_for": requested_for, "task_id": task_id, "mode": mode, "summary": summary,
                     "expires_in_s": expires_in_s, "payload": payload}.items():
            if v is not None:
                body[k] = v
        return self._t.post("/agp/approval-requests", body)

    def list(self, *, status: str | None = None, action: str | None = None, limit: int | None = None) -> dict[str, Any]:
        return self._t.get("/agp/approval-requests", params={k: v for k, v in {"status": status, "action": action, "limit": limit}.items() if v is not None})

    def get(self, request_id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/approval-requests/{request_id}")

    def decide(self, request_id: str, *, approver: str, decision: str, reason: str | None = None) -> dict[str, Any]:
        """Granted: the request carries the issued approval as "artifact"."""
        return self._t.post(f"/agp/approval-requests/{request_id}/decisions",
                            {"approver": approver, "decision": decision, **({"reason": reason} if reason else {})})

    def redeem(self, *, action: str, params_hash: str, requested_for: str) -> dict[str, Any]:
        """Use a granted approval — once. AGPNotFoundError when there's none."""
        return self._t.post("/agp/approvals/redeem", {"action": action, "params_hash": params_hash, "requested_for": requested_for})

    def two_person_actions(self) -> dict[str, Any]:
        return self._t.get("/agp/two-person-actions")

    def propose_two_person_actions(self, actions: list[str], requested_by: str) -> dict[str, Any]:
        """Itself a two-person action: answers with the approval request; applied once granted."""
        return self._t.put("/agp/two-person-actions", {"actions": actions, "requested_by": requested_by})
