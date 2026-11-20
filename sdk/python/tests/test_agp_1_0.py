"""
AGP Python SDK — AGP 1.0, against a live reference server with auth on (spec/studio-extensions.md).

    AGP_AUTH_BASE_URL=http://localhost:8098 AGP_PROVISIONER_ID=… AGP_PROVISIONER_SECRET=… \\
    AGP_OPERATOR_ID=… AGP_OPERATOR_SECRET=… pytest tests/test_agp_1_0.py

Each run provisions a fresh org. The server computes every verdict (no AGP_CALLER_VERDICTS).
"""
from __future__ import annotations

import hashlib
import os
import uuid

import pytest

from agp import AGPClient, AGPConflictError, AGPForbiddenError, AGPNotFoundError, AGPUnauthorizedError

URL = os.environ.get("AGP_AUTH_BASE_URL")
PROV = (os.environ.get("AGP_PROVISIONER_ID"), os.environ.get("AGP_PROVISIONER_SECRET"))
OP = (os.environ.get("AGP_OPERATOR_ID"), os.environ.get("AGP_OPERATOR_SECRET"))
pytestmark = pytest.mark.skipif(not (URL and all(PROV)), reason="AGP_AUTH_BASE_URL / AGP_PROVISIONER_ID / _SECRET not set")
ALL = ["agp.registry.read", "agp.registry.write", "agp.decision.read", "agp.decision.write", "agp.execution.read",
       "agp.execution.write", "agp.approval.write", "agp.policy.write", "agp.revocation.write", "agp.principal.admin", "agp.content.read"]


def H(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


@pytest.fixture(scope="module")
def c():
    prov = AGPClient(URL, client_id=PROV[0], client_secret=PROV[1])
    org = f"pysdk-{uuid.uuid4().hex[:8]}"
    made = prov.admin.provision_org_client(org, client_id=f"sdk-{org}", scopes=ALL)
    with pytest.raises(AGPConflictError):                                   # an org's first client, once
        prov.admin.provision_org_client(org, client_id=f"x-{org}", scopes=["agp.execution.write"])
    client = AGPClient(URL, client_id=made["client_id"], client_secret=made["client_secret"])
    for p in ("ann", "bo", "cy"):
        client.principals.register(principal_id=f"user:{p}", kind="user")
    client.principals.register(principal_id="assistant:ann", kind="assistant", acting_for="user:ann")
    yield client
    client.close()


def test_without_credentials_refused():
    with pytest.raises(AGPUnauthorizedError):
        AGPClient(URL).registry.list_tasks()


def test_the_ledger_principals_and_kept_content(c):
    r = c.ledger.report([{"event_kind": "http.request", "principal_id": "user:ann", "action_class": "read", "outcome": "executed",
                          "action": "GET /customers?email=ann@bank.com", "client_event_id": "e-1"}])
    assert r["recorded"] == 1
    assert c.ledger.report([{"event_kind": "http.request", "principal_id": "user:ann", "action_class": "read", "outcome": "executed",
                             "client_event_id": "e-1"}])["duplicates"] == 1
    items = c.ledger.events(limit=50, order="desc")["items"]
    assert "ann@bank.com" not in str(items)                                  # masked as read
    with pytest.raises(AGPForbiddenError):
        c.ledger.events(raw=True)
    assert c.ledger.verify()["ok"] is True
    pack, name = c.ledger.evidence_pack()
    assert pack[:2] == b"PK" and name and name.startswith("agp-evidence-")
    assert c.principals.get("assistant:ann")["acting_for"] == "user:ann"
    stored = c.content.store([{"kind": "prompt", "data": "hello"}])["stored"][0]
    assert c.content.get(stored["content_id"])["data"] == "hello"


def test_approvals_bound_to_people(c):
    params = H(uuid.uuid4().hex)
    req = c.approvals.request(action="variant.delete", params_hash=params, requested_by="user:ann", mode="dual")
    with pytest.raises(AGPForbiddenError):
        c.approvals.decide(req["request_id"], approver="user:ann", decision="approved")
    assert c.approvals.decide(req["request_id"], approver="user:bo", decision="approved")["status"] == "pending"
    done = c.approvals.decide(req["request_id"], approver="user:cy", decision="approved")
    assert done["status"] == "approved" and sorted(done["artifact"]["approver_ids"]) == ["user:bo", "user:cy"]
    assert c.approvals.redeem(action="variant.delete", params_hash=params, requested_for="user:ann")["approval_id"] == done["artifact"]["approval_id"]
    with pytest.raises(AGPNotFoundError):
        c.approvals.redeem(action="variant.delete", params_hash=params, requested_for="user:ann")


def test_packs_and_a_cited_server_verdict(c):
    pack_id = f"pysdk/{uuid.uuid4().hex[:8]}"
    c.packs.publish({"apiVersion": "agp/v1", "kind": "PolicyPack",
                     "metadata": {"pack_id": pack_id, "name": "Py pack", "version": "1.0.0", "publisher": "sdk"},
                     "spec": {"policy_sets": [{"name": "py", "version": "1.0.0", "publisher": "sdk", "regulatory_frameworks": [],
                                               "jurisdictions": [], "default_verdict": "allow", "rules": [
                         {"id": "refuse", "verdict": "deny", "rationale": "refused", "source_refs": [{"provision": "Art. 9(1)"}],
                          "condition": {"field": "signals.bian.service_domains", "op": "in", "value": ["Consumer Loan"]}}]}]}})
    [pset] = c.packs.install(pack_id)["policy_set_ids"]
    task = c.registry.create_task(principal_id="user:ann", requested_outcome="change a loan", risk_tier="low",
                                  signals={"bian": {"service_domains": ["Consumer Loan"]}})
    dec = c.decision.create_decision(task_id=task.task_id, agent_id="assistant:ann", selected_action="execute", rationale="r", uncertainty_score=0)
    pol = c.decision.evaluate_policy(task_id=task.task_id, decision_ref=dec.decision_id, policy_set_refs=[pset])
    extra = pol.model_extra or {}
    assert pol.verdict == "deny" and extra["source_refs"][0]["provision"] == "Art. 9(1)"
    # The same pack judging a tool call outside a task, for the person behind it.
    cap = c.registry.issue_capability(subject_agent="assistant:ann", issuer="sdk", principal_id="user:ann", permitted_actions=["*"])
    chk = c.registry.check_capability(cap.capability_id, agent_id="assistant:ann", tool_id="update_loan", acting_for="user:ann",
                                      policy_set_refs="installed", signals={"bian": {"service_domains": ["Consumer Loan"]}})
    assert chk["enforcement_decision"] == "DENY" and chk["failed_check"] == "policy" and "Art. 9(1)" in chk["reason"]
    assert c.packs.uninstall(pack_id)["uninstalled"] is True
    assert c.registry.check_capability(cap.capability_id, agent_id="assistant:ann", tool_id="update_loan",
                                       policy_set_refs="installed")["enforcement_decision"] == "PERMIT"


def test_detectors_and_the_orgs_status(c):
    assert c.detectors.settings()["detectors"]["integrity"]["mode"] == "enforce"
    assert c.detectors.org_status()["status"] == "active"
    assert c.detectors.blocked()["org_status"] == "active"
    assert isinstance(c.detectors.signals()["items"], list)
    assert c.detectors.propose_settings({"velocity": {"mode": "enforce"}}, "user:ann")["mode"] == "dual"


@pytest.mark.skipif(not all(OP), reason="AGP_OPERATOR_ID / _SECRET not set")
def test_the_hub_operator_sees_read_only_orgs_and_nothing_else(c):
    op = AGPClient(URL, client_id=OP[0], client_secret=OP[1])
    assert isinstance(op.operator.read_only_orgs()["items"], list)
    with pytest.raises(AGPForbiddenError):
        op.ledger.events()
    with pytest.raises(AGPForbiddenError):
        c.operator.read_only_orgs()
