/**
 * AGP SDK — detectors (E2), the org's status and step-up (AGP 1.0, spec/studio-extensions.md §4, §9)
 *
 * Detectors read the ledger and stop a principal whose behaviour turns anomalous (report mode alerts only).
 * An integrity failure makes the org read-only; reinstating it takes people. Step-up refuses a principal's next
 * change until a person signs in again (or, for an agent, a person clears it).
 */
import { Transport } from "./http.js";
import type { AnomalySignal, ApprovalRequest, BlockedSet, DetectorName, DetectorSetting, OrgStatus } from "./types.js";

export class DetectorsClient {
  constructor(private readonly t: Transport) {}

  async settings(): Promise<{ detectors: Record<DetectorName, DetectorSetting>; defaults?: Record<DetectorName, DetectorSetting> }> {
    return this.t.get("/agp/detectors");
  }

  /** A two-person action (detector.settings): answers with the approval request; applies once two others approve. */
  async proposeSettings(detectors: Partial<Record<DetectorName, Partial<DetectorSetting>>>, requested_by: string): Promise<ApprovalRequest> {
    return this.t.put("/agp/detectors", { detectors, requested_by });
  }

  async signals(params: { detector?: DetectorName; principal_id?: string; limit?: number } = {}): Promise<{ items: AnomalySignal[] }> {
    return this.t.get("/agp/anomaly-signals", params);
  }

  async orgStatus(): Promise<OrgStatus> {
    return this.t.get("/agp/org-status");
  }

  /** Ask to bring a read-only org back: two of its people, or one of them and the hub operator (reinstated_by). */
  async askToReinstateOrg(reason: string, requested_by: string): Promise<ApprovalRequest> {
    return this.t.post("/agp/org-status", { status: "active", reason, requested_by });
  }

  /** Clear a principal's step-up: signed_in_again (a product, when the person signs in) or cleared_by_person. */
  async clearStepUp(principal_id: string, params: { how: "signed_in_again" | "cleared_by_person"; on_behalf_of?: string }): Promise<Record<string, unknown>> {
    return this.t.post(`/agp/principals/${encodeURIComponent(principal_id)}/step-up/clear`, params);
  }

  /** Everyone currently stopped (and the org's status) — read on connecting to the status stream, and as a backstop. */
  async blocked(): Promise<BlockedSet> {
    return this.t.get("/agp/principals-blocked");
  }

  /** The Server-Sent Events URL for status changes (GET, with the client's bearer token). */
  statusStreamUrl(): string {
    return `${this.t.baseUrl}/agp/status-stream`;
  }
}
