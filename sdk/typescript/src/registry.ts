/**
 * AGP SDK — Registry API client
 */

import { futureIso, newIdempotencyKey, nowIso, Transport } from "./http.js";
import type {
  AttestationLevel, CapabilityToken, DelegationChain, GovernanceRequirements,
  LiabilityBinding, PagedResult, PolicySet, RequestOptions,
  RevocationNotice, RiskTier, RulesetEngine, SkillManifest, Task,
} from "./types.js";

export class RegistryClient {
  constructor(private readonly t: Transport) {}

  // ── Tasks ────────────────────────────────────────────────────────────

  async createTask(params: {
    principal_id: string;
    requested_outcome: string;
    risk_tier: RiskTier;
    expires_at?: string;
    sponsoring_entity?: string;
    governance_requirements?: GovernanceRequirements;
    jurisdictions?: string[];
    regulatory_frameworks?: string[];
  }, opts: RequestOptions = {}): Promise<Task> {
    const body: Record<string, unknown> = {
      principal_id:      params.principal_id,
      requested_outcome: params.requested_outcome,
      risk_tier:         params.risk_tier,
      created_at:        nowIso(),
    };
    if (params.expires_at)              body["expires_at"]              = params.expires_at;
    if (params.sponsoring_entity)       body["sponsoring_entity"]       = params.sponsoring_entity;
    if (params.governance_requirements) body["governance_requirements"] = params.governance_requirements;
    if (params.jurisdictions?.length)   body["jurisdictions"]           = params.jurisdictions;
    if (params.regulatory_frameworks?.length) body["regulatory_frameworks"] = params.regulatory_frameworks;

    return this.t.post<Task>("/agp/tasks", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  async getTask(task_id: string): Promise<Task> {
    return this.t.get<Task>(`/agp/tasks/${task_id}`);
  }

  async listTasks(params: {
    principal_id?: string;
    status?: string;
    limit?: number;
    cursor?: string;
  } = {}): Promise<PagedResult<Task>> {
    return this.t.get<PagedResult<Task>>("/agp/tasks", {
      principal_id: params.principal_id,
      status:       params.status,
      limit:        params.limit ?? 50,
      cursor:       params.cursor,
    });
  }

  async transitionTask(
    task_id: string,
    status: string,
    transition_guard_ref?: string,
  ): Promise<Task> {
    const body: Record<string, unknown> = { status };
    if (transition_guard_ref) body["transition_guard_ref"] = transition_guard_ref;
    return this.t.patch<Task>(`/agp/tasks/${task_id}`, body);
  }

  // ── Liability Bindings ────────────────────────────────────────────────

  async createLiabilityBinding(params: {
    task_id: string;
    sponsoring_entity: string;
    accountable_owner: string;
    jurisdiction: string;
    risk_tier: RiskTier;
  }, opts: RequestOptions = {}): Promise<LiabilityBinding> {
    return this.t.post<LiabilityBinding>("/agp/liability-bindings", {
      ...params,
      created_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  async getLiabilityBinding(binding_id: string): Promise<LiabilityBinding> {
    return this.t.get<LiabilityBinding>(`/agp/liability-bindings/${binding_id}`);
  }

  // ── Capability Tokens ─────────────────────────────────────────────────

  async issueCapability(params: {
    subject_agent: string;
    issuer: string;
    principal_id: string;
    permitted_actions: string[];
    constraints?: Record<string, unknown>;
    expires_at?: string;
    expires_in_days?: number;
    revocation_id?: string;
  }, opts: RequestOptions = {}): Promise<CapabilityToken> {
    return this.t.post<CapabilityToken>("/agp/capabilities", {
      subject_agent:     params.subject_agent,
      issuer:            params.issuer,
      principal_id:      params.principal_id,
      permitted_actions: params.permitted_actions,
      constraints:       params.constraints ?? {},
      expires_at:        params.expires_at ?? futureIso(params.expires_in_days ?? 30),
      revocation_id:     params.revocation_id ?? newIdempotencyKey(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  async getCapability(capability_id: string): Promise<CapabilityToken> {
    return this.t.get<CapabilityToken>(`/agp/capabilities/${capability_id}`);
  }

  // ── Delegations ───────────────────────────────────────────────────────

  async createDelegation(params: {
    root_principal: string;
    delegator_agent: string;
    delegate_agent: string;
    authority_scope: string[];
    constraints?: Record<string, unknown>;
    expires_at?: string;
    expires_in_days?: number;
    signature_chain?: string[];
    parent_delegation_id?: string;
  }, opts: RequestOptions = {}): Promise<DelegationChain> {
    const body: Record<string, unknown> = {
      root_principal:  params.root_principal,
      delegator_agent: params.delegator_agent,
      delegate_agent:  params.delegate_agent,
      authority_scope: params.authority_scope,
      constraints:     params.constraints ?? {},
      accepted_at:     nowIso(),
      expires_at:      params.expires_at ?? futureIso(params.expires_in_days ?? 30),
      signature_chain: params.signature_chain ?? [],
    };
    if (params.parent_delegation_id) body["parent_delegation_id"] = params.parent_delegation_id;
    return this.t.post<DelegationChain>("/agp/delegations", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  // ── Skills ────────────────────────────────────────────────────────────

  async registerSkill(params: {
    name: string;
    version: string;
    publisher: string;
    supported_protocols: string[];
    skill_class: string;
    risk_class: string;
    instruction_hash: string;
    attestation_level?: AttestationLevel;
  }, opts: RequestOptions = {}): Promise<SkillManifest> {
    return this.t.post<SkillManifest>("/agp/skills", {
      ...params,
      attestation_level: params.attestation_level ?? "self_attested",
      created_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  async listSkills(params: {
    publisher?: string;
    attestation_level?: string;
    risk_class?: string;
    limit?: number;
    cursor?: string;
  } = {}): Promise<PagedResult<SkillManifest>> {
    return this.t.get<PagedResult<SkillManifest>>("/agp/skills", {
      publisher:         params.publisher,
      attestation_level: params.attestation_level,
      risk_class:        params.risk_class,
      limit:             params.limit ?? 50,
      cursor:            params.cursor,
    });
  }

  // ── Policy Sets ───────────────────────────────────────────────────────

  async registerPolicySet(params: {
    name: string;
    version: string;
    publisher: string;
    regulatory_frameworks: string[];
    jurisdictions: string[];
    ruleset_hash: string;
    ruleset_engine?: RulesetEngine;
    attestation_level?: AttestationLevel;
    effective_from?: string;
    certifying_body?: string;
    supersedes?: string;
  }, opts: RequestOptions = {}): Promise<PolicySet> {
    const body: Record<string, unknown> = {
      name:                  params.name,
      version:               params.version,
      publisher:             params.publisher,
      regulatory_frameworks: params.regulatory_frameworks,
      jurisdictions:         params.jurisdictions,
      ruleset_hash:          params.ruleset_hash,
      ruleset_engine:        params.ruleset_engine   ?? "opa",
      attestation_level:     params.attestation_level ?? "self_attested",
      effective_from:        params.effective_from    ?? nowIso(),
      created_at:            nowIso(),
    };
    if (params.certifying_body) body["certifying_body"] = params.certifying_body;
    if (params.supersedes)      body["supersedes"]      = params.supersedes;
    return this.t.post<PolicySet>("/agp/policy-sets", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  async getPolicySet(policy_set_id: string): Promise<PolicySet> {
    return this.t.get<PolicySet>(`/agp/policy-sets/${policy_set_id}`);
  }

  async listPolicySets(params: {
    regulatory_framework?: string;
    jurisdiction?: string;
    status?: string;
    attestation_level?: string;
    limit?: number;
    cursor?: string;
  } = {}): Promise<PagedResult<PolicySet>> {
    return this.t.get<PagedResult<PolicySet>>("/agp/policy-sets", {
      regulatory_framework: params.regulatory_framework,
      jurisdiction:         params.jurisdiction,
      status:               params.status,
      attestation_level:    params.attestation_level,
      limit:                params.limit ?? 50,
      cursor:               params.cursor,
    });
  }

  async updatePolicySetStatus(policy_set_id: string, status: string): Promise<PolicySet> {
    return this.t.patch<PolicySet>(`/agp/policy-sets/${policy_set_id}`, { status });
  }

  // ── Revocations ───────────────────────────────────────────────────────

  async revoke(params: {
    issuer: string;
    target_type: string;
    target_id: string;
    reason: string;
  }, opts: RequestOptions = {}): Promise<RevocationNotice> {
    return this.t.post<RevocationNotice>("/agp/revocations", {
      ...params,
      effective_at: nowIso(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }
}
