/**
 * AGP TypeScript SDK — AGP 1.0, against a live reference server with auth on (spec/studio-extensions.md).
 *
 *   AGP_AUTH_BASE_URL=http://localhost:8098 AGP_PROVISIONER_ID=… AGP_PROVISIONER_SECRET=… \
 *   AGP_OPERATOR_ID=… AGP_OPERATOR_SECRET=… npm test
 *
 * Each run provisions a fresh org. The server computes every verdict (no AGP_CALLER_VERDICTS).
 */
import { createHash, randomUUID } from "node:crypto";
import { describe, it, expect, beforeAll } from "vitest";
import { AGPClient, AGPForbiddenError, AGPNotFoundError } from "../src/index.js";

const URL_ = process.env["AGP_AUTH_BASE_URL"];
const PROV_ID = process.env["AGP_PROVISIONER_ID"];
const PROV_SECRET = process.env["AGP_PROVISIONER_SECRET"];
const OP_ID = process.env["AGP_OPERATOR_ID"];
const OP_SECRET = process.env["AGP_OPERATOR_SECRET"];
const live = !!(URL_ && PROV_ID && PROV_SECRET);
const ALL = ["agp.registry.read", "agp.registry.write", "agp.decision.read", "agp.decision.write", "agp.execution.read",
             "agp.execution.write", "agp.approval.write", "agp.policy.write", "agp.revocation.write", "agp.principal.admin", "agp.content.read"];
const H = (s: string) => "sha256:" + createHash("sha256").update(s).digest("hex");
const now = () => new Date().toISOString();

let c: AGPClient;
const people: string[] = [];

describe.skipIf(!live)("AGP 1.0", () => {
  beforeAll(async () => {
    const prov = new AGPClient(URL_!, { client_id: PROV_ID!, client_secret: PROV_SECRET! });
    const org = `sdk10-${randomUUID().slice(0, 8)}`;
    const made = await prov.admin.provisionOrgClient(org, { client_id: `sdk-${org}`, scopes: ALL });
    c = new AGPClient(URL_!, { client_id: made.client_id, client_secret: made.client_secret });
    for (const p of ["ann", "bo", "cy"]) {
      await c.principals.register({ principal_id: `user:${p}`, kind: "user" });
      people.push(`user:${p}`);
    }
    await c.principals.register({ principal_id: "assistant:ann", kind: "assistant", acting_for: "user:ann" });
  });

  it("approvals bound to people: nobody approves their own; dual takes two others; used once", async () => {
    const params = H(randomUUID());
    const req = await c.approvals.request({ action: "variant.delete", params_hash: params, requested_by: "user:ann", mode: "dual" });
    expect(req.mode).toBe("dual");
    await expect(c.approvals.decide(req.request_id, { approver: "user:ann", decision: "approved" })).rejects.toBeInstanceOf(AGPForbiddenError);
    expect((await c.approvals.decide(req.request_id, { approver: "user:bo", decision: "approved" })).status).toBe("pending");
    const done = await c.approvals.decide(req.request_id, { approver: "user:cy", decision: "approved" });
    expect(done.status).toBe("approved");
    expect(done.artifact?.approver_ids.sort()).toEqual(["user:bo", "user:cy"]);
    const redeem = { action: "variant.delete", params_hash: params, requested_for: "user:ann" };
    expect((await c.approvals.redeem(redeem)).approval_id).toBe(done.artifact?.approval_id);
    await expect(c.approvals.redeem(redeem)).rejects.toBeInstanceOf(AGPNotFoundError);
    expect((await c.approvals.twoPersonActions()).fixed).toContain("org.reinstate");
  });

  it("packs: publish, install, a server verdict citing its provision across several sets, uninstall", async () => {
    const pack_id = `sdk/${randomUUID().slice(0, 8)}`;
    await c.packs.publish({ apiVersion: "agp/v1", kind: "PolicyPack",
      metadata: { pack_id, name: "SDK pack", version: "1.0.0", publisher: "sdk" },
      spec: { policy_sets: [{ name: "sdk", version: "1.0.0", publisher: "sdk", regulatory_frameworks: [], jurisdictions: [], default_verdict: "allow",
        rules: [{ id: "hold", verdict: "require_approval", source_refs: [{ provision: "Art. 9(2)" }],
                  condition: { field: "signals.bian.service_domains", op: "in", value: ["Consumer Loan"] } }] }] } });
    const inst = await c.packs.install(pack_id);
    expect(inst.policy_set_ids).toHaveLength(1);
    expect((await c.packs.list()).items.find(p => p.pack_id === pack_id)?.installed?.version).toBe("1.0.0");
    const [official] = (await c.packs.install("agp/finance")).policy_set_ids;

    const task = await c.registry.createTask({ principal_id: "user:ann", requested_outcome: "change a loan", risk_tier: "low",
      signals: { bian: { service_domains: ["Consumer Loan"] } } });
    const dec = await c.decision.createDecision({ task_id: task.task_id, agent_id: "assistant:ann", selected_action: "execute",
      rationale: "sdk", uncertainty_score: 0 });
    const pol = await c.decision.evaluatePolicy({ task_id: task.task_id, decision_ref: dec.decision_id,
      policy_set_refs: [official!, inst.policy_set_ids[0]!] }) as unknown as Record<string, any>;
    expect(pol["verdict"]).toBe("require_approval");
    expect(pol["source_refs"][0].provision).toBe("Art. 9(2)");
    expect(pol["evaluations"]).toHaveLength(2);

    expect((await c.packs.uninstall(pack_id)).uninstalled).toBe(true);
    expect((await c.packs.list()).items.find(p => p.pack_id === pack_id)?.installed).toBeNull();
  });

  it("the capability check outside a task: tools, policy, and the person behind the call", async () => {
    const cap = await c.registry.issueCapability({ subject_agent: "assistant:ann", issuer: "sdk", principal_id: "user:ann",
      permitted_actions: ["delete_sequence"] });
    const ok = await c.registry.checkCapability(cap.capability_id, { agent_id: "assistant:ann", tool_id: "delete_sequence", acting_for: "user:ann" });
    expect(ok.enforcement_decision).toBe("PERMIT");
    const no = await c.registry.checkCapability(cap.capability_id, { agent_id: "assistant:ann", tool_id: "push_to_github" });
    expect([no.enforcement_decision, no.failed_check]).toEqual(["DENY", "tool_permitted"]);
  });

  it("execute-async: validated as it runs, its receipt finishes the task", async () => {
    const ps = await c.registry.registerPolicySet({ name: `sdk-${randomUUID().slice(0, 6)}`, version: "1", publisher: "sdk",
      regulatory_frameworks: [], jurisdictions: [], ruleset_hash: H("r"), ruleset_engine: "custom", attestation_level: "self",
      policy_engine: "rules", default_verdict: "allow", rules: [{ id: "all", verdict: "allow" }] } as never);
    const task = await c.registry.createTask({ principal_id: "user:ann", requested_outcome: "x", risk_tier: "low" });
    await c.registry.createLiabilityBinding({ task_id: task.task_id, sponsoring_entity: "sdk", accountable_owner: "user:ann", jurisdiction: "GLOBAL", risk_tier: "low" });
    const cap = await c.registry.issueCapability({ subject_agent: "assistant:ann", issuer: "sdk", principal_id: "user:ann",
      permitted_actions: ["x.do"], task_id: task.task_id });
    await c.registry.transitionTask(task.task_id, "ANALYZING");
    const dec = await c.decision.createDecision({ task_id: task.task_id, agent_id: "assistant:ann", selected_action: "execute", rationale: "r", uncertainty_score: 0 });
    const pol = await c.decision.evaluatePolicy({ task_id: task.task_id, decision_ref: dec.decision_id, policy_set_ref: (ps as unknown as { policy_set_id: string }).policy_set_id });
    const env = await c.execution.submitEnvelope({ task_id: task.task_id, agent_id: "assistant:ann", tool_id: "x.do", operation: {},
      capability_token_ref: cap.capability_id, decision_ref: dec.decision_id, policy_decision_ref: pol.policy_evaluation_id, async_mode: true }) as unknown as { action_envelope_ref: string };
    const action = env.action_envelope_ref;
    expect((await c.registry.getTask(task.task_id)).status).toBe("EXECUTING");
    await c.execution.recordReceipt({ action_ref: action, task_id: task.task_id, executor_id: "assistant:ann", outcome: "success" });
    expect((await c.registry.getTask(task.task_id)).status).toBe("COMPLETED");
  });

  it("detectors, the org's status, who's stopped", async () => {
    const s = await c.detectors.settings();
    expect(s.detectors.integrity.mode).toBe("enforce");
    expect((await c.detectors.orgStatus()).status).toBe("active");
    expect(Array.isArray((await c.detectors.signals()).items)).toBe(true);
    expect((await c.detectors.blocked()).org_status).toBe("active");
    expect(c.detectors.statusStreamUrl()).toMatch(/\/agp\/status-stream$/);
    const req = await c.detectors.proposeSettings({ velocity: { mode: "enforce" } }, "user:ann");
    expect(req.mode).toBe("dual");                                       // a two-person action
  });

  it("the ledger is read masked; raw needs agp.execution.admin", async () => {
    await c.ledger.report([{ client_event_id: randomUUID(), event_kind: "http.request", principal_id: "user:ann", action_class: "read",
      outcome: "executed", action: "GET /customers?email=ann@bank.com" }]);
    const items = (await c.ledger.events({ limit: 50, order: "desc" })).items as unknown as Record<string, unknown>[];
    expect(JSON.stringify(items)).not.toContain("ann@bank.com");
    await expect(c.ledger.events({ raw: true })).rejects.toBeInstanceOf(AGPForbiddenError);
  });

  it.skipIf(!(OP_ID && OP_SECRET))("the hub operator lists read-only orgs and can't read an org's ledger", async () => {
    const op = new AGPClient(URL_!, { client_id: OP_ID!, client_secret: OP_SECRET! });
    expect(Array.isArray((await op.operator.readOnlyOrgs()).items)).toBe(true);
    await expect(op.ledger.events({})).rejects.toBeInstanceOf(AGPForbiddenError);
    await expect(c.operator.readOnlyOrgs()).rejects.toBeInstanceOf(AGPForbiddenError);
  });
});
