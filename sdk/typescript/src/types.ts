/**
 * AGP TypeScript SDK — Protocol types
 *
 * Field names use snake_case to match the AGP wire format directly.
 * This avoids a translation layer and keeps stack traces readable.
 */

// ── Shared literals ──────────────────────────────────────────────────────────

export type RiskTier = "low" | "medium" | "high" | "critical";

export type TaskStatus =
  | "CREATED" | "BOUND" | "DELEGATED" | "SKILL_BOUND" | "COMMERCE_INIT"
  | "ANALYZING" | "DECIDED" | "POLICY_CHECKED" | "APPROVAL_PENDING"
  | "EXECUTING" | "COMPLETED" | "DENIED" | "REVOKED" | "QUARANTINED" | "FAILED";

export type Verdict =
  | "allow" | "deny" | "require_approval" | "require_stronger_auth" | "quarantine";

export type ApprovalDecision = "approved" | "denied";

export type PolicySetStatus = "active" | "deprecated" | "revoked";

export type RulesetEngine = "opa" | "cedar" | "casbin" | "custom";

export type AttestationLevel = "self_attested" | "third_party_attested" | "verified";

// ── Registry domain ──────────────────────────────────────────────────────────

export interface Task {
  task_id: string;
  principal_id: string;
  requested_outcome: string;
  risk_tier: RiskTier;
  status: TaskStatus;
  created_at: string;
  expires_at?: string;
  sponsoring_entity?: string;
  governance_requirements?: GovernanceRequirements;
  liability_binding_ref?: string;
  jurisdictions?: string[];
  regulatory_frameworks?: string[];
}

export interface GovernanceRequirements {
  required_roles: string[];
  quorum?: number;
}

export interface LiabilityBinding {
  binding_id: string;
  type: "LiabilityBinding";
  task_id: string;
  sponsoring_entity: string;
  accountable_owner: string;
  jurisdiction: string;
  risk_tier: RiskTier;
  created_at: string;
}

export interface CapabilityToken {
  capability_id: string;
  type: "CapabilityToken";
  subject_agent: string;
  issuer: string;
  principal_id: string;
  permitted_actions: string[];
  constraints: Record<string, unknown>;
  expires_at: string;
  revocation_id: string;
}

export interface DelegationChain {
  delegation_id: string;
  type: "DelegationChain";
  root_principal: string;
  delegator_agent: string;
  delegate_agent: string;
  authority_scope: string[];
  constraints: Record<string, unknown>;
  accepted_at: string;
  expires_at: string;
  signature_chain: string[];
  parent_delegation_id?: string;
}

export interface SkillManifest {
  skill_id: string;
  type: "SkillManifest";
  name: string;
  version: string;
  publisher: string;
  supported_protocols: string[];
  skill_class: string;
  risk_class: string;
  instruction_hash: string;
  attestation_level: AttestationLevel;
  created_at: string;
}

export interface PolicySet {
  policy_set_id: string;
  type: "PolicySet";
  name: string;
  version: string;
  publisher: string;
  regulatory_frameworks: string[];
  jurisdictions: string[];
  ruleset_hash: string;
  ruleset_engine: RulesetEngine;
  attestation_level: AttestationLevel;
  status: PolicySetStatus;
  effective_from: string;
  created_at: string;
  certifying_body?: string;
  supersedes?: string;
}

export interface RevocationNotice {
  revocation_id: string;
  type: "RevocationNotice";
  issuer: string;
  target_type: string;
  target_id: string;
  reason: string;
  effective_at: string;
}

// ── Decision domain ──────────────────────────────────────────────────────────

export interface AttestedContext {
  context_id: string;
  type: "AttestedContext";
  task_id: string;
  trust_class: string;
  created_at: string;
}

export interface EvidenceBundle {
  bundle_id: string;
  type: "EvidenceBundle";
  task_id: string;
  items: Array<Record<string, unknown>>;
  created_at: string;
}

export interface DecisionRecord {
  decision_id: string;
  type: "DecisionRecord";
  task_id: string;
  agent_id: string;
  selected_action: string;
  rationale: string;
  uncertainty_score: number;
  created_at: string;
}

export interface PolicyDecision {
  policy_evaluation_id: string;
  type: "PolicyDecision";
  task_id: string;
  decision_ref: string;
  verdict: Verdict;
  evaluated_at: string;
  policy_set_ref?: string;
  jurisdiction?: string;
  rationale?: string;
  matched_rules?: string[];
  obligations?: string[];
}

export interface ApprovalArtifact {
  approval_id: string;
  type: "ApprovalArtifact";
  task_id: string;
  approver_id: string;
  decision: ApprovalDecision;
  approved_at: string;
  notes?: string;
}

export interface EscalationNotice {
  escalation_id: string;
  type: "EscalationNotice";
  task_id: string;
  raised_by: string;
  concern_type: string;
  description: string;
  raised_at: string;
}

// ── Execution domain ─────────────────────────────────────────────────────────

export interface GovernanceAttestation {
  agent_role: string;
  verdict: "cleared" | "blocked";
  attestation_ref?: string;
}

export interface ActionEnvelope {
  action_id: string;
  type: "ActionEnvelope";
  task_id: string;
  agent_id: string;
  tool_id: string;
  operation: Record<string, unknown>;
  capability_token_ref: string;
  decision_ref: string;
  policy_decision_ref: string;
  created_at: string;
  approval_ref?: string;
  receipt_ref?: string;
  governance_attestations?: GovernanceAttestation[];
}

export interface ExecutionReceipt {
  receipt_id: string;
  type: "ExecutionReceipt";
  action_ref: string;
  task_id: string;
  executed_at: string;
  executor_id: string;
  outcome: string;
}

export interface EventLedgerRecord {
  event_id: string;
  type: "EventLedgerRecord";
  task_id: string;
  timestamp: string;
  agent_id: string;
  principal_id: string;
  outcome: string;
  prev_event_hash?: string;
  tool_action_ref?: string;
  decision_ref?: string;
}

export interface AsyncOperation {
  operation_id: string;
  status: string;
  created_at: string;
  status_url: string;
  action_envelope_ref?: string;
}

// ── Pagination ───────────────────────────────────────────────────────────────

export interface Page {
  has_more: boolean;
  next_cursor?: string | null;
}

export interface PagedResult<T> {
  items: T[];
  page: Page;
}

// ── Request option bags ───────────────────────────────────────────────────────

export interface RequestOptions {
  idempotency_key?: string;
}
