/**
 * AGP SDK — the hub operator (AGP 1.0, spec/studio-extensions.md §4.4)
 *
 * A credential not tied to an org (scope agp.operator only): it lists read-only orgs and decides the hub's half of
 * reinstating one (hub_and_org), naming the hub's person. It can read nothing else in an org.
 */
import { Transport } from "./http.js";
import type { ApprovalRequest, ReadOnlyOrg } from "./types.js";

export class OperatorClient {
  constructor(private readonly t: Transport) {}

  async readOnlyOrgs(prefix?: string): Promise<{ items: ReadOnlyOrg[] }> {
    return this.t.get("/agp/operator/orgs", prefix ? { prefix } : {});
  }

  async decide(org_id: string, request_id: string, params: { approver: string; decision: "approved" | "denied"; reason?: string }): Promise<ApprovalRequest> {
    return this.t.post(`/agp/operator/orgs/${encodeURIComponent(org_id)}/approval-requests/${encodeURIComponent(request_id)}/decisions`, params);
  }
}
