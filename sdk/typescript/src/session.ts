/**
 * AGP SDK — TaskSession
 *
 * Fluent, stateful wrapper around the full AGP task lifecycle.
 * Manages all artifact refs internally so callers never pass
 * decision_id / policy_evaluation_id between calls manually.
 *
 * Usage:
 *   const session = await client.taskSession({ principal_id: "agent-1", ... });
 *   await session.bind({ sponsoring_entity: "acme", ... });
 *   await session.decide({ agent_id: "agent-1", selected_action: "analyse", ... });
 *   await session.evaluate({ verdict: "allow" });
 *   const result = await session.execute({ agent_id: "agent-1", tool_id: "nlp", operation: {} });
 */

import type { DecisionClient } from "./decision.js";
import type { SubmitEnvelopeResult } from "./execution.js";
import type { ExecutionClient } from "./execution.js";
import type { RegistryClient } from "./registry.js";
import type {
  ActionEnvelope, ApprovalArtifact, AsyncOperation,
  CapabilityToken, DecisionRecord, GovernanceAttestation,
  LiabilityBinding, PolicyDecision, RiskTier, Task,
} from "./types.js";

export class TaskSession {
  task: Task;

  // Accumulated artifacts
  liability_binding: LiabilityBinding | null = null;
  capability_token:  CapabilityToken  | null = null;
  decision_record:   DecisionRecord   | null = null;
  policy_decision:   PolicyDecision   | null = null;
  approval:          ApprovalArtifact | null = null;

  constructor(
    private readonly reg: RegistryClient,
    private readonly dec: DecisionClient,
    private readonly exe: ExecutionClient,
    task: Task,
  ) {
    this.task = task;
  }

  get task_id(): string { return this.task.task_id; }

  // ── Step 1: Bind liability ──────────────────────────────────────────

  async bind(params: {
    sponsoring_entity: string;
    accountable_owner: string;
    jurisdiction: string;
    risk_tier?: RiskTier;
  }): Promise<this> {
    this.liability_binding = await this.reg.createLiabilityBinding({
      task_id:           this.task_id,
      sponsoring_entity: params.sponsoring_entity,
      accountable_owner: params.accountable_owner,
      jurisdiction:      params.jurisdiction,
      risk_tier:         params.risk_tier ?? this.task.risk_tier,
    });
    this.task = await this.reg.getTask(this.task_id);
    return this;
  }

  // ── Step 1b: Capability token ───────────────────────────────────────

  async issueCapability(params: {
    subject_agent: string;
    issuer: string;
    principal_id: string;
    permitted_actions: string[];
    constraints?: Record<string, unknown>;
    expires_in_days?: number;
  }): Promise<this> {
    this.capability_token = await this.reg.issueCapability(params);
    return this;
  }

  withCapability(token: CapabilityToken): this {
    this.capability_token = token;
    return this;
  }

  // ── Step 2: Decision ────────────────────────────────────────────────

  async decide(params: {
    agent_id: string;
    selected_action: string;
    rationale: string;
    uncertainty_score: number;
  }): Promise<this> {
    const current = await this.reg.getTask(this.task_id);
    if (current.status === "BOUND") {
      await this.reg.transitionTask(this.task_id, "ANALYZING");
    }
    this.decision_record = await this.dec.createDecision({
      task_id: this.task_id,
      ...params,
    });
    this.task = await this.reg.getTask(this.task_id);
    return this;
  }

  // ── Step 3: Policy evaluation ───────────────────────────────────────

  async evaluate(params: {
    verdict: string;
    rationale?: string;
    policy_set_ref?: string;
    jurisdiction?: string;
    matched_rules?: string[];
    obligations?: string[];
  }): Promise<this> {
    if (!this.decision_record) {
      throw new Error("Call decide() before evaluate()");
    }
    this.policy_decision = await this.dec.evaluatePolicy({
      task_id:       this.task_id,
      decision_ref:  this.decision_record.decision_id,
      verdict:       params.verdict as never,
      rationale:     params.rationale,
      policy_set_ref: params.policy_set_ref,
      jurisdiction:  params.jurisdiction,
      matched_rules: params.matched_rules,
      obligations:   params.obligations,
    });
    this.task = await this.reg.getTask(this.task_id);
    return this;
  }

  // ── Step 4 (conditional): Human approval ───────────────────────────

  async approve(params: {
    approver_id: string;
    decision?: "approved" | "denied";
    notes?: string;
  }): Promise<this> {
    this.approval = await this.dec.createApproval({
      task_id:     this.task_id,
      approver_id: params.approver_id,
      decision:    params.decision ?? "approved",
      notes:       params.notes,
    });
    this.task = await this.reg.getTask(this.task_id);
    return this;
  }

  async escalate(params: {
    raised_by: string;
    concern_type: string;
    description: string;
  }): Promise<this> {
    await this.dec.escalate({ task_id: this.task_id, ...params });
    return this;
  }

  // ── Step 5: Execute ─────────────────────────────────────────────────

  async execute(params: {
    agent_id: string;
    tool_id: string;
    operation: Record<string, unknown>;
    capability_token_ref?: string;
    governance_attestations?: GovernanceAttestation[];
    async_mode?: boolean;
  }): Promise<SubmitEnvelopeResult> {
    if (!this.policy_decision) {
      throw new Error("Call evaluate() before execute()");
    }

    const cap_ref = params.capability_token_ref
      ?? this.capability_token?.capability_id;
    if (!cap_ref) {
      throw new Error(
        "No capability_token_ref. Call issueCapability(), withCapability(), or pass capability_token_ref.",
      );
    }

    // Advance to EXECUTING if still at POLICY_CHECKED
    const current = await this.reg.getTask(this.task_id);
    if (current.status === "POLICY_CHECKED") {
      await this.reg.transitionTask(this.task_id, "EXECUTING");
    }

    const result = await this.exe.submitEnvelope({
      task_id:              this.task_id,
      agent_id:             params.agent_id,
      tool_id:              params.tool_id,
      operation:            params.operation,
      capability_token_ref: cap_ref,
      decision_ref:         this.decision_record!.decision_id,
      policy_decision_ref:  this.policy_decision.policy_evaluation_id,
      approval_ref:         this.approval?.approval_id,
      governance_attestations: params.governance_attestations,
      async_mode:           params.async_mode,
    });

    if (!params.async_mode) {
      this.task = await this.reg.getTask(this.task_id);
    }
    return result;
  }

  // ── Utilities ───────────────────────────────────────────────────────

  async refresh(): Promise<this> {
    this.task = await this.reg.getTask(this.task_id);
    return this;
  }

  async replay(): Promise<import("./types.js").EventLedgerRecord[]> {
    const result = await this.exe.replayTask(this.task_id);
    return result.events;
  }

  async fail(): Promise<void> {
    try {
      await this.reg.transitionTask(this.task_id, "FAILED");
    } catch {
      // Best-effort
    }
  }
}
