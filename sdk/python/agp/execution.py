"""
AGP SDK — Execution API client

Wraps: /agp/action-envelopes, /execution-receipts, /ledger-events,
       /tasks/{id}/replay, /operations/{id}
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .http import Transport, new_idempotency_key
from .models import (
    ActionEnvelope, AsyncOperation, EventLedgerRecord,
    ExecutionReceipt, GovernanceAttestation, PagedResult,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionClient:
    def __init__(self, transport: Transport):
        self._t = transport

    # ── Action Envelopes ───────────────────────────────────────────────────

    def submit_envelope(
        self,
        *,
        task_id: str,
        agent_id: str,
        tool_id: str,
        operation: dict[str, Any],
        capability_token_ref: str,
        decision_ref: str,
        policy_decision_ref: str,
        approval_ref: str | None = None,
        governance_attestations: list[GovernanceAttestation] | None = None,
        async_mode: bool = False,
        params_hash: str | None = None,
        idempotency_key: str | None = None,
    ) -> ActionEnvelope | AsyncOperation:
        """
        Submit an ActionEnvelope through the fail-closed gate.

        Returns ActionEnvelope on synchronous execution (default).
        Returns AsyncOperation when async_mode=True.

        Raises:
            AGPPolicyDeniedError  — verdict is deny/quarantine
            AGPApprovalRequiredError — approval missing for high-risk task
            AGPTokenRevokedError / AGPTokenExpiredError — bad capability token
        """
        body: dict[str, Any] = {
            "task_id": task_id,
            "agent_id": agent_id,
            "tool_id": tool_id,
            "operation": operation,
            "capability_token_ref": capability_token_ref,
            "decision_ref": decision_ref,
            "policy_decision_ref": policy_decision_ref,
            "created_at": _now(),
        }
        if approval_ref:
            body["approval_ref"] = approval_ref
        if params_hash:
            body["params_hash"] = params_hash
        if governance_attestations:
            body["governance_attestations"] = [
                a.model_dump() for a in governance_attestations
            ]

        prefer = "execute-async" if async_mode else None
        raw = self._t.post(
            "/agp/action-envelopes", body,
            prefer=prefer,
            idempotency_key=idempotency_key or new_idempotency_key(),
        )

        if async_mode or "operation_id" in raw:
            return AsyncOperation.model_validate(raw)
        return ActionEnvelope.model_validate(raw)

    def validate_envelope(
        self,
        *,
        task_id: str,
        agent_id: str,
        tool_id: str,
        operation: dict[str, Any],
        capability_token_ref: str,
        decision_ref: str,
        policy_decision_ref: str,
        approval_ref: str | None = None,
    ) -> bool:
        """
        Dry-run validation of an ActionEnvelope. Returns True if the gate
        would pass; raises an AGPError subclass if it would fail.
        Does not mutate any state.
        """
        body: dict[str, Any] = {
            "task_id": task_id,
            "agent_id": agent_id,
            "tool_id": tool_id,
            "operation": operation,
            "capability_token_ref": capability_token_ref,
            "decision_ref": decision_ref,
            "policy_decision_ref": policy_decision_ref,
            "created_at": _now(),
        }
        if approval_ref:
            body["approval_ref"] = approval_ref
        result = self._t.post("/agp/action-envelopes", body, prefer="validate-only")
        return result.get("valid", False)

    def get_envelope(self, action_id: str) -> ActionEnvelope:
        return ActionEnvelope.model_validate(
            self._t.get(f"/agp/action-envelopes/{action_id}")
        )

    # ── Execution Receipts ─────────────────────────────────────────────────

    def record_receipt(self, *, action_ref: str, task_id: str, executor_id: str, outcome: str,
                       executed_at: str | None = None, **extra: Any) -> dict[str, Any]:
        """The product's receipt for an action it carried out (execute-async): it finishes the task (AGP 1.0, §2.6)."""
        return self._t.post("/agp/execution-receipts", {"action_ref": action_ref, "task_id": task_id, "executor_id": executor_id,
                                                        "outcome": outcome, "executed_at": executed_at or _now(), **extra},
                            idempotency_key=new_idempotency_key())

    def get_receipt(self, receipt_id: str) -> ExecutionReceipt:
        return ExecutionReceipt.model_validate(
            self._t.get(f"/agp/execution-receipts/{receipt_id}")
        )

    # ── Ledger ─────────────────────────────────────────────────────────────

    def append_ledger_event(
        self,
        *,
        task_id: str,
        agent_id: str,
        principal_id: str,
        outcome: str,
        prev_event_hash: str | None = None,
        tool_action_ref: str | None = None,
        decision_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> EventLedgerRecord:
        body: dict[str, Any] = {
            "task_id": task_id,
            "timestamp": _now(),
            "agent_id": agent_id,
            "principal_id": principal_id,
            "outcome": outcome,
        }
        if prev_event_hash:
            body["prev_event_hash"] = prev_event_hash
        if tool_action_ref:
            body["tool_action_ref"] = tool_action_ref
        if decision_ref:
            body["decision_ref"] = decision_ref
        raw = self._t.post("/agp/ledger-events", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return EventLedgerRecord.model_validate(raw)

    def list_ledger_events(
        self,
        *,
        task_id: str | None = None,
        outcome: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> PagedResult:
        params: dict[str, Any] = {"limit": limit}
        if task_id:
            params["task_id"] = task_id
        if outcome:
            params["outcome"] = outcome
        if cursor:
            params["cursor"] = cursor
        return PagedResult.model_validate(
            self._t.get("/agp/ledger-events", params=params)
        )

    def replay_task(self, task_id: str) -> dict[str, Any]:
        """Return the complete ordered event ledger for a task."""
        return self._t.get(f"/agp/tasks/{task_id}/replay")

    # ── Async Operations ───────────────────────────────────────────────────

    def get_operation(self, operation_id: str) -> AsyncOperation:
        return AsyncOperation.model_validate(
            self._t.get(f"/agp/operations/{operation_id}")
        )
