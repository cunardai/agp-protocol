/**
 * AGP SDK — Execution API client
 */

import { newIdempotencyKey, nowIso, Transport } from "./http.js";
import type {
  ActionEnvelope, AsyncOperation, EventLedgerRecord,
  ExecutionReceipt, GovernanceAttestation, PagedResult, RequestOptions,
} from "./types.js";

export type SubmitEnvelopeResult = ActionEnvelope | AsyncOperation;

export class ExecutionClient {
  constructor(private readonly t: Transport) {}

  // ── Action Envelopes ──────────────────────────────────────────────────

  async submitEnvelope(params: {
    task_id: string;
    agent_id: string;
    tool_id: string;
    operation: Record<string, unknown>;
    capability_token_ref: string;
    decision_ref: string;
    policy_decision_ref: string;
    approval_ref?: string;
    governance_attestations?: GovernanceAttestation[];
    /** execute-async: the product carries the action out — it validates, acts, and its receipt finishes the task. */
    async_mode?: boolean;
    /** The action's parameters' hash: an approval for other parameters is refused (§2.2). */
    params_hash?: string;
  }, opts: RequestOptions = {}): Promise<SubmitEnvelopeResult> {
    const body: Record<string, unknown> = {
      task_id:              params.task_id,
      agent_id:             params.agent_id,
      tool_id:              params.tool_id,
      operation:            params.operation,
      capability_token_ref: params.capability_token_ref,
      decision_ref:         params.decision_ref,
      policy_decision_ref:  params.policy_decision_ref,
      created_at:           nowIso(),
    };
    if (params.approval_ref)             body["approval_ref"]             = params.approval_ref;
    if (params.governance_attestations)  body["governance_attestations"]  = params.governance_attestations;
    if (params.params_hash)              body["params_hash"]              = params.params_hash;

    const prefer = params.async_mode ? "execute-async" : undefined;
    return this.t.post<SubmitEnvelopeResult>("/agp/action-envelopes", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
      prefer,
    });
  }

  async validateEnvelope(params: {
    task_id: string;
    agent_id: string;
    tool_id: string;
    operation: Record<string, unknown>;
    capability_token_ref: string;
    decision_ref: string;
    policy_decision_ref: string;
    approval_ref?: string;
  }): Promise<boolean> {
    const body: Record<string, unknown> = {
      task_id:              params.task_id,
      agent_id:             params.agent_id,
      tool_id:              params.tool_id,
      operation:            params.operation,
      capability_token_ref: params.capability_token_ref,
      decision_ref:         params.decision_ref,
      policy_decision_ref:  params.policy_decision_ref,
      created_at:           nowIso(),
    };
    if (params.approval_ref) body["approval_ref"] = params.approval_ref;
    const result = await this.t.post<{ valid: boolean }>(
      "/agp/action-envelopes", body, { prefer: "validate-only" },
    );
    return result.valid === true;
  }

  async getEnvelope(action_id: string): Promise<ActionEnvelope> {
    return this.t.get<ActionEnvelope>(`/agp/action-envelopes/${action_id}`);
  }

  // ── Receipts ──────────────────────────────────────────────────────────

  /** The product's receipt for an action it carried out (execute-async): it finishes the task (§2.6). */
  async recordReceipt(params: { action_ref: string; task_id: string; executor_id: string; outcome: "success" | "failed"; executed_at?: string;
                                [extra: string]: unknown }): Promise<ExecutionReceipt> {
    return this.t.post<ExecutionReceipt>("/agp/execution-receipts", { executed_at: nowIso(), ...params }, { idempotency_key: newIdempotencyKey() });
  }

  async getReceipt(receipt_id: string): Promise<ExecutionReceipt> {
    return this.t.get<ExecutionReceipt>(`/agp/execution-receipts/${receipt_id}`);
  }

  // ── Ledger ────────────────────────────────────────────────────────────

  async appendLedgerEvent(params: {
    task_id: string;
    agent_id: string;
    principal_id: string;
    outcome: string;
    prev_event_hash?: string;
    tool_action_ref?: string;
    decision_ref?: string;
  }, opts: RequestOptions = {}): Promise<EventLedgerRecord> {
    const body: Record<string, unknown> = {
      task_id:      params.task_id,
      timestamp:    nowIso(),
      agent_id:     params.agent_id,
      principal_id: params.principal_id,
      outcome:      params.outcome,
    };
    if (params.prev_event_hash) body["prev_event_hash"] = params.prev_event_hash;
    if (params.tool_action_ref) body["tool_action_ref"] = params.tool_action_ref;
    if (params.decision_ref)    body["decision_ref"]    = params.decision_ref;
    return this.t.post<EventLedgerRecord>("/agp/ledger-events", body, {
      idempotency_key: opts.idempotency_key ?? newIdempotencyKey(),
    });
  }

  async listLedgerEvents(params: {
    task_id?: string;
    outcome?: string;
    limit?: number;
    cursor?: string;
  } = {}): Promise<PagedResult<EventLedgerRecord>> {
    return this.t.get<PagedResult<EventLedgerRecord>>("/agp/ledger-events", {
      task_id: params.task_id,
      outcome:  params.outcome,
      limit:   params.limit ?? 100,
      cursor:  params.cursor,
    });
  }

  async replayTask(task_id: string): Promise<{ task_id: string; events: EventLedgerRecord[]; replay_complete: boolean }> {
    return this.t.get(`/agp/tasks/${task_id}/replay`);
  }

  // ── Async Operations ──────────────────────────────────────────────────

  async getOperation(operation_id: string): Promise<AsyncOperation> {
    return this.t.get<AsyncOperation>(`/agp/operations/${operation_id}`);
  }
}
