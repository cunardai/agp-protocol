"""
§4 Task Registry — AGP Conformance Tests

Covers: task creation, field validation, listing, retrieval.
"""
import pytest


class TestTaskCreation:
    """§4.1 Task creation"""

    def test_create_task_minimal(self, c):
        """§4.1 — Minimal required fields produce a CREATED task."""
        r = c.post("/agp/tasks", {
            "principal_id": "agent-001",
            "requested_outcome": "test",
            "risk_tier": "low",
            "created_at": c.now(),
        })
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "CREATED"
        assert body["task_id"].startswith("tsk_")
        assert body["principal_id"] == "agent-001"

    def test_create_task_with_v06_fields(self, c):
        """§4.1 v0.6 — Tasks accept jurisdictions and regulatory_frameworks."""
        r = c.post("/agp/tasks", {
            "principal_id": "agent-001",
            "requested_outcome": "test",
            "risk_tier": "medium",
            "created_at": c.now(),
            "jurisdictions": ["EU", "EEA"],
            "regulatory_frameworks": ["EU_AI_ACT_2024"],
        })
        assert r.status_code == 201
        body = r.json()
        assert "EU" in body["jurisdictions"]
        assert "EU_AI_ACT_2024" in body["regulatory_frameworks"]

    def test_create_task_all_risk_tiers(self, c):
        """§4.1 — All four risk tiers are accepted."""
        for tier in ("low", "medium", "high", "critical"):
            r = c.post("/agp/tasks", {
                "principal_id": "agent-001",
                "requested_outcome": "test",
                "risk_tier": tier,
                "created_at": c.now(),
            })
            assert r.status_code == 201, f"risk_tier={tier} rejected: {r.text}"

    def test_create_task_invalid_risk_tier(self, c):
        """§4.1 — Unknown risk_tier is rejected with 400."""
        r = c.post("/agp/tasks", {
            "principal_id": "agent-001",
            "requested_outcome": "test",
            "risk_tier": "extreme",
            "created_at": c.now(),
        })
        assert r.status_code == 400

    @pytest.mark.parametrize("missing_field", ["principal_id", "requested_outcome", "risk_tier", "created_at"])
    def test_create_task_missing_required_field(self, c, missing_field):
        """§4.1 — Missing required field returns 400."""
        body = {
            "principal_id": "agent-001",
            "requested_outcome": "test",
            "risk_tier": "low",
            "created_at": c.now(),
        }
        del body[missing_field]
        r = c.post("/agp/tasks", body)
        assert r.status_code == 400


class TestTaskRetrieval:
    """§4.2 Task retrieval"""

    def test_get_task(self, c):
        """§4.2 — Created task is retrievable by ID."""
        task = c.create_task()
        r = c.get(f"/agp/tasks/{task['task_id']}")
        assert r.status_code == 200
        assert r.json()["task_id"] == task["task_id"]

    def test_get_task_not_found(self, c):
        """§4.2 — Unknown task_id returns 404."""
        r = c.get("/agp/tasks/tsk_doesnotexist")
        assert r.status_code == 404

    def test_list_tasks(self, c):
        """§4.2 — List endpoint returns items array with pagination metadata."""
        c.create_task(principal_id="list-test-principal")
        r = c.get("/agp/tasks")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "page" in body
        assert "has_more" in body["page"]

    def test_list_tasks_filter_by_principal(self, c):
        """§4.2 — principal_id filter returns only matching tasks."""
        uid = c.uid()
        c.create_task(principal_id=f"filter-principal-{uid}")
        c.create_task(principal_id="other-principal")
        r = c.get("/agp/tasks", principal_id=f"filter-principal-{uid}")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(t["principal_id"] == f"filter-principal-{uid}" for t in items)

    def test_list_tasks_filter_by_status(self, c):
        """§4.2 — status filter returns only tasks in that state."""
        task = c.create_task()
        r = c.get("/agp/tasks", status="CREATED")
        items = r.json()["items"]
        assert any(t["task_id"] == task["task_id"] for t in items)
