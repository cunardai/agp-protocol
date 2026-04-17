/**
 * AGP TypeScript SDK — integration tests
 *
 * Runs against a live server. Set AGP_BASE_URL env var to override.
 *   AGP_BASE_URL=http://localhost:8099 npm test
 */

import { describe, it, expect, beforeAll } from "vitest";
import { AGPClient } from "../src/index.js";
import { AGPNotFoundError } from "../src/exceptions.js";

const SERVER_URL = process.env["AGP_BASE_URL"] ?? "http://localhost:8099";
let client: AGPClient;

beforeAll(() => {
  client = new AGPClient(SERVER_URL);
});

describe("TaskSession — full low-risk lifecycle", () => {
  it("creates a task, walks all steps, completes", async () => {
    const session = await client.taskSession({
      principal_id: "ts-agent-001",
      requested_outcome: "analyse sentiment",
      risk_tier: "low",
    });

    expect(session.task.status).toBe("CREATED");

    const token = await client.registry.issueCapability({
      subject_agent:     "ts-agent-001",
      issuer:            "ts-principal",
      principal_id:      "ts-principal",
      permitted_actions: ["analyse"],
    });
    session.withCapability(token);

    await session.bind({
      sponsoring_entity: "acme-corp",
      accountable_owner: "cto@acme.com",
      jurisdiction:      "EU",
    });
    expect(session.task.status).toBe("BOUND");

    await session.decide({
      agent_id:          "ts-agent-001",
      selected_action:   "analyse",
      rationale:         "No PII, standard NLP",
      uncertainty_score: 0.05,
    });
    expect(session.decision_record).not.toBeNull();

    await session.evaluate({ verdict: "allow" });
    expect(session.policy_decision?.verdict).toBe("allow");

    const result = await session.execute({
      agent_id:  "ts-agent-001",
      tool_id:   "nlp-tool",
      operation: { text: "analyse this feedback" },
    });
    expect(result).toHaveProperty("action_id");

    await session.refresh();
    expect(session.task.status).toBe("COMPLETED");
  });
});

describe("TaskSession — v0.6 fields", () => {
  it("stores jurisdictions and regulatory_frameworks on task", async () => {
    const session = await client.taskSession({
      principal_id:          "ts-agent-eu",
      requested_outcome:     "EU-governed analysis",
      risk_tier:             "medium",
      jurisdictions:         ["EU"],
      regulatory_frameworks: ["EU_AI_ACT_2024"],
    });
    expect(session.task.jurisdictions).toContain("EU");
    expect(session.task.regulatory_frameworks).toContain("EU_AI_ACT_2024");
  });
});

describe("resumeSession", () => {
  it("picks up an existing task by ID", async () => {
    const original = await client.taskSession({
      principal_id:      "ts-agent-resume",
      requested_outcome: "test resume",
      risk_tier:         "low",
    });
    const resumed = await client.resumeSession(original.task_id);
    expect(resumed.task_id).toBe(original.task_id);
    expect(resumed.task.status).toBe("CREATED");
  });
});

describe("Error handling", () => {
  it("throws AGPNotFoundError for unknown task", async () => {
    await expect(
      client.registry.getTask("tsk_doesnotexist"),
    ).rejects.toThrow(AGPNotFoundError);
  });

  it("throws AGPBadRequestError for missing required field", async () => {
    const { AGPBadRequestError } = await import("../src/exceptions.js");
    await expect(
      client.registry.createTask({
        principal_id:      "x",
        requested_outcome: "x",
        risk_tier:         "extreme" as never,  // invalid tier
      }),
    ).rejects.toThrow(AGPBadRequestError);
  });
});

describe("PolicySet lifecycle", () => {
  it("registers, deprecates, and revokes a PolicySet", async () => {
    const ps = await client.registry.registerPolicySet({
      name:                  "TS SDK Test PolicySet",
      version:               "1.0.0",
      publisher:             "ts-sdk-test",
      regulatory_frameworks: ["EU_AI_ACT_2024"],
      jurisdictions:         ["EU"],
      ruleset_hash:          `sha256:ts${Date.now()}`,
      ruleset_engine:        "opa",
    });
    expect(ps.status).toBe("active");

    const deprecated = await client.registry.updatePolicySetStatus(ps.policy_set_id, "deprecated");
    expect(deprecated.status).toBe("deprecated");

    const revoked = await client.registry.updatePolicySetStatus(ps.policy_set_id, "revoked");
    expect(revoked.status).toBe("revoked");
  });
});

describe("validate-only mode", () => {
  it("returns true without mutating task state", async () => {
    const session = await client.taskSession({
      principal_id:      "ts-agent-validate",
      requested_outcome: "test validate-only",
      risk_tier:         "low",
    });
    const token = await client.registry.issueCapability({
      subject_agent:     "ts-agent-validate",
      issuer:            "ts-principal",
      principal_id:      "ts-principal",
      permitted_actions: ["test"],
    });
    session.withCapability(token);
    await session.bind({ sponsoring_entity: "x", accountable_owner: "y@x.com", jurisdiction: "EU" });
    await session.decide({ agent_id: "ts-agent-validate", selected_action: "test", rationale: "test", uncertainty_score: 0.1 });
    await session.evaluate({ verdict: "allow" });

    await client.registry.transitionTask(session.task_id, "EXECUTING");

    const valid = await client.execution.validateEnvelope({
      task_id:              session.task_id,
      agent_id:             "ts-agent-validate",
      tool_id:              "test-tool",
      operation:            {},
      capability_token_ref: token.capability_id,
      decision_ref:         session.decision_record!.decision_id,
      policy_decision_ref:  session.policy_decision!.policy_evaluation_id,
    });
    expect(valid).toBe(true);
  });
});

describe("Audit replay", () => {
  it("returns ledger events after execution", async () => {
    const session = await client.taskSession({
      principal_id:      "ts-agent-replay",
      requested_outcome: "test replay",
      risk_tier:         "low",
    });
    const token = await client.registry.issueCapability({
      subject_agent:     "ts-agent-replay",
      issuer:            "ts-principal",
      principal_id:      "ts-principal",
      permitted_actions: ["test"],
    });
    session.withCapability(token);
    await session.bind({ sponsoring_entity: "x", accountable_owner: "y@x.com", jurisdiction: "EU" });
    await session.decide({ agent_id: "ts-agent-replay", selected_action: "test", rationale: "test", uncertainty_score: 0.1 });
    await session.evaluate({ verdict: "allow" });
    await session.execute({ agent_id: "ts-agent-replay", tool_id: "test-tool", operation: {} });

    const events = await session.replay();
    expect(events.length).toBeGreaterThanOrEqual(1);
  });
});
