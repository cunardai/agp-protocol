/**
 * AGP SDK — approvals bound to people (AGP 1.0, spec/studio-extensions.md §2.2)
 *
 * Ask for an action (its name and a hash of its parameters) for a person; other people decide; a granted request
 * issues an approval that is used once (redeem), for exactly that action, those parameters and that person.
 * Nobody approves their own action; the org's two-person list makes some actions need two others.
 */
import { Transport } from "./http.js";
import type { ApprovalMode, ApprovalRequest, BoundApproval } from "./types.js";

export class ApprovalsClient {
  constructor(private readonly t: Transport) {}

  async request(params: { action: string; params_hash: string; requested_by: string; requested_for?: string; task_id?: string;
                          mode?: ApprovalMode; summary?: string; expires_in_s?: number; payload?: Record<string, unknown> }): Promise<ApprovalRequest> {
    return this.t.post("/agp/approval-requests", params);
  }

  async list(params: { status?: ApprovalRequest["status"]; action?: string; limit?: number } = {}): Promise<{ items: ApprovalRequest[] }> {
    return this.t.get("/agp/approval-requests", params);
  }

  async get(request_id: string): Promise<ApprovalRequest> {
    return this.t.get(`/agp/approval-requests/${encodeURIComponent(request_id)}`);
  }

  /** A person's decision. Granted: the request carries the issued approval as `artifact`. */
  async decide(request_id: string, params: { approver: string; decision: "approved" | "denied"; reason?: string }): Promise<ApprovalRequest & { artifact?: BoundApproval }> {
    return this.t.post(`/agp/approval-requests/${encodeURIComponent(request_id)}/decisions`, params);
  }

  /** Use a granted approval for exactly this action, these parameters, this person — once. 404 when there's none. */
  async redeem(params: { action: string; params_hash: string; requested_for: string }): Promise<BoundApproval> {
    return this.t.post("/agp/approvals/redeem", params);
  }

  async twoPersonActions(): Promise<{ actions: string[]; fixed: string[] }> {
    return this.t.get("/agp/two-person-actions");
  }

  /** Changing the list is itself a two-person action: answers with the approval request, applied once granted. */
  async proposeTwoPersonActions(actions: string[], requested_by: string): Promise<ApprovalRequest> {
    return this.t.put("/agp/two-person-actions", { actions, requested_by });
  }
}
