/**
 * AGP TypeScript SDK — the v0.9 studio profile, against a live server with auth on.
 *
 *   AGP_AUTH_BASE_URL=http://localhost:8098 AGP_PROVISIONER_ID=… AGP_PROVISIONER_SECRET=… npm test
 *
 * The server's bootstrap client must hold agp.org.provision (AGP_CLIENT_SCOPES=agp.org.provision).
 * Each run provisions a fresh org, so runs don't see each other.
 */
import { describe, it, expect, beforeAll } from "vitest";
import {
  AGPClient, AGPConflictError, AGPPrincipalBlockedError, AGPUnauthorizedError, AGPForbiddenError, contentRef,
} from "../src/index.js";

const URL_ = process.env["AGP_AUTH_BASE_URL"];
const PROV_ID = process.env["AGP_PROVISIONER_ID"];
const PROV_SECRET = process.env["AGP_PROVISIONER_SECRET"];
const live = !!(URL_ && PROV_ID && PROV_SECRET);
const ALL = ["agp.registry.read", "agp.registry.write", "agp.decision.read", "agp.decision.write", "agp.execution.read",
             "agp.execution.write", "agp.approval.write", "agp.policy.write", "agp.revocation.write", "agp.principal.admin", "agp.content.read"];

let org = "";
let c: AGPClient;

describe.skipIf(!live)("studio profile", () => {
  beforeAll(async () => {
    const prov = new AGPClient(URL_!, { client_id: PROV_ID!, client_secret: PROV_SECRET! });
    org = `sdk-${crypto.randomUUID().slice(0, 8)}`;
    const made = await prov.admin.provisionOrgClient(org, { client_id: `sdk-${org}`, scopes: ALL });
    c = new AGPClient(URL_!, { client_id: made.client_id, client_secret: made.client_secret });
    // Provisioning is once: the org now has a client, so it's not the provisioner's to add to.
    await expect(prov.admin.provisionOrgClient(org, { client_id: `x-${org}`, scopes: ["agp.execution.write"] })).rejects.toBeInstanceOf(AGPConflictError);
  });

  it("refuses without credentials", async () => {
    await expect(new AGPClient(URL_!).registry.listTasks({})).rejects.toBeInstanceOf(AGPUnauthorizedError);
  });

  it("reports acts once, AGP naming the reporter", async () => {
    const events = [
      { client_event_id: "e1", event_kind: "http.request", principal_id: "user:ann", action_class: "read" as const, outcome: "executed" as const },
      { client_event_id: "e2", event_kind: "tool.call", principal_id: "assistant:ann", acting_for: "user:ann", action_class: "write" as const, outcome: "initiated" as const },
    ];
    expect((await c.ledger.report(events)).recorded).toBe(2);
    expect((await c.ledger.report(events)).duplicates).toBe(2);
    const items = (await c.ledger.events({ limit: 100 })).items as unknown as Record<string, unknown>[];
    const mine = items.filter(e => e["source"] === "reported");
    expect(mine.map(e => e["actor"])).toEqual([`sdk-${org}`, `sdk-${org}`]);
  });

  it("seals, verifies, and exports an evidence pack", async () => {
    await c.ledger.report([{ event_kind: "export.done", principal_id: "user:ann", action_class: "read", outcome: "executed" }]);
    const cp = await c.ledger.seal();
    expect("checkpoint_id" in cp).toBe(true);
    expect((await c.ledger.verify()).ok).toBe(true);
    expect((await c.ledger.checkpoints()).items.length).toBeGreaterThan(0);
    const key = await c.ledger.checkpointKey();
    expect(key.alg).toBe("Ed25519");
    const pack = await c.ledger.evidencePack();
    expect(new Uint8Array(pack.bytes).slice(0, 2)).toEqual(new Uint8Array([0x50, 0x4b]));   // a zip
    expect(pack.filename).toMatch(/^agp-evidence-/);
  });

  it("principals: a person's suspension stops whoever acts for them; two admins reinstate", async () => {
    await c.principals.register({ principal_id: "user:ann", kind: "user" });
    await c.principals.register({ principal_id: "user:bo", kind: "user" });
    await c.principals.register({ principal_id: "user:cy", kind: "user" });
    await c.principals.register({ principal_id: "assistant:ann", kind: "assistant", acting_for: "user:ann" });
    await c.principals.setStatus("user:ann", { status: "suspended", reason: "sdk test", on_behalf_of: "user:bo" });
    const eff = (await c.principals.get("assistant:ann")).effective!;
    expect([eff.effective_status, eff.blocked_by]).toEqual(["suspended", "user:ann"]);
    await expect(c.registry.createTask({ principal_id: "assistant:ann", requested_outcome: "x", risk_tier: "low" }))
      .rejects.toBeInstanceOf(AGPPrincipalBlockedError);
    expect((await c.principals.setStatus("user:ann", { status: "active", reason: "ok", on_behalf_of: "user:bo" })).pending).toBe(true);
    await expect(c.principals.setStatus("user:ann", { status: "active", reason: "again", on_behalf_of: "user:bo" })).rejects.toBeInstanceOf(AGPForbiddenError);
    expect((await c.principals.setStatus("user:ann", { status: "active", reason: "agreed", on_behalf_of: "user:cy" })).status).toBe("active");
    expect((await c.principals.history("user:ann")).verify.ok).toBe(true);
  });

  it("content: the id and hash computed here are the ones AGP gives, whatever the characters", async () => {
    const text = JSON.stringify({ messages: [{ role: "user", content: "Zoë owes £300 — 日本語" }] });
    const ref = await contentRef(text);
    const [stored] = (await c.content.store([{ kind: "prompt", data: ref.data, sha256: ref.sha256 }])).stored;
    expect(stored!.content_id).toBe(ref.content_id);
    expect((await c.content.get(ref.content_id)).data).toBe(text);
    expect((await c.content.setRetention(30)).days).toBe(30);
    expect((await c.content.retention()).days).toBe(30);
  });

  it("objects keep their versions; policy sets are superseded", async () => {
    const t = await c.registry.createTask({ principal_id: "user:bo", requested_outcome: "x", risk_tier: "low" });
    await c.registry.transitionTask(t.task_id, "BOUND");
    const v = await c.admin.versions("tasks", t.task_id);
    expect(v.items.map(i => i.data["status"])).toEqual(["CREATED", "BOUND"]);
    expect(v.verify.ok).toBe(true);
    const ps = await c.registry.registerPolicySet({
      name: "Limits", version: "1.0.0", publisher: "sdk", regulatory_frameworks: ["X"], jurisdictions: ["EU"],
      ruleset_hash: "sha256:" + "a".repeat(64), ruleset_engine: "custom", attestation_level: "self_attested",
      // Verdicts come from the server: every policy set needs an engine (here, rules of its own).
      policy_engine: "rules", default_verdict: "allow", rules: [{ id: "big", verdict: "require_approval", when: { risk_tier_in: ["high"] } }],
    });
    const next = await c.registry.newPolicySetVersion(ps.policy_set_id, {
      name: "Limits", version: "1.1.0", publisher: "sdk", regulatory_frameworks: ["X"], jurisdictions: ["EU"],
      ruleset_hash: "sha256:" + "b".repeat(64), ruleset_engine: "custom", attestation_level: "self_attested",
      effective_from: new Date().toISOString(), created_at: new Date().toISOString(),
      policy_engine: "rules", default_verdict: "allow", rules: [{ id: "big", verdict: "deny", when: { risk_tier_in: ["high"] } }],
    });
    expect(next.supersedes).toBe(ps.policy_set_id);
    expect((await c.registry.policySetVersions(next.policy_set_id)).items.map(p => p.version)).toEqual(["1.0.0", "1.1.0"]);
  });

  it("clients: registered in the org, deleted for good", async () => {
    const made = await c.admin.registerClient({ client_id: `p-${org}`, scopes: ["agp.registry.read"] });
    expect(made.client_secret.length).toBeGreaterThan(16);
    expect((await c.admin.listClients()).items.map(x => x.client_id)).toContain(`p-${org}`);
    await c.admin.deleteClient(`p-${org}`);
    await expect(c.admin.registerClient({ client_id: `p-${org}`, scopes: [] })).rejects.toBeInstanceOf(AGPConflictError);
  });
});
