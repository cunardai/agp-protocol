"""
AGP SDK — AGPClient

Top-level entry point. Composes RegistryClient, DecisionClient,
ExecutionClient, and TaskSession into a single object.

Usage:
    from agp import AGPClient

    client = AGPClient("http://localhost:8099")

    # High-level session API
    with client.task_session(
        principal_id="my-agent",
        requested_outcome="analyse sentiment",
        risk_tier="low",
    ) as session:
        session.bind(sponsoring_entity="acme", accountable_owner="cto@acme.com",
                     jurisdiction="EU")
        session.decide(agent_id="my-agent", selected_action="analyse",
                       rationale="safe", uncertainty_score=0.05)
        session.evaluate(verdict="allow")
        receipt = session.execute(agent_id="my-agent", tool_id="nlp",
                                  operation={}, capability_token_ref="cap_xxx")

    # Low-level direct API
    task = client.registry.create_task(...)
    decision = client.decision.create_decision(...)
"""
from __future__ import annotations

from typing import Any

from .decision import DecisionClient
from .execution import ExecutionClient
from .http import Transport
from .models import RiskTier, Task
from .registry import RegistryClient
from .session import TaskSession


class AGPClient:
    """
    Main AGP client. Thread-safe for concurrent use.

    Args:
        base_url:  URL of the AGP server (e.g. "http://localhost:8099")
        timeout:   HTTP request timeout in seconds (default 30)
        headers:   Additional headers to send with every request
                   (e.g. {"Authorization": "Bearer <token>"})
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self._transport = Transport(
            base_url,
            timeout=timeout,
            headers=headers,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.registry  = RegistryClient(self._transport)
        self.decision  = DecisionClient(self._transport)
        self.execution = ExecutionClient(self._transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "AGPClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── TaskSession factory ────────────────────────────────────────────────

    def task_session(
        self,
        *,
        principal_id: str,
        requested_outcome: str,
        risk_tier: RiskTier,
        expires_at: str | None = None,
        sponsoring_entity: str | None = None,
        governance_requirements: dict[str, Any] | None = None,
        jurisdictions: list[str] | None = None,
        regulatory_frameworks: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> TaskSession:
        """
        Create a new task and return a TaskSession bound to it.

        The session can be used as a context manager — on unhandled exception
        it will attempt to mark the task FAILED.
        """
        task = self.registry.create_task(
            principal_id=principal_id,
            requested_outcome=requested_outcome,
            risk_tier=risk_tier,
            expires_at=expires_at,
            sponsoring_entity=sponsoring_entity,
            governance_requirements=governance_requirements,
            jurisdictions=jurisdictions,
            regulatory_frameworks=regulatory_frameworks,
            idempotency_key=idempotency_key,
        )
        return TaskSession(
            registry=self.registry,
            decision=self.decision,
            execution=self.execution,
            task=task,
        )

    def resume_session(self, task_id: str) -> TaskSession:
        """
        Resume a TaskSession for an existing task (e.g. after a restart
        or when picking up an APPROVAL_PENDING task from a queue).
        """
        task = self.registry.get_task(task_id)
        return TaskSession(
            registry=self.registry,
            decision=self.decision,
            execution=self.execution,
            task=task,
        )
