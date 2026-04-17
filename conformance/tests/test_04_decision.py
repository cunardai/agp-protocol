"""
§10-§13 Decision Domain — AGP Conformance Tests

Covers: decisions, policy evaluations, approvals, escalations,
        policy_set_ref validation, verdict enforcement.
"""
import pytest


class TestDecisions:
    """§10 Decision Records"""

    def test_create_decision(self, c):
        """§10.1 — DecisionRecord is created and task advances to DECIDED."""
        task = c.create_task()
        c.bind_liability(task["task_id"])
        c.advance(task["task_id"], "ANALYZING")
        r = c.post("/agp/decision/decisions", {
            "task_id": task["task_id"],
            "agent_id": "agent-001",
            "selected_action": "analyse",
            "rationale": "safe action",
            "uncertainty_score": 0.1,
            "created_at": c.now(),
        })
        assert r.status_code == 201
        assert r.json()["type"] == "DecisionRecord"
        # Task should auto-advance to DECIDED
        t = c.get(f"/agp/tasks/{task['task_id']}").json()
        assert t["status"] == "DECIDED"

    @pytest.mark.parametrize("missing", ["task_id", "agent_id", "selected_action",
                                          "rationale", "uncertainty_score", "created_at"])
    def test_decision_missing_required_field(self, c, missing):
        """§10.1 — Missing required field returns 400."""
        task = c.create_task()
        c.bind_liability(task["task_id"])
        c.advance(task["task_id"], "ANALYZING")
        body = {
            "task_id": task["task_id"], "agent_id": "agent-001",
            "selected_action": "test", "rationale": "test",
            "uncertainty_score": 0.1, "created_at": c.now(),
        }
        del body[missing]
        r = c.post("/agp/decision/decisions", body)
        assert r.status_code == 400

    def test_get_decision(self, c):
        """§10.1 — DecisionRecord is retrievable by ID."""
        ctx = c.setup_to_decided()
        dec_id = ctx["decision"]["decision_id"]
        r = c.get(f"/agp/decision/decisions/{dec_id}")
        assert r.status_code == 200
        assert r.json()["decision_id"] == dec_id

    def test_get_decision_not_found(self, c):
        """§10.1 — Unknown decision_id returns 404."""
        r = c.get("/agp/decision/decisions/dec_doesnotexist")
        assert r.status_code == 404


class TestPolicyEvaluations:
    """§11 Policy Evaluations"""

    def test_allow_verdict_advances_task_to_policy_checked(self, c):
        """§11.1 — allow verdict auto-advances task to POLICY_CHECKED."""
        ctx = c.setup_to_decided()
        c.create_policy_evaluation(ctx["task"]["task_id"], ctx["decision"]["decision_id"])
        t = c.get(f"/agp/tasks/{ctx['task']['task_id']}").json()
        assert t["status"] == "POLICY_CHECKED"

    def test_deny_verdict_advances_task_to_denied(self, c):
        """§11.1 — deny verdict auto-advances task to DENIED."""
        ctx = c.setup_to_decided()
        c.create_policy_evaluation(
            ctx["task"]["task_id"], ctx["decision"]["decision_id"],
            verdict="deny", rationale="test denial",
        )
        t = c.get(f"/agp/tasks/{ctx['task']['task_id']}").json()
        assert t["status"] == "DENIED"

    def test_require_approval_advances_task_to_approval_pending(self, c):
        """§11.1 — require_approval verdict auto-advances to APPROVAL_PENDING."""
        ctx = c.setup_to_decided()
        c.create_policy_evaluation(
            ctx["task"]["task_id"], ctx["decision"]["decision_id"],
            verdict="require_approval",
        )
        t = c.get(f"/agp/tasks/{ctx['task']['task_id']}").json()
        assert t["status"] == "APPROVAL_PENDING"

    def test_quarantine_verdict_advances_task_to_quarantined(self, c):
        """§11.1 — quarantine verdict auto-advances to QUARANTINED."""
        ctx = c.setup_to_decided()
        c.create_policy_evaluation(
            ctx["task"]["task_id"], ctx["decision"]["decision_id"],
            verdict="quarantine", rationale="flagged for review",
        )
        t = c.get(f"/agp/tasks/{ctx['task']['task_id']}").json()
        assert t["status"] == "QUARANTINED"

    def test_deny_without_rationale_rejected(self, c):
        """§11.2 — deny verdict without rationale returns 400."""
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "deny",
            "evaluated_at": c.now(),
            # no rationale
        })
        assert r.status_code == 400

    def test_quarantine_without_rationale_rejected(self, c):
        """§11.2 — quarantine verdict without rationale returns 400."""
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "quarantine",
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    def test_invalid_verdict_rejected(self, c):
        """§11.2 — Unknown verdict value returns 400."""
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "maybe",
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    def test_nonexistent_decision_ref_rejected(self, c):
        """§11.2 — Referencing unknown DecisionRecord returns 400."""
        task = c.create_task()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": task["task_id"],
            "decision_ref": "dec_doesnotexist",
            "verdict": "allow",
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    def test_policy_set_ref_valid_active_accepted(self, c):
        """§11.3 v0.6 — Policy evaluation referencing active PolicySet is accepted."""
        ps = c.create_policy_set()
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow",
            "policy_set_ref": ps["policy_set_id"],
            "evaluated_at": c.now(),
        })
        assert r.status_code == 201
        assert r.json()["policy_set_ref"] == ps["policy_set_id"]

    def test_policy_set_ref_deprecated_rejected(self, c):
        """§11.3 v0.6 — Referencing a deprecated PolicySet returns 400."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "deprecated"})
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow",
            "policy_set_ref": ps["policy_set_id"],
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    def test_policy_set_ref_revoked_rejected(self, c):
        """§11.3 v0.6 — Referencing a revoked PolicySet returns 400."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "revoked"})
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow",
            "policy_set_ref": ps["policy_set_id"],
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    def test_policy_set_ref_nonexistent_rejected(self, c):
        """§11.3 v0.6 — Referencing an unknown PolicySet returns 400."""
        ctx = c.setup_to_decided()
        r = c.post("/agp/decision/policy-evaluations", {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow",
            "policy_set_ref": "pset_doesnotexist",
            "evaluated_at": c.now(),
        })
        assert r.status_code == 400

    @pytest.mark.parametrize("missing", ["task_id", "decision_ref", "verdict", "evaluated_at"])
    def test_policy_eval_missing_required_field(self, c, missing):
        """§11.2 — Missing required field returns 400."""
        ctx = c.setup_to_decided()
        body = {
            "task_id": ctx["task"]["task_id"],
            "decision_ref": ctx["decision"]["decision_id"],
            "verdict": "allow",
            "evaluated_at": c.now(),
        }
        del body[missing]
        r = c.post("/agp/decision/policy-evaluations", body)
        assert r.status_code == 400


class TestApprovals:
    """§12 Approval Artifacts"""

    def test_approved_decision_advances_task(self, c):
        """§12.1 — approved decision advances APPROVAL_PENDING → POLICY_CHECKED."""
        ctx = c.setup_to_decided()
        task_id = ctx["task"]["task_id"]
        c.create_policy_evaluation(task_id, ctx["decision"]["decision_id"],
                                   verdict="require_approval")
        t = c.get(f"/agp/tasks/{task_id}").json()
        assert t["status"] == "APPROVAL_PENDING"

        c.create_approval(task_id, decision="approved")
        t = c.get(f"/agp/tasks/{task_id}").json()
        assert t["status"] == "POLICY_CHECKED"

    def test_denied_approval_advances_to_denied(self, c):
        """§12.1 — denied approval advances APPROVAL_PENDING → DENIED."""
        ctx = c.setup_to_decided()
        task_id = ctx["task"]["task_id"]
        c.create_policy_evaluation(task_id, ctx["decision"]["decision_id"],
                                   verdict="require_approval")
        c.create_approval(task_id, decision="denied")
        t = c.get(f"/agp/tasks/{task_id}").json()
        assert t["status"] == "DENIED"

    def test_invalid_approval_decision_rejected(self, c):
        """§12.1 — Unknown approval decision value returns 400."""
        ctx = c.setup_to_decided()
        task_id = ctx["task"]["task_id"]
        c.create_policy_evaluation(task_id, ctx["decision"]["decision_id"],
                                   verdict="require_approval")
        r = c.post("/agp/decision/approvals", {
            "task_id": task_id,
            "approver_id": "approver-001",
            "decision": "maybe",
            "approved_at": c.now(),
        })
        assert r.status_code == 400


class TestEscalations:
    """§13 Escalations"""

    def test_create_escalation(self, c):
        """§13.1 — EscalationNotice is created and retrievable."""
        task = c.create_task()
        r = c.post("/agp/decision/escalations", {
            "task_id": task["task_id"],
            "raised_by": "agent-001",
            "concern_type": "safety",
            "description": "Potential harm to vulnerable group",
            "raised_at": c.now(),
        })
        assert r.status_code == 201
        assert r.json()["escalation_id"].startswith("esc_")

    @pytest.mark.parametrize("missing", ["task_id", "raised_by", "concern_type",
                                          "description", "raised_at"])
    def test_escalation_missing_required_field(self, c, missing):
        """§13.1 — Missing required field returns 400."""
        task = c.create_task()
        body = {
            "task_id": task["task_id"], "raised_by": "agent-001",
            "concern_type": "safety", "description": "test", "raised_at": c.now(),
        }
        del body[missing]
        r = c.post("/agp/decision/escalations", body)
        assert r.status_code == 400
