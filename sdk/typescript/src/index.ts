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
export { LedgerClient } from "./ledger.js";
export { PrincipalsClient } from "./principals.js";
export { ContentClient, contentRef } from "./content.js";
export { AdminClient } from "./admin.js";

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
  AGPUnauthorizedError,
  AGPForbiddenError,
  AGPPrincipalBlockedError,
  AGPImmutableError,
  AGPLedgerUnavailableError,
  AGPAuthNotConfiguredError,
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
  // v0.9 studio profile
  Outcome, ActionClass, ReportedEvent, LedgerVerification, Checkpoint, CheckpointKey,
  PrincipalKind, PrincipalStatus, EffectiveStatus, Principal,
  ContentKind, ContentItem, StoredContent, KeptContent, ObjectVersion, OAuthClient,
} from "./types.js";
