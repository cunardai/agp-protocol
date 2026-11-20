/**
 * AGP SDK — AGPClient
 *
 * Top-level entry point. Composes RegistryClient, DecisionClient,
 * ExecutionClient, and TaskSession.
 *
 * Usage:
 *   import { AGPClient } from "agp";
 *
 *   const client = new AGPClient("http://localhost:8099");
 *
 *   // High-level session API
 *   const session = await client.taskSession({
 *     principal_id: "my-agent",
 *     requested_outcome: "analyse sentiment",
 *     risk_tier: "low",
 *   });
 *   await session.bind({ sponsoring_entity: "acme", accountable_owner: "cto@acme.com", jurisdiction: "EU" });
 *   await session.decide({ agent_id: "my-agent", selected_action: "analyse", rationale: "safe", uncertainty_score: 0.05 });
 *   await session.evaluate({ verdict: "allow" });
 *   const result = await session.execute({ agent_id: "my-agent", tool_id: "nlp", operation: {} });
 *
 *   // Low-level direct API
 *   const task = await client.registry.createTask({ ... });
 *   const pe   = await client.decision.evaluatePolicy({ ... });
 */

import { AdminClient } from "./admin.js";
import { ApprovalsClient } from "./approvals.js";
import { DetectorsClient } from "./detectors.js";
import { OperatorClient } from "./operator.js";
import { PacksClient } from "./packs.js";
import { ContentClient } from "./content.js";
import { DecisionClient } from "./decision.js";
import { LedgerClient } from "./ledger.js";
import { PrincipalsClient } from "./principals.js";
import { ExecutionClient } from "./execution.js";
import { Transport } from "./http.js";
import { RegistryClient } from "./registry.js";
import { TaskSession } from "./session.js";
import type { GovernanceRequirements, RiskTier, Task } from "./types.js";

export interface AGPClientOptions {
  /** HTTP request timeout in milliseconds (default: 30 000) */
  timeout_ms?: number;
  /** Additional headers sent with every request */
  headers?: Record<string, string>;
  /** OAuth 2.0 client credentials — fetches and caches bearer tokens automatically */
  client_id?: string;
  client_secret?: string;
}

export class AGPClient {
  readonly registry:  RegistryClient;
  readonly decision:  DecisionClient;
  readonly execution: ExecutionClient;
  /** The ledger: report acts, verify, checkpoints, evidence packs. */
  readonly ledger:     LedgerClient;
  /** The principal register (E1): who acts, for whom, and whether they may. */
  readonly principals: PrincipalsClient;
  /** Kept prompts and answers, with the org's retention. */
  readonly content:    ContentClient;
  /** OAuth clients, provisioning an org's first client, object history. */
  readonly admin:      AdminClient;
  /** Approvals bound to people: ask, decide, redeem once; the org's two-person list. */
  readonly approvals:  ApprovalsClient;
  /** Detectors (E2), the org's status, step-up, who's stopped now. */
  readonly detectors:  DetectorsClient;
  /** Policy Packs: publish, install, uninstall; verdicts cite their provisions. */
  readonly packs:      PacksClient;
  /** The hub operator (scope agp.operator): read-only orgs, the hub's half of reinstating one. */
  readonly operator:   OperatorClient;

  private readonly transport: Transport;

  constructor(base_url: string, options: AGPClientOptions = {}) {
    this.transport = new Transport({
      base_url,
      ...(options.timeout_ms    !== undefined && { timeout_ms:    options.timeout_ms }),
      ...(options.headers       !== undefined && { headers:       options.headers }),
      ...(options.client_id     !== undefined && { client_id:     options.client_id }),
      ...(options.client_secret !== undefined && { client_secret: options.client_secret }),
    });
    this.registry  = new RegistryClient(this.transport);
    this.decision  = new DecisionClient(this.transport);
    this.execution = new ExecutionClient(this.transport);
    this.ledger     = new LedgerClient(this.transport);
    this.principals = new PrincipalsClient(this.transport);
    this.content    = new ContentClient(this.transport);
    this.admin      = new AdminClient(this.transport);
    this.approvals  = new ApprovalsClient(this.transport);
    this.detectors  = new DetectorsClient(this.transport);
    this.packs      = new PacksClient(this.transport);
    this.operator   = new OperatorClient(this.transport);
  }

  /**
   * Create a new task and return a TaskSession bound to it.
   * On error, call session.fail() to mark the task FAILED.
   */
  async taskSession(params: {
    principal_id: string;
    requested_outcome: string;
    risk_tier: RiskTier;
    expires_at?: string;
    sponsoring_entity?: string;
    governance_requirements?: GovernanceRequirements;
    jurisdictions?: string[];
    regulatory_frameworks?: string[];
  }): Promise<TaskSession> {
    const task = await this.registry.createTask(params);
    return new TaskSession(this.registry, this.decision, this.execution, task);
  }

  /**
   * Resume a TaskSession for an existing task.
   * Useful for picking up APPROVAL_PENDING tasks from a queue.
   */
  async resumeSession(task_id: string): Promise<TaskSession> {
    const task = await this.registry.getTask(task_id);
    return new TaskSession(this.registry, this.decision, this.execution, task);
  }
}
