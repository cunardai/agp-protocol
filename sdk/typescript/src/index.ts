/**
 * AGP TypeScript SDK — Agent Governance Protocol
 * https://agp.dev
 */

export { AGPClient } from "./client.js";
export type { AGPClientOptions } from "./client.js";

export { TaskSession } from "./session.js";

export { RegistryClient } from "./registry.js";
export { DecisionClient } from "./decision.js";
export { ExecutionClient } from "./execution.js";
export type { SubmitEnvelopeResult } from "./execution.js";

export {
  AGPError,
  AGPNotFoundError,
  AGPBadRequestError,
  AGPConflictError,
  AGPUnprocessableError,
  AGPPolicyDeniedError,
  AGPTokenRevokedError,
  AGPTokenExpiredError,
  AGPApprovalRequiredError,
  AGPServerError,
  AGPConnectionError,
} from "./exceptions.js";

export type {
  // Shared
  RiskTier, TaskStatus, Verdict, ApprovalDecision,
  PolicySetStatus, RulesetEngine, AttestationLevel,
  // Registry
  Task, GovernanceRequirements, LiabilityBinding, CapabilityToken,
  DelegationChain, SkillManifest, PolicySet, RevocationNotice,
  // Decision
  AttestedContext, EvidenceBundle, DecisionRecord,
  PolicyDecision, ApprovalArtifact, EscalationNotice,
  // Execution
  GovernanceAttestation, ActionEnvelope, ExecutionReceipt,
  EventLedgerRecord, AsyncOperation,
  // Pagination
  Page, PagedResult,
  // Options
  RequestOptions,
} from "./types.js";
