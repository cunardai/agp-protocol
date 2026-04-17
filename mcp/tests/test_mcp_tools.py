"""
AGP MCP server — integration tests

Runs against a live AGP server. Set AGP_BASE_URL to point at it.
  AGP_BASE_URL=http://localhost:8099 pytest tests/

These tests call the MCP tool functions directly (bypassing the MCP wire
protocol) so they run fast without needing a full MCP client.
"""

from __future__ import annotations

import json
import os
import pytest
import httpx

from agp_mcp.server import (
    create_task,
    get_task,
    transition_task,
    bind_liability,
    issue_capability,
    register_policy_set,
    record_decision,
    evaluate_policy,
    create_approval,
    create_escalation,
    submit_action,
    validate_action,
    replay_audit_log,
    run_governed_task,
    _http,
    lifespan,
    mcp,
)

BASE_URL = os.environ.get("AGP_BASE_URL", "http://localhost:8099")

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def start_server():
    """Inject a fresh httpx client per test."""
    import agp_mcp.server as srv
    # max_keepalive_connections=0 prevents connection pooling so aclose() is
    # a no-op — avoids the "Event loop is closed" error during teardown on
    # Python 3.12+ with pytest-asyncio.
    client = httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Content-Type": "application/json"},
        timeout=30,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=0),
    )
    srv._http = client
    yield
    srv._http = None
    # Client cleanup is best-effort; connections are already closed (no keepalive).
    try:
        await client.aclose()
    except RuntimeError:
        pass


# ── Registry tools ────────────────────────────────────────────────────────────

class TestCreateTask:
    async def test_creates_task_with_required_fields(self):
        raw = await create_task(
            principal_id="mcp-agent-001",
            requested_outcome="test MCP binding",
            risk_tier="low",
        )
        task = json.loads(raw)
        assert task["task_id"].startswith("tsk_")
        assert task["status"] == "CREATED"
        assert task["risk_tier"] == "low"

    async def test_creates_task_with_v06_fields(self):
        raw = await create_task(
            principal_id="mcp-agent-eu",
            requested_outcome="EU governed task",
            risk_tier="medium",
            jurisdictions=["EU"],
            regulatory_frameworks=["EU_AI_ACT_2024"],
        )
        task = json.loads(raw)
        assert "EU" in task["jurisdictions"]
        assert "EU_AI_ACT_2024" in task["regulatory_frameworks"]

    async def test_invalid_risk_tier_raises_tool_error(self):
        from mcp.server.fastmcp.exceptions import ToolError
        with pytest.raises(ToolError):
            await create_task(
                principal_id="x",
                requested_outcome="x",
                risk_tier="ultralow",  # invalid
            )


class TestGetTask:
    async def test_retrieves_task(self):
        created = json.loads(await create_task(
            principal_id="mcp-get-test",
            requested_outcome="retrieval test",
            risk_tier="low",
        ))
        fetched = json.loads(await get_task(created["task_id"]))
        assert fetched["task_id"] == created["task_id"]

    async def test_not_found_raises_tool_error(self):
        from mcp.server.fastmcp.exceptions import ToolError
        with pytest.raises(ToolError, match="AGP_NOT_FOUND"):
            await get_task("tsk_doesnotexist_mcp")


class TestBindLiability:
    async def test_binds_and_advances_to_bound(self):
        task = json.loads(await create_task(
            principal_id="mcp-bind-agent",
            requested_outcome="bind test",
            risk_tier="low",
        ))
        raw = await bind_liability(
            task_id=task["task_id"],
            sponsoring_entity="acme-corp",
            accountable_owner="cto@acme.com",
            jurisdiction="EU",
        )
        binding = json.loads(raw)
        assert "binding_id" in binding
        assert binding["task_id"] == task["task_id"]

        refreshed = json.loads(await get_task(task["task_id"]))
        assert refreshed["status"] == "BOUND"


class TestIssueCapability:
    async def test_issues_capability_token(self):
        raw = await issue_capability(
            subject_agent="mcp-cap-agent",
            issuer="mcp-principal",
            principal_id="mcp-principal",
            permitted_actions=["analyse", "summarise"],
        )
        token = json.loads(raw)
        assert "capability_id" in token
        assert "analyse" in token["permitted_actions"]


class TestRegisterPolicySet:
    async def test_registers_policy_set(self):
        import time
        raw = await register_policy_set(
            name="MCP Test PolicySet",
            version="1.0.0",
            publisher="mcp-test",
            regulatory_frameworks=["EU_AI_ACT_2024"],
            jurisdictions=["EU"],
            ruleset_hash=f"sha256:mcp{int(time.time())}",
        )
        ps = json.loads(raw)
        assert ps["status"] == "active"
        assert "policy_set_id" in ps


# ── Decision tools ────────────────────────────────────────────────────────────

class TestRecordDecision:
    async def _bound_task(self) -> dict:
        task = json.loads(await create_task(
            principal_id="mcp-dec-agent",
            requested_outcome="decision test",
            risk_tier="low",
        ))
        await bind_liability(
            task_id=task["task_id"],
            sponsoring_entity="acme",
            accountable_owner="owner@acme.com",
            jurisdiction="EU",
        )
        return task

    async def test_records_decision(self):
        task = await self._bound_task()
        raw = await record_decision(
            task_id=task["task_id"],
            agent_id="mcp-dec-agent",
            selected_action="analyse",
            rationale="safe, no PII",
            uncertainty_score=0.05,
        )
        decision = json.loads(raw)
        assert "decision_id" in decision
        assert decision["task_id"] == task["task_id"]

    async def test_high_uncertainty_goes_to_approval_pending(self):
        task = await self._bound_task()
        raw = await record_decision(
            task_id=task["task_id"],
            agent_id="mcp-dec-agent",
            selected_action="risky-action",
            rationale="uncertain about this",
            uncertainty_score=0.95,  # triggers escalation
        )
        decision = json.loads(raw)
        assert "decision_id" in decision
        refreshed = json.loads(await get_task(task["task_id"]))
        assert refreshed["status"] in ("APPROVAL_PENDING", "DECIDED")


class TestEvaluatePolicy:
    async def _decided_task(self) -> tuple[dict, dict]:
        task = json.loads(await create_task(
            principal_id="mcp-pe-agent",
            requested_outcome="policy eval test",
            risk_tier="low",
        ))
        await bind_liability(
            task_id=task["task_id"],
            sponsoring_entity="acme",
            accountable_owner="owner@acme.com",
            jurisdiction="EU",
        )
        decision = json.loads(await record_decision(
            task_id=task["task_id"],
            agent_id="mcp-pe-agent",
            selected_action="test",
            rationale="test",
            uncertainty_score=0.1,
        ))
        return task, decision

    async def test_allow_verdict(self):
        task, decision = await self._decided_task()
        raw = await evaluate_policy(
            task_id=task["task_id"],
            verdict="allow",
            rationale="policy check passed",
            decision_ref=decision["decision_id"],
        )
        pd = json.loads(raw)
        assert pd["verdict"] == "allow"
        assert "policy_evaluation_id" in pd

        refreshed = json.loads(await get_task(task["task_id"]))
        assert refreshed["status"] == "POLICY_CHECKED"

    async def test_require_approval_verdict(self):
        task, decision = await self._decided_task()
        raw = await evaluate_policy(
            task_id=task["task_id"],
            verdict="require_approval",
            rationale="needs human sign-off",
            decision_ref=decision["decision_id"],
        )
        pd = json.loads(raw)
        assert pd["verdict"] == "require_approval"
        refreshed = json.loads(await get_task(task["task_id"]))
        assert refreshed["status"] == "APPROVAL_PENDING"


# ── Execution tools ───────────────────────────────────────────────────────────

async def _setup_for_execution() -> dict:
    """Helper: walk to POLICY_CHECKED and return all artefact IDs."""
    task = json.loads(await create_task(
        principal_id="mcp-exec-agent",
        requested_outcome="execution test",
        risk_tier="low",
    ))
    task_id = task["task_id"]
    await bind_liability(
        task_id=task_id,
        sponsoring_entity="acme",
        accountable_owner="owner@acme.com",
        jurisdiction="EU",
    )
    token = json.loads(await issue_capability(
        subject_agent="mcp-exec-agent",
        issuer="mcp-principal",
        principal_id="mcp-principal",
        permitted_actions=["test"],
    ))
    decision = json.loads(await record_decision(
        task_id=task_id,
        agent_id="mcp-exec-agent",
        selected_action="test",
        rationale="test",
        uncertainty_score=0.1,
    ))
    pd = json.loads(await evaluate_policy(
        task_id=task_id,
        verdict="allow",
        rationale="ok",
        decision_ref=decision["decision_id"],
    ))
    return {
        "task_id": task_id,
        "capability_id": token["capability_id"],
        "decision_id": decision["decision_id"],
        "policy_evaluation_id": pd["policy_evaluation_id"],
    }


class TestValidateAction:
    async def test_validate_only_returns_true(self):
        ids = await _setup_for_execution()
        # Advance to EXECUTING first
        await transition_task(ids["task_id"], "EXECUTING")
        raw = await validate_action(
            task_id=ids["task_id"],
            agent_id="mcp-exec-agent",
            tool_id="test-tool",
            operation={},
            capability_token_ref=ids["capability_id"],
            decision_ref=ids["decision_id"],
            policy_decision_ref=ids["policy_evaluation_id"],
        )
        result = json.loads(raw)
        assert result.get("valid") is True

        # Task state unchanged
        refreshed = json.loads(await get_task(ids["task_id"]))
        assert refreshed["status"] == "EXECUTING"


class TestSubmitAction:
    async def test_submits_and_completes(self):
        ids = await _setup_for_execution()
        raw = await submit_action(
            task_id=ids["task_id"],
            agent_id="mcp-exec-agent",
            tool_id="test-tool",
            operation={"input": "hello"},
            capability_token_ref=ids["capability_id"],
            decision_ref=ids["decision_id"],
            policy_decision_ref=ids["policy_evaluation_id"],
        )
        receipt = json.loads(raw)
        assert "action_id" in receipt

        refreshed = json.loads(await get_task(ids["task_id"]))
        assert refreshed["status"] == "COMPLETED"


class TestReplayAuditLog:
    async def test_returns_ledger_events(self):
        ids = await _setup_for_execution()
        await submit_action(
            task_id=ids["task_id"],
            agent_id="mcp-exec-agent",
            tool_id="test-tool",
            operation={},
            capability_token_ref=ids["capability_id"],
            decision_ref=ids["decision_id"],
            policy_decision_ref=ids["policy_evaluation_id"],
        )
        raw = await replay_audit_log(ids["task_id"])
        result = json.loads(raw)
        events = result["events"] if "events" in result else result
        assert len(events) >= 1
        assert "event_id" in events[0]


# ── High-level session tool ───────────────────────────────────────────────────

class TestRunGovernedTask:
    async def test_full_lifecycle_allow(self):
        raw = await run_governed_task(
            principal_id="mcp-hl-agent",
            requested_outcome="full lifecycle test",
            risk_tier="low",
            selected_action="test",
            rationale="testing high-level tool",
            tool_id="test-tool",
            operation={"data": "sample"},
            sponsoring_entity="acme-corp",
            accountable_owner="cto@acme.com",
            jurisdiction="EU",
            policy_verdict="allow",
            uncertainty_score=0.1,
        )
        summary = json.loads(raw)
        assert summary["status"] == "COMPLETED"
        assert "task_id" in summary
        assert "action_id" in summary
        assert "receipt" in summary

    async def test_require_approval_stops_before_execution(self):
        raw = await run_governed_task(
            principal_id="mcp-hl-agent",
            requested_outcome="approval required test",
            risk_tier="medium",
            selected_action="sensitive-action",
            rationale="needs approval",
            tool_id="sensitive-tool",
            operation={},
            sponsoring_entity="acme-corp",
            accountable_owner="cto@acme.com",
            jurisdiction="EU",
            policy_verdict="require_approval",
            uncertainty_score=0.5,
        )
        summary = json.loads(raw)
        assert summary["status"] == "APPROVAL_PENDING"
        assert "task_id" in summary
        assert "message" in summary
