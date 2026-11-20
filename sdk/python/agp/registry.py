"""
AGP SDK — Registry API client

Wraps: /agp/tasks, /agp/liability-bindings, /agp/capabilities,
       /agp/delegations, /agp/skills, /agp/policy-sets, /agp/revocations
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from .http import Transport, new_idempotency_key
from .models import (
    CapabilityToken, DelegationChain, LiabilityBinding,
    PagedResult, PolicySet, RevocationNotice, RiskTier,
    SkillManifest, Task,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegistryClient:
    def __init__(self, transport: Transport):
        self._t = transport

    # ── Tasks ──────────────────────────────────────────────────────────────

    def create_task(
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
        tool: str | None = None,
        intent: str | None = None,
        arguments: dict[str, Any] | None = None,
        signals: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Task:
        """tool / intent / arguments / signals: what a policy's conditions read (AGP 1.0, Policy Packs) —
        e.g. signals={"bian": {"service_domains": ["Consumer Loan"]}}."""
        body: dict[str, Any] = {
            "principal_id": principal_id,
            "requested_outcome": requested_outcome,
            "risk_tier": risk_tier,
            "created_at": _now(),
        }
        if expires_at:
            body["expires_at"] = expires_at
        if sponsoring_entity:
            body["sponsoring_entity"] = sponsoring_entity
        if governance_requirements:
            body["governance_requirements"] = governance_requirements
        if jurisdictions:
            body["jurisdictions"] = jurisdictions
        if regulatory_frameworks:
            body["regulatory_frameworks"] = regulatory_frameworks
        for k, v in (("tool", tool), ("intent", intent), ("arguments", arguments), ("signals", signals)):
            if v is not None:
                body[k] = v

        raw = self._t.post("/agp/tasks", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return Task.model_validate(raw)

    def get_task(self, task_id: str) -> Task:
        return Task.model_validate(self._t.get(f"/agp/tasks/{task_id}"))

    def list_tasks(
        self,
        *,
        principal_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> PagedResult:
        params: dict[str, Any] = {"limit": limit}
        if principal_id:
            params["principal_id"] = principal_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return PagedResult.model_validate(self._t.get("/agp/tasks", params=params))

    def transition_task(self, task_id: str, status: str,
                        transition_guard_ref: str | None = None) -> Task:
        body: dict[str, Any] = {"status": status}
        if transition_guard_ref:
            body["transition_guard_ref"] = transition_guard_ref
        return Task.model_validate(self._t.patch(f"/agp/tasks/{task_id}", body))

    # ── Liability Bindings ─────────────────────────────────────────────────

    def create_liability_binding(
        self,
        *,
        task_id: str,
        sponsoring_entity: str,
        accountable_owner: str,
        jurisdiction: str,
        risk_tier: RiskTier,
        idempotency_key: str | None = None,
    ) -> LiabilityBinding:
        body = {
            "task_id": task_id,
            "sponsoring_entity": sponsoring_entity,
            "accountable_owner": accountable_owner,
            "jurisdiction": jurisdiction,
            "risk_tier": risk_tier,
            "created_at": _now(),
        }
        raw = self._t.post("/agp/liability-bindings", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return LiabilityBinding.model_validate(raw)

    def get_liability_binding(self, binding_id: str) -> LiabilityBinding:
        return LiabilityBinding.model_validate(
            self._t.get(f"/agp/liability-bindings/{binding_id}")
        )

    # ── Capability Tokens ──────────────────────────────────────────────────

    def issue_capability(
        self,
        *,
        subject_agent: str,
        issuer: str,
        principal_id: str,
        permitted_actions: list[str],
        constraints: dict[str, Any] | None = None,
        expires_in_days: int = 30,
        expires_at: str | None = None,
        revocation_id: str | None = None,
        task_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> CapabilityToken:
        exp = expires_at or (
            datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        ).isoformat()
        rev_id = revocation_id or new_idempotency_key()
        body = {
            "subject_agent": subject_agent,
            "issuer": issuer,
            "principal_id": principal_id,
            "permitted_actions": permitted_actions,
            "constraints": constraints or {},
            "expires_at": exp,
            "revocation_id": rev_id,
            **({"task_id": task_id} if task_id else {}),
        }
        raw = self._t.post("/agp/capabilities", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return CapabilityToken.model_validate(raw)

    def check_capability(
        self,
        capability_id: str,
        *,
        agent_id: str,
        tool_id: str,
        acting_for: str | None = None,
        policy_set_refs: list[str] | str | None = None,
        signals: dict[str, Any] | None = None,
        arguments: dict[str, Any] | None = None,
        risk_tier: str | None = None,
    ) -> dict[str, Any]:
        """May this agent use this tool under this capability, now? — for tool calls outside a task (AGP 1.0, §6).
        policy_set_refs ("installed" = every pack installed in the org) judges the call by Policy Packs too;
        acting_for names the principal behind it (checked too). A DENY is returned, not raised: read
        ["enforcement_decision"], ["failed_check"], ["reason"] and, from a pack, ["source_refs"]."""
        body: dict[str, Any] = {"agent_id": agent_id, "tool_id": tool_id}
        for k, v in (("acting_for", acting_for), ("policy_set_refs", policy_set_refs), ("signals", signals),
                     ("arguments", arguments), ("risk_tier", risk_tier)):
            if v is not None:
                body[k] = v
        return self._t.post(f"/agp/capabilities/{capability_id}/check", body, allow_status=(403,))

    def get_capability(self, capability_id: str) -> CapabilityToken:
        return CapabilityToken.model_validate(
            self._t.get(f"/agp/capabilities/{capability_id}")
        )

    # ── Delegations ────────────────────────────────────────────────────────

    def create_delegation(
        self,
        *,
        root_principal: str,
        delegator_agent: str,
        delegate_agent: str,
        authority_scope: list[str],
        constraints: dict[str, Any] | None = None,
        expires_in_days: int = 30,
        expires_at: str | None = None,
        signature_chain: list[str] | None = None,
        parent_delegation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DelegationChain:
        exp = expires_at or (
            datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        ).isoformat()
        body: dict[str, Any] = {
            "root_principal": root_principal,
            "delegator_agent": delegator_agent,
            "delegate_agent": delegate_agent,
            "authority_scope": authority_scope,
            "constraints": constraints or {},
            "accepted_at": _now(),
            "expires_at": exp,
            "signature_chain": signature_chain or [],
        }
        if parent_delegation_id:
            body["parent_delegation_id"] = parent_delegation_id
        raw = self._t.post("/agp/delegations", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return DelegationChain.model_validate(raw)

    # ── Skills ─────────────────────────────────────────────────────────────

    def register_skill(
        self,
        *,
        name: str,
        version: str,
        publisher: str,
        supported_protocols: list[str],
        skill_class: str,
        risk_class: str,
        instruction_hash: str,
        attestation_level: str = "self_attested",
        idempotency_key: str | None = None,
    ) -> SkillManifest:
        body = {
            "name": name, "version": version, "publisher": publisher,
            "supported_protocols": supported_protocols,
            "skill_class": skill_class, "risk_class": risk_class,
            "instruction_hash": instruction_hash,
            "attestation_level": attestation_level,
            "created_at": _now(),
        }
        raw = self._t.post("/agp/skills", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return SkillManifest.model_validate(raw)

    def list_skills(
        self,
        *,
        publisher: str | None = None,
        attestation_level: str | None = None,
        risk_class: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> PagedResult:
        params: dict[str, Any] = {"limit": limit}
        if publisher:
            params["publisher"] = publisher
        if attestation_level:
            params["attestation_level"] = attestation_level
        if risk_class:
            params["risk_class"] = risk_class
        if cursor:
            params["cursor"] = cursor
        return PagedResult.model_validate(self._t.get("/agp/skills", params=params))

    # ── Policy Sets ────────────────────────────────────────────────────────

    def register_policy_set(
        self,
        *,
        name: str,
        version: str,
        publisher: str,
        regulatory_frameworks: list[str],
        jurisdictions: list[str],
        ruleset_hash: str,
        ruleset_engine: str = "opa",
        attestation_level: str = "self_attested",
        effective_from: str | None = None,
        certifying_body: str | None = None,
        supersedes: str | None = None,
        idempotency_key: str | None = None,
    ) -> PolicySet:
        body: dict[str, Any] = {
            "name": name, "version": version, "publisher": publisher,
            "regulatory_frameworks": regulatory_frameworks,
            "jurisdictions": jurisdictions,
            "ruleset_hash": ruleset_hash,
            "ruleset_engine": ruleset_engine,
            "attestation_level": attestation_level,
            "effective_from": effective_from or _now(),
            "created_at": _now(),
        }
        if certifying_body:
            body["certifying_body"] = certifying_body
        if supersedes:
            body["supersedes"] = supersedes
        raw = self._t.post("/agp/policy-sets", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return PolicySet.model_validate(raw)

    def get_policy_set(self, policy_set_id: str) -> PolicySet:
        return PolicySet.model_validate(
            self._t.get(f"/agp/policy-sets/{policy_set_id}")
        )

    def list_policy_sets(
        self,
        *,
        regulatory_framework: str | None = None,
        jurisdiction: str | None = None,
        status: str | None = None,
        attestation_level: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> PagedResult:
        params: dict[str, Any] = {"limit": limit}
        if regulatory_framework:
            params["regulatory_framework"] = regulatory_framework
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if status:
            params["status"] = status
        if attestation_level:
            params["attestation_level"] = attestation_level
        if cursor:
            params["cursor"] = cursor
        return PagedResult.model_validate(
            self._t.get("/agp/policy-sets", params=params)
        )

    def update_policy_set_status(self, policy_set_id: str, status: str) -> PolicySet:
        return PolicySet.model_validate(
            self._t.patch(f"/agp/policy-sets/{policy_set_id}", {"status": status})
        )

    # ── Revocations ────────────────────────────────────────────────────────

    def revoke(
        self,
        *,
        issuer: str,
        target_type: str,
        target_id: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> RevocationNotice:
        body = {
            "issuer": issuer,
            "target_type": target_type,
            "target_id": target_id,
            "reason": reason,
            "effective_at": _now(),
        }
        raw = self._t.post("/agp/revocations", body,
                           idempotency_key=idempotency_key or new_idempotency_key())
        return RevocationNotice.model_validate(raw)
