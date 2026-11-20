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

// ── v0.9 (studio): the ledger, principals, reported events, kept content ─────

export type Outcome = "initiated" | "executed" | "failed" | "denied" | "revoked" | "quarantined" | "approval_granted" | "approval_denied";
export type ActionClass = "read" | "write" | "publish" | "transact" | "delete" | "admin";

/** An act a product reports (POST /agp/events). AGP sets the actor, org and source itself. */
export interface ReportedEvent {
  client_event_id?: string;          // filled in if missing; AGP records each id once per org
  event_kind: string;                // dotted lower case: "http.request", "tool.call", "ai.call"…
  principal_id: string;              // who acted
  acting_for?: string;               // whom an agent acted for
  action_class: ActionClass;
  action?: string;
  resource?: string;
  verdict?: "allow" | "deny" | "step_up" | "quarantined";
  outcome: Outcome;
  refs?: Record<string, unknown>;
  payload_hash?: string;             // "sha256:<64 hex>"
  session_id?: string;
  request_id?: string;
  observed_at?: string;
  detail?: Record<string, unknown>;
}

export interface LedgerVerification {
  org_id: string;
  ok: boolean;
  checked: number;
  break?: { event_id?: string; why: string };
  checkpoints: { ok: boolean; checked: number; break?: unknown };
}

export interface Checkpoint {
  type: "LedgerCheckpoint";
  checkpoint_id: string;
  org_id: string;
  from_position: number;
  to_position: number;
  head_event_id: string;
  head_hash: string;
  prev_checkpoint_hash: string | null;
  sealed_at: string;
  alg: "Ed25519";
  public_key: string;
  key_id: string;
  signature: string;
  anchor?: { scheme: string; token?: string; gen_time?: string; error?: string };
}

export interface CheckpointKey { alg: "Ed25519"; public_key: string; key_id: string; ephemeral: boolean; trusted_key_ids: string[] }

export type PrincipalKind = "user" | "assistant" | "mcp_client" | "a2a_agent" | "a2a_caller" | "api_key" | "service" | "job" | "script";
export type PrincipalStatus = "active" | "restricted" | "suspended" | "revoked";

export interface EffectiveStatus {
  principal_id: string;
  kind: PrincipalKind;
  status: PrincipalStatus;
  effective_status: PrincipalStatus;
  blocked_by: string | null;
  chain: string[];
}

export interface Principal {
  type: "Principal";
  principal_id: string;
  kind: PrincipalKind;
  display: string;
  acting_for: string | null;
  risk_tier: string;
  client_id: string | null;
  external_ref: string | null;
  status: PrincipalStatus;
  status_reason: string;
  status_since: string;
  status_by: string;
  pending_reinstatement?: { by: string; at: string; reason: string } | null;
  created_at: string;
  effective?: EffectiveStatus;
}

export type ContentKind = "prompt" | "answer" | "attachment" | "tool_arguments" | "tool_result";
export interface ContentItem { kind: ContentKind; data: string | Record<string, unknown> | unknown[]; media_type?: string; sha256?: string; truncated?: boolean; full_sha256?: string }
export interface StoredContent { content_id: string; sha256: string; expires_at: string }
export interface KeptContent {
  content_id: string; kind: ContentKind; media_type: string; sha256: string; size: number;
  truncated: boolean; full_sha256: string; created_at: string; expires_at: string; org_id: string;
  data: string | Record<string, unknown> | unknown[];
}

export interface ObjectVersion { resource_type: string; id: string; org_id: string; version: number; at: string; actor: string; data_hash: string; prev_hash: string | null; data: Record<string, unknown> }

export interface OAuthClient { client_id: string; scopes: string[]; created_at: string; description: string; org_id: string }

// ── AGP 1.0: approvals bound to people, detectors, packs, the capability check, the operator ───────────────

export type ApprovalMode = "self" | "single" | "dual" | "hub_and_org" | `multi:${number}`;
export interface ApprovalDecisionEntry { approver: string; decision: "approved" | "denied"; reason?: string; at: string; via?: string; hub?: boolean }
export interface ApprovalRequest {
  type: "ApprovalRequest"; request_id: string; action: string; params_hash: string; task_id?: string | null;
  requested_by: string; requested_for: string; mode: ApprovalMode; required: number; summary: string;
  status: "pending" | "approved" | "denied" | "expired"; decisions: ApprovalDecisionEntry[];
  approval_ref?: string; payload?: Record<string, unknown>; created_at: string; expires_at: string;
}
export interface BoundApproval {
  type: "ApprovalArtifact"; approval_id: string; request_id: string; task_id?: string | null; action: string; params_hash: string;
  decision: "approved"; approver_id: string; approver_ids: string[]; requested_by: string; requested_for: string;
  mode: ApprovalMode; approved_at: string; valid_until: string;
}

export type DetectorName = "velocity" | "scope_probing" | "integrity" | "ai_spend" | "bulk_read" | "destructive" | "credentials" | "agent_behaviour" | "time";
export type DetectorMode = "report" | "enforce" | "off";
export type DetectorResponse = "record" | "alert" | "step_up" | "restrict" | "suspend" | "org_read_only";
export interface DetectorSetting { mode: DetectorMode; response: DetectorResponse; [threshold: string]: unknown }
export interface AnomalySignal {
  type: "AnomalySignal"; signal_id: string; detector: DetectorName; principal_id: string | null; score: number;
  evidence: string[]; summary: string; mode: DetectorMode; response: DetectorResponse; at: string;
  context?: Record<string, unknown>;
}
export interface OrgStatus { org_id: string; status: "active" | "read_only"; reason: string | null; reinstated_by: "dual" | "hub_and_org" }
export interface BlockedSet { org_status: string; items: { principal_id: string; effective_status?: string; reason?: string; by?: string; step_up?: boolean }[] }

export interface SourceRef { provision: string; instrument?: string; [k: string]: string | undefined }
export interface PolicyPackSummary {
  pack_id: string; name: string; version: string; publisher: string; description: string; citation: Record<string, string>;
  channel: "official" | "org"; policy_sets: number; rules: number; versions?: string[];
  installed: { version: string; policy_set_ids: string[]; installed_at: string; installed_by: string } | null;
}
export interface PackInstall { install_id: string; pack_id: string; version: string; channel: string; manifest_hash: string; policy_set_ids: string[];
  installed_at: string; installed_by: string; replaced?: string | null; uninstalled?: boolean; uninstalled_at?: string }
/** A PolicyPack manifest (schemas/policy-pack.json). */
export interface PolicyPackManifest { apiVersion: "agp/v1"; kind: "PolicyPack"; metadata: Record<string, unknown>; spec: Record<string, unknown> }

export interface CapabilityCheck {
  valid: boolean; enforcement_decision: "PERMIT" | "DENY"; capability_id?: string; expires_at?: string;
  failed_check?: string; reason?: string; matched_rule?: string | number; source_refs?: SourceRef[]; pack_id?: string;
  policy?: { verdict: Verdict; matched_rule?: string | number; source_refs?: SourceRef[]; pack_id?: string };
  checks: { check: string; passed: boolean; detail?: string }[]; validated_at: string;
}
export interface ReadOnlyOrg { org_id: string; reason: string | null; requests: ApprovalRequest[] }
