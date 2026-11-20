"""
AGP SDK — Decision API client

Wraps: /agp/decision/contexts, /evidence-bundles, /decisions,
       /policy-evaluations, /approvals, /escalations
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .http import Transport, new_idempotency_key
from .models import (
    ApprovalArtifact, ApprovalDecision, AttestedContext, DecisionRecord,
    EscalationNotice, EvidenceBundle, PolicyDecision, Verdict,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionClient:
    def __init__(self, transport: Transport):
        self._t = transport

    # ── Attested Contexts ──────────────────────────────────────────────────

    def create_context(
        self,
        *,
        task_id: str,
        trust_class: str,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> AttestedContext:
        body = {"task_id": task_id, "trust_class": trust_class,
                "created_at": _now(), **extra}
        raw = self._t.post("/agp/decision/contexts", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return AttestedContext.model_validate(raw)

    def get_context(self, context_id: str) -> AttestedContext:
        return AttestedContext.model_validate(
            self._t.get(f"/agp/decision/contexts/{context_id}")
        )

    # ── Evidence Bundles ───────────────────────────────────────────────────

    def create_evidence_bundle(
        self,
        *,
        task_id: str,
        items: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> EvidenceBundle:
        body = {"task_id": task_id, "items": items, "created_at": _now()}
        raw = self._t.post("/agp/decision/evidence-bundles", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return EvidenceBundle.model_validate(raw)

    # ── Decisions ──────────────────────────────────────────────────────────

    def create_decision(
        self,
        *,
        task_id: str,
        agent_id: str,
        selected_action: str,
        rationale: str,
        uncertainty_score: float,
        idempotency_key: str | None = None,
        **extra: Any,
    ) -> DecisionRecord:
        body = {
            "task_id": task_id,
            "agent_id": agent_id,
            "selected_action": selected_action,
            "rationale": rationale,
            "uncertainty_score": uncertainty_score,
            "created_at": _now(),
            **extra,
        }
        raw = self._t.post("/agp/decision/decisions", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return DecisionRecord.model_validate(raw)

    def get_decision(self, decision_id: str) -> DecisionRecord:
        return DecisionRecord.model_validate(
            self._t.get(f"/agp/decision/decisions/{decision_id}")
        )

    # ── Policy Evaluations ─────────────────────────────────────────────────

    def evaluate_policy(
        self,
        *,
        task_id: str,
        decision_ref: str,
        verdict: Verdict | None = None,
        rationale: str | None = None,
        policy_set_ref: str | None = None,
        policy_set_refs: list[str] | None = None,
        jurisdiction: str | None = None,
        matched_rules: list[str] | None = None,
        obligations: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> PolicyDecision:
        # The verdict is the server's (AGP 1.0, §2.1): name the PolicySet, or several (the most restrictive wins).
        # A verdict sent is kept as caller_verdict and doesn't count — except on a v0.5-profile server.
        body: dict[str, Any] = {
            "task_id": task_id,
            "decision_ref": decision_ref,
            "evaluated_at": _now(),
        }
        if verdict:
            body["verdict"] = verdict
        if policy_set_refs:
            body["policy_set_refs"] = policy_set_refs
        if rationale:
            body["rationale"] = rationale
        if policy_set_ref:
            body["policy_set_ref"] = policy_set_ref
        if jurisdiction:
            body["jurisdiction"] = jurisdiction
        if matched_rules:
            body["matched_rules"] = matched_rules
        if obligations:
            body["obligations"] = obligations
        raw = self._t.post("/agp/decision/policy-evaluations", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return PolicyDecision.model_validate(raw)

    def get_policy_evaluation(self, policy_evaluation_id: str) -> PolicyDecision:
        return PolicyDecision.model_validate(
            self._t.get(f"/agp/decision/policy-evaluations/{policy_evaluation_id}")
        )

    # ── Approvals ──────────────────────────────────────────────────────────

    def create_approval(
        self,
        *,
        task_id: str,
        approver_id: str,
        decision: ApprovalDecision,
        notes: str | None = None,
        idempotency_key: str | None = None,
    ) -> ApprovalArtifact:
        body: dict[str, Any] = {
            "task_id": task_id,
            "approver_id": approver_id,
            "decision": decision,
            "approved_at": _now(),
        }
        if notes:
            body["notes"] = notes
        raw = self._t.post("/agp/decision/approvals", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return ApprovalArtifact.model_validate(raw)

    def get_approval(self, approval_id: str) -> ApprovalArtifact:
        return ApprovalArtifact.model_validate(
            self._t.get(f"/agp/decision/approvals/{approval_id}")
        )

    # ── Escalations ────────────────────────────────────────────────────────

    def escalate(
        self,
        *,
        task_id: str,
        raised_by: str,
        concern_type: str,
        description: str,
        idempotency_key: str | None = None,
    ) -> EscalationNotice:
        body = {
            "task_id": task_id,
            "raised_by": raised_by,
            "concern_type": concern_type,
            "description": description,
            "raised_at": _now(),
        }
        raw = self._t.post("/agp/decision/escalations", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return EscalationNotice.model_validate(raw)
