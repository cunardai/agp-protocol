"""
SDK integration tests — run against a live AGP server.

Usage:
    pytest tests/ --base-url http://localhost:8099
"""
import pytest

from agp import AGPClient, AGPNotFoundError, AGPPolicyDeniedError


class TestTaskSession:
    def test_full_low_risk_lifecycle(self, client):
        """Happy path: low-risk task through full lifecycle."""
        with client.task_session(
            principal_id="sdk-agent-001",
            requested_outcome="analyse sentiment",
            risk_tier="low",
        ) as session:
            assert session.task.status == "CREATED"

            cap = client.registry.issue_capability(
                subject_agent="sdk-agent-001",
                issuer="sdk-principal",
                principal_id="sdk-principal",
                permitted_actions=["analyse"],
            )
            session.with_capability(cap)

            session.bind(
                sponsoring_entity="acme-corp",
                accountable_owner="cto@acme.com",
                jurisdiction="EU",
            )
            assert session.task.status == "BOUND"

            session.decide(
                agent_id="sdk-agent-001",
                selected_action="analyse",
                rationale="No PII, standard NLP",
                uncertainty_score=0.05,
            )
            assert session.decision_record is not None

            session.evaluate(verdict="allow")
            assert session.policy_decision is not None
            assert session.policy_decision.verdict == "allow"

            result = session.execute(
                agent_id="sdk-agent-001",
                tool_id="nlp-tool",
                operation={"text": "analyse this feedback"},
            )
            assert result is not None
            session.refresh()
            assert session.task.status == "COMPLETED"

    def test_task_session_with_v06_fields(self, client):
        """Task session accepts jurisdictions and regulatory_frameworks."""
        with client.task_session(
            principal_id="sdk-agent-eu",
            requested_outcome="EU-governed analysis",
            risk_tier="medium",
            jurisdictions=["EU"],
            regulatory_frameworks=["EU_AI_ACT_2024"],
        ) as session:
            assert "EU" in session.task.jurisdictions
            assert "EU_AI_ACT_2024" in session.task.regulatory_frameworks

    def test_resume_session(self, client):
        """resume_session() picks up an existing task."""
        original = client.task_session(
            principal_id="sdk-agent-resume",
            requested_outcome="test resume",
            risk_tier="low",
        )
        task_id = original.task_id

        resumed = client.resume_session(task_id)
        assert resumed.task_id == task_id
        assert resumed.task.status == "CREATED"

    def test_not_found_error(self, client):
        """AGPNotFoundError raised for unknown task."""
        with pytest.raises(AGPNotFoundError):
            client.registry.get_task("tsk_doesnotexist")

    def test_policy_set_lifecycle(self, client):
        """PolicySet registration and status transitions via SDK."""
        ps = client.registry.register_policy_set(
            name="SDK Test PolicySet",
            version="1.0.0",
            publisher="sdk-test",
            regulatory_frameworks=["EU_AI_ACT_2024"],
            jurisdictions=["EU"],
            ruleset_hash="sha256:sdktest",
            ruleset_engine="opa",
        )
        assert ps.status == "active"

        deprecated = client.registry.update_policy_set_status(
            ps.policy_set_id, "deprecated"
        )
        assert deprecated.status == "deprecated"

        revoked = client.registry.update_policy_set_status(
            ps.policy_set_id, "revoked"
        )
        assert revoked.status == "revoked"

    def test_session_fails_task_on_exception(self, client):
        """Context manager marks task FAILED on unhandled exception."""
        task_id = None
        try:
            with client.task_session(
                principal_id="sdk-agent-fail",
                requested_outcome="test failure handling",
                risk_tier="low",
            ) as session:
                task_id = session.task_id
                raise ValueError("simulated agent error")
        except ValueError:
            pass

        if task_id:
            task = client.registry.get_task(task_id)
            assert task.status == "FAILED"

    def test_validate_envelope(self, client):
        """validate_envelope() returns True without mutating state."""
        with client.task_session(
            principal_id="sdk-agent-validate",
            requested_outcome="test validate-only",
            risk_tier="low",
        ) as session:
            cap = client.registry.issue_capability(
                subject_agent="sdk-agent-validate",
                issuer="sdk-principal",
                principal_id="sdk-principal",
                permitted_actions=["test"],
            )
            session.with_capability(cap)
            session.bind(sponsoring_entity="x", accountable_owner="y@x.com",
                         jurisdiction="EU")
            session.decide(agent_id="sdk-agent-validate", selected_action="test",
                           rationale="test", uncertainty_score=0.1)
            session.evaluate(verdict="allow")

            # Advance to EXECUTING manually so validate-only works
            client.registry.transition_task(session.task_id, "EXECUTING")

            valid = client.execution.validate_envelope(
                task_id=session.task_id,
                agent_id="sdk-agent-validate",
                tool_id="test-tool",
                operation={},
                capability_token_ref=cap.capability_id,
                decision_ref=session.decision_record.decision_id,
                policy_decision_ref=session.policy_decision.policy_evaluation_id,
            )
            assert valid is True

    def test_audit_replay(self, client):
        """replay() returns ordered ledger events after execution."""
        with client.task_session(
            principal_id="sdk-agent-replay",
            requested_outcome="test replay",
            risk_tier="low",
        ) as session:
            cap = client.registry.issue_capability(
                subject_agent="sdk-agent-replay",
                issuer="sdk-principal",
                principal_id="sdk-principal",
                permitted_actions=["test"],
            )
            session.with_capability(cap)
            session.bind(sponsoring_entity="x", accountable_owner="y@x.com",
                         jurisdiction="EU")
            session.decide(agent_id="sdk-agent-replay", selected_action="test",
                           rationale="test", uncertainty_score=0.1)
            session.evaluate(verdict="allow")
            session.execute(agent_id="sdk-agent-replay", tool_id="test-tool",
                            operation={})

            events = session.replay()
            assert len(events) >= 1
