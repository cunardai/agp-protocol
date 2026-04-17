"""
AGP Conformance Test Client

Thin wrapper around requests. Every test imports this module to get a
pre-configured session pointed at the server under test.

Usage:
    from client import AGPClient
    c = AGPClient("http://localhost:8099")
    task = c.post("/agp/tasks", {...}).json()
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class AGPClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    # ── Low-level ─────────────────────────────────────────────────────────

    def post(self, path: str, body: dict, *, idempotency_key: str | None = None,
             prefer: str | None = None) -> requests.Response:
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if prefer:
            headers["Prefer"] = prefer
        return self.session.post(f"{self.base}{path}", json=body, headers=headers)

    def get(self, path: str, **params) -> requests.Response:
        return self.session.get(f"{self.base}{path}", params=params)

    def patch(self, path: str, body: dict, *, idempotency_key: str | None = None) -> requests.Response:
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return self.session.patch(f"{self.base}{path}", json=body, headers=headers)

    # ── Convenience builders ───────────────────────────────────────────────

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def future(self, days: int = 30) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    def past(self, seconds: int = 10) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()

    def uid(self) -> str:
        return uuid.uuid4().hex[:8]

    # ── Resource builders ──────────────────────────────────────────────────

    def create_task(self, **overrides) -> dict:
        body: dict[str, Any] = {
            "principal_id": f"principal-{self.uid()}",
            "requested_outcome": "conformance test action",
            "risk_tier": "low",
            "created_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/tasks", body)
        assert r.status_code == 201, f"create_task failed: {r.text}"
        return r.json()

    def create_policy_set(self, **overrides) -> dict:
        body: dict[str, Any] = {
            "name": f"Test PolicySet {self.uid()}",
            "version": "1.0.0",
            "publisher": "conformance-suite",
            "regulatory_frameworks": ["EU_AI_ACT_2024"],
            "jurisdictions": ["EU"],
            "ruleset_hash": f"sha256:{self.uid()}",
            "ruleset_engine": "opa",
            "attestation_level": "self_attested",
            "effective_from": self.now(),
            "created_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/policy-sets", body)
        assert r.status_code == 201, f"create_policy_set failed: {r.text}"
        return r.json()

    def bind_liability(self, task_id: str, **overrides) -> dict:
        body: dict[str, Any] = {
            "task_id": task_id,
            "sponsoring_entity": f"entity-{self.uid()}",
            "accountable_owner": f"owner-{self.uid()}@example.com",
            "jurisdiction": "EU",
            "risk_tier": "low",
            "created_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/liability-bindings", body)
        assert r.status_code == 201, f"bind_liability failed: {r.text}"
        return r.json()

    def issue_capability(self, task_id: str, **overrides) -> dict:
        body: dict[str, Any] = {
            "subject_agent": f"agent-{self.uid()}",
            "issuer": f"issuer-{self.uid()}",
            "principal_id": f"principal-{self.uid()}",
            "permitted_actions": ["test_action"],
            "constraints": {},
            "expires_at": self.future(),
            "revocation_id": f"rev-{self.uid()}",
        }
        body.update(overrides)
        r = self.post("/agp/capabilities", body)
        assert r.status_code == 201, f"issue_capability failed: {r.text}"
        return r.json()

    def create_decision(self, task_id: str, **overrides) -> dict:
        body: dict[str, Any] = {
            "task_id": task_id,
            "agent_id": f"agent-{self.uid()}",
            "selected_action": "test_action",
            "rationale": "conformance test decision",
            "uncertainty_score": 0.1,
            "created_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/decision/decisions", body)
        assert r.status_code == 201, f"create_decision failed: {r.text}"
        return r.json()

    def create_policy_evaluation(self, task_id: str, decision_id: str, **overrides) -> dict:
        body: dict[str, Any] = {
            "task_id": task_id,
            "decision_ref": decision_id,
            "verdict": "allow",
            "evaluated_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/decision/policy-evaluations", body)
        assert r.status_code == 201, f"create_policy_evaluation failed: {r.text}"
        return r.json()

    def create_approval(self, task_id: str, decision: str = "approved", **overrides) -> dict:
        body: dict[str, Any] = {
            "task_id": task_id,
            "approver_id": f"approver-{self.uid()}",
            "decision": decision,
            "approved_at": self.now(),
        }
        body.update(overrides)
        r = self.post("/agp/decision/approvals", body)
        assert r.status_code == 201, f"create_approval failed: {r.text}"
        return r.json()

    def advance(self, task_id: str, status: str) -> dict:
        r = self.patch(f"/agp/tasks/{task_id}", {"status": status})
        assert r.status_code == 200, f"advance to {status} failed: {r.text}"
        return r.json()

    # ── Full lifecycle helpers ─────────────────────────────────────────────

    def setup_to_decided(self, risk_tier: str = "low") -> dict:
        """Returns dict with task, token, decision ready for policy evaluation."""
        task = self.create_task(risk_tier=risk_tier)
        task_id = task["task_id"]
        token = self.issue_capability(task_id)
        self.bind_liability(task_id, risk_tier=risk_tier)
        self.advance(task_id, "ANALYZING")
        decision = self.create_decision(task_id)
        return {"task": task, "token": token, "decision": decision}

    def setup_to_policy_checked(self, risk_tier: str = "low",
                                verdict: str = "allow",
                                policy_set_id: str | None = None) -> dict:
        """Returns dict with everything needed for action envelope."""
        ctx = self.setup_to_decided(risk_tier=risk_tier)
        task_id = ctx["task"]["task_id"]
        dec_id = ctx["decision"]["decision_id"]
        pe_kwargs: dict[str, Any] = {"verdict": verdict}
        if verdict in ("deny", "quarantine"):
            pe_kwargs["rationale"] = "conformance test denial"
        if policy_set_id:
            pe_kwargs["policy_set_ref"] = policy_set_id
        pe = self.create_policy_evaluation(task_id, dec_id, **pe_kwargs)
        ctx["policy_eval"] = pe
        return ctx

    def setup_for_execution(self, risk_tier: str = "low") -> dict:
        """Full setup ready to POST /agp/action-envelopes."""
        ctx = self.setup_to_policy_checked(risk_tier=risk_tier)
        task_id = ctx["task"]["task_id"]
        if risk_tier in ("high", "critical"):
            approval = self.create_approval(task_id)
            ctx["approval"] = approval
        self.advance(task_id, "EXECUTING")
        return ctx
