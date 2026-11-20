/**
 * AGP SDK — Registry API client
 */

import { futureIso, newIdempotencyKey, nowIso, Transport } from "./http.js";
import type {
  AttestationLevel, CapabilityCheck, CapabilityToken, DelegationChain, GovernanceRequirements,
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
    /** What a policy's conditions read (AGP 1.0, Policy Packs): the tool or intent, its arguments, and
     *  namespaced signals (e.g. { bian: { service_domains: [...] } }). */
    tool?: string;
    intent?: string;
    arguments?: Record<string, unknown>;
    signals?: Record<string, unknown>;
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
    for (const k of ["tool", "intent", "arguments", "signals"] as const) if (params[k] !== undefined) body[k] = params[k];

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
    /** Bind it to one task (the §10 gate then refuses it for any other). */
    task_id?: string;
  }, opts: RequestOptions = {}): Promise<CapabilityToken> {
    return this.t.post<CapabilityToken>("/agp/capabilities", {
      ...(params.task_id ? { task_id: params.task_id } : {}),
      subject_agent:     params.subject_agent,
      issuer:            params.issuer,
      principal_id:      params.principal_id,
      permitted_actions: params.permitted_actions,
      constraints:       params.constraints ?? {},
      expires_at:        params.expires_at ?? futureIso(params.expires_in_days ?? 30),
      revocation_id:     params.revocation_id ?? newIdempotencyKey(),
    }, { idempotency_key: opts.idempotency_key ?? newIdempotencyKey() });
  }

  /**
   * May this agent use this tool under this capability, now? — for tool calls outside a task (AGP 1.0, §6).
   * Optionally judged by Policy Packs too: policy_set_refs ("installed" = every pack installed in the org) on
   * the call's signals and arguments; acting_for names the principal behind the call (checked too). A DENY
   * answers 403 — returned here, not thrown, so the caller can show the failed check and its provision.
   */
  async checkCapability(capability_id: string, params: {
    agent_id: string; tool_id: string; acting_for?: string; policy_set_refs?: string[] | "installed";
    signals?: Record<string, unknown>; arguments?: Record<string, unknown>; risk_tier?: string;
  }): Promise<CapabilityCheck> {
    return this.t.post<CapabilityCheck>(`/agp/capabilities/${encodeURIComponent(capability_id)}/check`, params, { allow_status: [403] });
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
    /** The engine the server runs to compute verdicts (v0.9: required) — "euai_act", "gdpr_dp", or "rules". */
    policy_engine?: string;
    /** For the "rules" engine: the verdict when no rule matches, and the rules (first match wins). */
    default_verdict?: string;
    default_rationale?: string;
    /** A rule: a condition tree (all / any / not over {field, op, value}) or v0.9's `when`; source_refs cite the
     *  provisions it implements; effective_from / _until bound when it applies (AGP 1.0, Policy Packs). */
    rules?: { id?: string; verdict: string; rationale?: string; when?: Record<string, unknown>; condition?: Record<string, unknown>;
              scope?: { tools?: string[] }; source_refs?: { provision: string; [k: string]: string }[];
              effective_from?: string; effective_until?: string; set?: Record<string, unknown>; require?: string[] }[];
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
    for (const k of ["policy_engine", "default_verdict", "default_rationale", "rules"] as const) {
      if (params[k] !== undefined) body[k] = params[k];
    }
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

  /** A policy set is never edited: a new version is a new PolicySet that supersedes this one. */
  async newPolicySetVersion(policy_set_id: string, params: Record<string, unknown>): Promise<PolicySet & { supersedes: string; lineage_id: string }> {
    return this.t.post(`/agp/policy-sets/${encodeURIComponent(policy_set_id)}/versions`, params);
  }

  /** Every version of a policy set, oldest first. */
  async policySetVersions(policy_set_id: string): Promise<{ lineage_id: string; items: PolicySet[] }> {
    return this.t.get(`/agp/policy-sets/${encodeURIComponent(policy_set_id)}/versions`);
  }

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
