"""
§16 Error Response Format — AGP Conformance Tests

All error responses must use the AGP error envelope:
  { "error": { "code": "AGP_*", "message": "..." } }

A server that returns bare HTTP errors or non-AGP bodies is non-conformant.
"""


def _is_agp_error(body: dict) -> bool:
    """Check that the body follows the AGP error envelope format."""
    return (
        isinstance(body, dict)
        and "error" in body
        and isinstance(body["error"], dict)
        and "code" in body["error"]
        and "message" in body["error"]
    )


class TestErrorEnvelope:
    """§16 Error envelope format"""

    def test_400_uses_agp_error_envelope(self, c):
        """§16.1 — 400 responses use AGP error envelope."""
        r = c.post("/agp/tasks", {
            "principal_id": "agent-001",
            # missing required fields
        })
        assert r.status_code == 400
        assert _is_agp_error(r.json()), f"Expected AGP error envelope, got: {r.text}"

    def test_404_uses_agp_error_envelope(self, c):
        """§16.1 — 404 responses use AGP error envelope."""
        r = c.get("/agp/tasks/tsk_doesnotexist")
        assert r.status_code == 404
        assert _is_agp_error(r.json()), f"Expected AGP error envelope, got: {r.text}"

    def test_422_uses_agp_error_envelope(self, c):
        """§16.1 — 422 responses use AGP error envelope."""
        task = c.create_task()
        r = c.patch(f"/agp/tasks/{task['task_id']}", {"status": "COMPLETED"})
        assert r.status_code == 422
        assert _is_agp_error(r.json()), f"Expected AGP error envelope, got: {r.text}"

    def test_409_uses_agp_error_envelope(self, c):
        """§16.1 — 409 responses use AGP error envelope."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "revoked"})
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "active"})
        assert r.status_code in (409, 422)
        assert _is_agp_error(r.json()), f"Expected AGP error envelope, got: {r.text}"

    def test_error_code_starts_with_agp_prefix(self, c):
        """§16.2 — Error codes must use AGP_ prefix."""
        r = c.get("/agp/tasks/tsk_doesnotexist")
        body = r.json()
        code = body.get("error", {}).get("code", "")
        assert code.startswith("AGP_"), f"Error code '{code}' does not use AGP_ prefix"

    def test_execution_gate_422_includes_section_reference(self, c):
        """§16.3 — Execution gate 422 errors should reference the violated section (§10.x)."""
        ctx = c.setup_to_policy_checked()
        c.advance(ctx["task"]["task_id"], "EXECUTING")
        body = {
            "task_id": ctx["task"]["task_id"],
            "agent_id": "agent-001",
            "tool_id": "tool",
            "operation": {},
            "capability_token_ref": "cap_doesnotexist",
            "decision_ref": ctx["decision"]["decision_id"],
            "policy_decision_ref": ctx["policy_eval"]["policy_evaluation_id"],
            "created_at": c.now(),
        }
        r = c.post("/agp/action-envelopes", body)
        assert r.status_code == 422
        msg = r.json().get("error", {}).get("message", "")
        assert "§10" in msg or "10." in msg, (
            f"Expected section reference in message, got: {msg!r}"
        )


class TestHealthEndpoint:
    """§1 Health and server identity"""

    def test_health_returns_ok(self, c):
        """§1.1 — /health returns 200 with status=ok."""
        import requests as req
        r = req.get(f"{c.base}/health")
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"

    def test_health_includes_version(self, c):
        """§1.1 — /health response includes version field."""
        import requests as req
        r = req.get(f"{c.base}/health")
        assert "version" in r.json()

    def test_health_includes_storage_backend(self, c):
        """§1.1 — /health response includes storage backend type."""
        import requests as req
        r = req.get(f"{c.base}/health")
        assert "storage" in r.json()
