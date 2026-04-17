"""
§5-§8 Registry Artifacts — AGP Conformance Tests

Covers: liability bindings, capability tokens, delegations, skills,
        revocations, policy sets.
"""
import pytest


class TestLiabilityBindings:
    """§5 Liability Bindings"""

    def test_create_binding_advances_task_to_bound(self, c):
        """§5.1 — Creating a LiabilityBinding auto-advances CREATED task to BOUND."""
        task = c.create_task()
        assert task["status"] == "CREATED"
        c.bind_liability(task["task_id"])
        updated = c.get(f"/agp/tasks/{task['task_id']}").json()
        assert updated["status"] == "BOUND"

    def test_create_binding_sets_liability_binding_ref(self, c):
        """§5.1 — Task gets liability_binding_ref after binding."""
        task = c.create_task()
        binding = c.bind_liability(task["task_id"])
        updated = c.get(f"/agp/tasks/{task['task_id']}").json()
        assert updated.get("liability_binding_ref") == binding["binding_id"]

    @pytest.mark.parametrize("missing", ["task_id", "sponsoring_entity", "accountable_owner",
                                          "jurisdiction", "risk_tier", "created_at"])
    def test_binding_missing_required_field(self, c, missing):
        """§5.1 — Missing required field rejected with 400."""
        task = c.create_task()
        body = {
            "task_id": task["task_id"],
            "sponsoring_entity": "entity",
            "accountable_owner": "owner@example.com",
            "jurisdiction": "EU",
            "risk_tier": "low",
            "created_at": c.now(),
        }
        del body[missing]
        r = c.post("/agp/liability-bindings", body)
        assert r.status_code == 400

    def test_binding_nonexistent_task_rejected(self, c):
        """§5.1 — Binding referencing unknown task_id returns 400."""
        r = c.post("/agp/liability-bindings", {
            "task_id": "tsk_doesnotexist",
            "sponsoring_entity": "x", "accountable_owner": "y",
            "jurisdiction": "EU", "risk_tier": "low", "created_at": c.now(),
        })
        assert r.status_code == 400

    def test_get_binding(self, c):
        """§5.1 — LiabilityBinding is retrievable by ID."""
        task = c.create_task()
        binding = c.bind_liability(task["task_id"])
        r = c.get(f"/agp/liability-bindings/{binding['binding_id']}")
        assert r.status_code == 200
        assert r.json()["binding_id"] == binding["binding_id"]


class TestCapabilityTokens:
    """§6 Capability Tokens"""

    def test_issue_token(self, c):
        """§6.1 — Capability token is issued and retrievable."""
        task = c.create_task()
        token = c.issue_capability(task["task_id"])
        assert token["capability_id"].startswith("cap_")
        assert token["type"] == "CapabilityToken"

    @pytest.mark.parametrize("missing", ["subject_agent", "issuer", "principal_id",
                                          "permitted_actions", "constraints",
                                          "expires_at", "revocation_id"])
    def test_token_missing_required_field(self, c, missing):
        """§6.1 — Missing required field rejected with 400."""
        body = {
            "subject_agent": "agent-001", "issuer": "issuer-001",
            "principal_id": "principal-001",
            "permitted_actions": ["test"], "constraints": {},
            "expires_at": c.future(), "revocation_id": "rev-001",
        }
        del body[missing]
        r = c.post("/agp/capabilities", body)
        assert r.status_code == 400

    def test_get_token_not_found(self, c):
        """§6.1 — Unknown capability_id returns 404."""
        r = c.get("/agp/capabilities/cap_doesnotexist")
        assert r.status_code == 404


class TestDelegations:
    """§7 Delegation Chains"""

    def test_create_delegation(self, c):
        """§7.1 — Delegation chain is created and retrievable."""
        body = {
            "root_principal": "principal-root",
            "delegator_agent": "agent-a",
            "delegate_agent": "agent-b",
            "authority_scope": ["read", "analyse"],
            "constraints": {"max_hops_remaining": 2},
            "accepted_at": c.now(),
            "expires_at": c.future(),
            "signature_chain": ["sig-001"],
        }
        r = c.post("/agp/delegations", body)
        assert r.status_code == 201
        assert r.json()["delegation_id"].startswith("del_")

    def test_delegation_with_valid_parent(self, c):
        """§7.2 — Child delegation referencing a parent with hops remaining is accepted."""
        parent_body = {
            "root_principal": "principal-root",
            "delegator_agent": "agent-a", "delegate_agent": "agent-b",
            "authority_scope": ["read"], "constraints": {"max_hops_remaining": 2},
            "accepted_at": c.now(), "expires_at": c.future(),
            "signature_chain": ["sig-001"],
        }
        parent = c.post("/agp/delegations", parent_body).json()
        child_body = {
            "root_principal": "principal-root",
            "delegator_agent": "agent-b", "delegate_agent": "agent-c",
            "authority_scope": ["read"], "constraints": {"max_hops_remaining": 1},
            "accepted_at": c.now(), "expires_at": c.future(),
            "signature_chain": ["sig-001", "sig-002"],
            "parent_delegation_id": parent["delegation_id"],
        }
        r = c.post("/agp/delegations", child_body)
        assert r.status_code == 201

    def test_delegation_parent_exhausted_hops(self, c):
        """§7.2 — Child delegation rejected when parent has no remaining hops."""
        parent_body = {
            "root_principal": "principal-root",
            "delegator_agent": "agent-a", "delegate_agent": "agent-b",
            "authority_scope": ["read"], "constraints": {"max_hops_remaining": 0},
            "accepted_at": c.now(), "expires_at": c.future(),
            "signature_chain": ["sig-001"],
        }
        parent = c.post("/agp/delegations", parent_body).json()
        child_body = {
            "root_principal": "principal-root",
            "delegator_agent": "agent-b", "delegate_agent": "agent-c",
            "authority_scope": ["read"], "constraints": {"max_hops_remaining": 0},
            "accepted_at": c.now(), "expires_at": c.future(),
            "signature_chain": ["sig-001", "sig-002"],
            "parent_delegation_id": parent["delegation_id"],
        }
        r = c.post("/agp/delegations", child_body)
        assert r.status_code == 409

    def test_delegation_nonexistent_parent_rejected(self, c):
        """§7.2 — Referencing non-existent parent delegation returns 400."""
        r = c.post("/agp/delegations", {
            "root_principal": "x", "delegator_agent": "a", "delegate_agent": "b",
            "authority_scope": ["read"], "constraints": {}, "accepted_at": c.now(),
            "expires_at": c.future(), "signature_chain": [], "parent_delegation_id": "del_doesnotexist",
        })
        assert r.status_code == 400


class TestSkills:
    """§8 Skill Manifests"""

    def test_register_skill(self, c):
        """§8.1 — Skill manifest is registered and retrievable."""
        body = {
            "name": f"test-skill-{c.uid()}",
            "version": "1.0.0",
            "publisher": "conformance-suite",
            "supported_protocols": ["agp/0.5"],
            "skill_class": "analysis",
            "risk_class": "low",
            "instruction_hash": f"sha256:{c.uid()}",
            "attestation_level": "self_attested",
            "created_at": c.now(),
        }
        r = c.post("/agp/skills", body)
        assert r.status_code == 201
        assert r.json()["skill_id"].startswith("skl_")

    def test_list_skills_filter_by_publisher(self, c):
        """§8.1 — Skills list supports publisher filter."""
        uid = c.uid()
        c.post("/agp/skills", {
            "name": "filtered-skill", "version": "1.0.0",
            "publisher": f"pub-{uid}",
            "supported_protocols": ["agp/0.5"], "skill_class": "analysis",
            "risk_class": "low", "instruction_hash": f"sha256:{uid}",
            "attestation_level": "self_attested", "created_at": c.now(),
        })
        r = c.get("/agp/skills", publisher=f"pub-{uid}")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        assert all(s["publisher"] == f"pub-{uid}" for s in items)


class TestPolicySets:
    """§9 v0.6 Policy Sets"""

    def test_register_policy_set(self, c):
        """§9.1 — PolicySet is registered with active status."""
        ps = c.create_policy_set()
        assert ps["policy_set_id"].startswith("pset_")
        assert ps["status"] == "active"
        assert ps["type"] == "PolicySet"

    def test_policy_set_lifecycle_active_to_deprecated(self, c):
        """§9.2 — active → deprecated transition accepted."""
        ps = c.create_policy_set()
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "deprecated"})
        assert r.status_code == 200
        assert r.json()["status"] == "deprecated"

    def test_policy_set_lifecycle_deprecated_to_revoked(self, c):
        """§9.2 — deprecated → revoked transition accepted."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "deprecated"})
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "revoked"})
        assert r.status_code == 200
        assert r.json()["status"] == "revoked"

    def test_policy_set_lifecycle_active_to_revoked(self, c):
        """§9.2 — active → revoked is a valid shortcut."""
        ps = c.create_policy_set()
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "revoked"})
        assert r.status_code == 200

    def test_policy_set_revoked_cannot_be_reactivated(self, c):
        """§9.2 — revoked → active is forbidden (one-way lifecycle)."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "revoked"})
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "active"})
        assert r.status_code in (409, 422)

    def test_policy_set_deprecated_cannot_be_reactivated(self, c):
        """§9.2 — deprecated → active is forbidden."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "deprecated"})
        r = c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "active"})
        assert r.status_code in (409, 422)

    def test_verified_attestation_requires_certifying_body(self, c):
        """§9.1 — verified attestation_level requires certifying_body."""
        r = c.post("/agp/policy-sets", {
            "name": "verified-test", "version": "1.0.0", "publisher": "test",
            "regulatory_frameworks": ["EU_AI_ACT_2024"], "jurisdictions": ["EU"],
            "ruleset_hash": f"sha256:{c.uid()}", "ruleset_engine": "opa",
            "attestation_level": "verified",
            "effective_from": c.now(), "created_at": c.now(),
        })
        assert r.status_code == 400

    def test_verified_attestation_with_certifying_body_accepted(self, c):
        """§9.1 — verified attestation with certifying_body is accepted."""
        r = c.post("/agp/policy-sets", {
            "name": "verified-ok", "version": "1.0.0", "publisher": "test",
            "regulatory_frameworks": ["EU_AI_ACT_2024"], "jurisdictions": ["EU"],
            "ruleset_hash": f"sha256:{c.uid()}", "ruleset_engine": "opa",
            "attestation_level": "verified",
            "certifying_body": "accredited-lab-001",
            "effective_from": c.now(), "created_at": c.now(),
        })
        assert r.status_code == 201

    def test_invalid_ruleset_engine_rejected(self, c):
        """§9.1 — Unknown ruleset_engine is rejected."""
        r = c.post("/agp/policy-sets", {
            "name": "bad-engine", "version": "1.0.0", "publisher": "test",
            "regulatory_frameworks": ["EU_AI_ACT_2024"], "jurisdictions": ["EU"],
            "ruleset_hash": f"sha256:{c.uid()}", "ruleset_engine": "unknown_engine",
            "attestation_level": "self_attested",
            "effective_from": c.now(), "created_at": c.now(),
        })
        assert r.status_code == 400

    def test_list_policy_sets_filter_by_framework(self, c):
        """§9.3 — regulatory_framework filter returns only matching sets."""
        c.create_policy_set(regulatory_frameworks=["NIST_AI_RMF_1_0"], jurisdictions=["US"])
        ps_eu = c.create_policy_set(regulatory_frameworks=["EU_AI_ACT_2024"])
        uid = ps_eu["policy_set_id"]
        r = c.get("/agp/policy-sets", regulatory_framework="NIST_AI_RMF_1_0")
        assert r.status_code == 200
        items = r.json()["items"]
        assert all("NIST_AI_RMF_1_0" in p["regulatory_frameworks"] for p in items)

    def test_list_policy_sets_filter_by_status(self, c):
        """§9.3 — status filter returns only PolicySets in that state."""
        ps = c.create_policy_set()
        c.patch(f"/agp/policy-sets/{ps['policy_set_id']}", {"status": "deprecated"})
        r = c.get("/agp/policy-sets", status="deprecated")
        items = r.json()["items"]
        assert any(p["policy_set_id"] == ps["policy_set_id"] for p in items)
        assert all(p["status"] == "deprecated" for p in items)


class TestRevocations:
    """§6.3 Revocations"""

    def test_create_revocation(self, c):
        """§6.3 — RevocationNotice is created and retrievable."""
        token = c.issue_capability(c.create_task()["task_id"])
        r = c.post("/agp/revocations", {
            "issuer": "principal-001",
            "target_type": "CapabilityToken",
            "target_id": token["capability_id"],
            "reason": "capability no longer needed",
            "effective_at": c.now(),
        })
        assert r.status_code == 201
        assert r.json()["revocation_id"].startswith("rev_")

    @pytest.mark.parametrize("missing", ["issuer", "target_type", "target_id", "reason", "effective_at"])
    def test_revocation_missing_required_field(self, c, missing):
        """§6.3 — Missing required field returns 400."""
        body = {
            "issuer": "principal-001", "target_type": "CapabilityToken",
            "target_id": "cap_test", "reason": "test", "effective_at": c.now(),
        }
        del body[missing]
        r = c.post("/agp/revocations", body)
        assert r.status_code == 400
