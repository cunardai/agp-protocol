/**
 * AGP SDK — Decision API client
 */

import { newIdempotencyKey, nowIso, Transport } from "./http.js";
import type {
  ApprovalArtifact, ApprovalDecision, AttestedContext, DecisionRecord,
  EscalationNotice, EvidenceBundle, PolicyDecision, RequestOptions, Verdict,
} from "./types.js";

export class DecisionClient {
  constructor(private readonly t: Transport) {}

  // ── Attested Contexts ─────────────────────────────────────────────────

  async createContext(params: {
    task_id: string;
    trust_class: string;
    [key: string]: unknown;
  }, opts: RequestOptions = {}): Promise<AttestedContext> {
    return this.t.post<AttestedContext>("/agp/decision/contexts", {
      ...params,
      created_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  async getContext(context_id: string): Promise<AttestedContext> {
    return this.t.get<AttestedContext>(`/agp/decision/contexts/${context_id}`);
  }

  // ── Evidence Bundles ──────────────────────────────────────────────────

  async createEvidenceBundle(params: {
    task_id: string;
    items: Array<Record<string, unknown>>;
  }, opts: RequestOptions = {}): Promise<EvidenceBundle> {
    return this.t.post<EvidenceBundle>("/agp/decision/evidence-bundles", {
      ...params,
      created_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  // ── Decisions ─────────────────────────────────────────────────────────

  async createDecision(params: {
    task_id: string;
    agent_id: string;
    selected_action: string;
    rationale: string;
    uncertainty_score: number;
    [key: string]: unknown;
  }, opts: RequestOptions = {}): Promise<DecisionRecord> {
    return this.t.post<DecisionRecord>("/agp/decision/decisions", {
      ...params,
      created_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  async getDecision(decision_id: string): Promise<DecisionRecord> {
    return this.t.get<DecisionRecord>(`/agp/decision/decisions/${decision_id}`);
  }

  // ── Policy Evaluations ────────────────────────────────────────────────

  /**
   * The verdict is the server's (AGP 1.0, §2.1): name the PolicySet (policy_set_ref) or several
   * (policy_set_refs — the most restrictive wins). A `verdict` is kept as caller_verdict and doesn't count,
   * except on a server that allows callers' verdicts (the v0.5 profile).
   */
  async evaluatePolicy(params: {
    task_id: string;
    decision_ref: string;
    verdict?: Verdict;
    rationale?: string;
    policy_set_ref?: string;
    policy_set_refs?: string[];
    jurisdiction?: string;
    matched_rules?: string[];
    obligations?: string[];
  }, opts: RequestOptions = {}): Promise<PolicyDecision> {
    const body: Record<string, unknown> = {
      task_id:      params.task_id,
      decision_ref: params.decision_ref,
      evaluated_at: nowIso(),
    };
    if (params.verdict)         body["verdict"]         = params.verdict;
    if (params.policy_set_refs) body["policy_set_refs"] = params.policy_set_refs;
    if (params.rationale)       body["rationale"]       = params.rationale;
    if (params.policy_set_ref)  body["policy_set_ref"]  = params.policy_set_ref;
    if (params.jurisdiction)    body["jurisdiction"]    = params.jurisdiction;
    if (params.matched_rules)   body["matched_rules"]   = params.matched_rules;
    if (params.obligations)     body["obligations"]     = params.obligations;
    return this.t.post<PolicyDecision>("/agp/decision/policy-evaluations", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  async getPolicyEvaluation(policy_evaluation_id: string): Promise<PolicyDecision> {
    return this.t.get<PolicyDecision>(
      `/agp/decision/policy-evaluations/${policy_evaluation_id}`,
    );
  }

  // ── Approvals ─────────────────────────────────────────────────────────

  async createApproval(params: {
    task_id: string;
    approver_id: string;
    decision: ApprovalDecision;
    notes?: string;
  }, opts: RequestOptions = {}): Promise<ApprovalArtifact> {
    const body: Record<string, unknown> = {
      task_id:     params.task_id,
      approver_id: params.approver_id,
      decision:    params.decision,
      approved_at: nowIso(),
    };
    if (params.notes) body["notes"] = params.notes;
    return this.t.post<ApprovalArtifact>("/agp/decision/approvals", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  async getApproval(approval_id: string): Promise<ApprovalArtifact> {
    return this.t.get<ApprovalArtifact>(`/agp/decision/approvals/${approval_id}`);
  }

  // ── Escalations ───────────────────────────────────────────────────────

  async escalate(params: {
    task_id: string;
    raised_by: string;
    concern_type: string;
    description: string;
  }, opts: RequestOptions = {}): Promise<EscalationNotice> {
    return this.t.post<EscalationNotice>("/agp/decision/escalations", {
      ...params,
      raised_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }
}
