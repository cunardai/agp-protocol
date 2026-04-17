"""
§15 Idempotency — AGP Conformance Tests

Any POST with an Idempotency-Key must return the same object on repeat
calls without creating duplicates. This is critical for safe retry logic.
"""


class TestIdempotency:
    """§15 Idempotency-Key semantics"""

    def test_task_idempotency(self, c):
        """§15.1 — Repeated task creation with same key returns same task_id."""
        key = f"idem-task-{c.uid()}"
        body = {
            "principal_id": "agent-idem",
            "requested_outcome": "test idempotency",
            "risk_tier": "low",
            "created_at": c.now(),
        }
        r1 = c.post("/agp/tasks", body, idempotency_key=key)
        r2 = c.post("/agp/tasks", body, idempotency_key=key)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["task_id"] == r2.json()["task_id"]

    def test_liability_binding_idempotency(self, c):
        """§15.1 — Repeated binding creation returns same binding_id."""
        task = c.create_task()
        key = f"idem-lib-{c.uid()}"
        body = {
            "task_id": task["task_id"],
            "sponsoring_entity": "acme", "accountable_owner": "cto@acme.com",
            "jurisdiction": "EU", "risk_tier": "low", "created_at": c.now(),
        }
        r1 = c.post("/agp/liability-bindings", body, idempotency_key=key)
        r2 = c.post("/agp/liability-bindings", body, idempotency_key=key)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["binding_id"] == r2.json()["binding_id"]

    def test_decision_idempotency(self, c):
        """§15.1 — Repeated decision creation returns same decision_id."""
        task = c.create_task()
        c.bind_liability(task["task_id"])
        c.advance(task["task_id"], "ANALYZING")
        key = f"idem-dec-{c.uid()}"
        body = {
            "task_id": task["task_id"], "agent_id": "agent-001",
            "selected_action": "test", "rationale": "idempotency test",
            "uncertainty_score": 0.1, "created_at": c.now(),
        }
        r1 = c.post("/agp/decision/decisions", body, idempotency_key=key)
        r2 = c.post("/agp/decision/decisions", body, idempotency_key=key)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["decision_id"] == r2.json()["decision_id"]

    def test_policy_evaluation_idempotency(self, c):
        """§15.1 — Repeated policy evaluation returns same policy_evaluation_id."""
        ctx = c.setup_to_decided()
        key = f"idem-pe-{c.uid()}"
        body = {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow", "evaluated_at": c.now(),
        }
        r1 = c.post("/agp/decision/policy-evaluations", body, idempotency_key=key)
        r2 = c.post("/agp/decision/policy-evaluations", body, idempotency_key=key)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["policy_evaluation_id"] == r2.json()["policy_evaluation_id"]

    def test_policy_set_idempotency(self, c):
        """§15.1 — Repeated PolicySet registration returns same policy_set_id."""
        key = f"idem-pset-{c.uid()}"
        body = {
            "name": f"idem-pset-{c.uid()}", "version": "1.0.0",
            "publisher": "conformance-suite",
            "regulatory_frameworks": ["EU_AI_ACT_2024"], "jurisdictions": ["EU"],
            "ruleset_hash": f"sha256:{c.uid()}", "ruleset_engine": "opa",
            "attestation_level": "self_attested",
            "effective_from": c.now(), "created_at": c.now(),
        }
        r1 = c.post("/agp/policy-sets", body, idempotency_key=key)
        r2 = c.post("/agp/policy-sets", body, idempotency_key=key)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["policy_set_id"] == r2.json()["policy_set_id"]

    def test_without_idempotency_key_creates_new_resource(self, c):
        """§15.2 — Requests without Idempotency-Key create separate resources."""
        body = {
            "principal_id": "agent-no-idem",
            "requested_outcome": "test",
            "risk_tier": "low",
            "created_at": c.now(),
        }
        r1 = c.post("/agp/tasks", body)
        r2 = c.post("/agp/tasks", body)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["task_id"] != r2.json()["task_id"]
