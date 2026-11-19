/**
 * AGP SDK — the ledger (v0.9 studio profile)
 *
 *   report(events)         acts a product reports; AGP names the actor (the token's client), never the body
 *   verify()               do the org's chains and signed checkpoints hold
 *   seal() / checkpoints() / verifyCheckpoint(id) / checkpointKey()
 *   evidencePack({from,to}) a zip an auditor checks offline with its verify.py
 */
import { Transport } from "./http.js";
import type { Checkpoint, CheckpointKey, EventLedgerRecord, LedgerVerification, ReportedEvent } from "./types.js";

export class LedgerClient {
  constructor(private readonly t: Transport) {}

  /** Report acts (≤ 500 per call; split larger batches). Each gets a client_event_id if it has none, so a
   *  retried batch is recorded once. All are checked before any is written. */
  async report(events: ReportedEvent[]): Promise<{ recorded: number; duplicates: number; event_ids: string[] }> {
    const stamped = events.map(e => ({ ...e, client_event_id: e.client_event_id ?? crypto.randomUUID(), observed_at: e.observed_at ?? new Date().toISOString() }));
    const out = { recorded: 0, duplicates: 0, event_ids: [] as string[] };
    for (let i = 0; i < stamped.length; i += 500) {
      const r = await this.t.post<typeof out>("/agp/events", { events: stamped.slice(i, i + 500) });
      out.recorded += r.recorded; out.duplicates += r.duplicates; out.event_ids.push(...r.event_ids);
    }
    return out;
  }

  async events(params: { task_id?: string; outcome?: string; limit?: number; cursor?: string } = {}): Promise<{ items: EventLedgerRecord[] }> {
    return this.t.get("/agp/ledger-events", params);
  }

  async verify(): Promise<LedgerVerification> {
    return this.t.get("/agp/ledger/verify");
  }

  async checkpointKey(): Promise<CheckpointKey> {
    return this.t.get("/agp/ledger/checkpoint-key");
  }

  /** Seal the ledger now (normally hourly). { skipped } when there's nothing new. */
  async seal(): Promise<Checkpoint | { skipped: string }> {
    return this.t.post("/agp/ledger/checkpoints", {});
  }

  async checkpoints(): Promise<{ items: Checkpoint[] }> {
    return this.t.get("/agp/ledger/checkpoints");
  }

  async verifyCheckpoint(checkpoint_id: string): Promise<Record<string, unknown>> {
    return this.t.get(`/agp/ledger/checkpoints/${encodeURIComponent(checkpoint_id)}/verify`);
  }

  /** The evidence pack for a period: a zip of the events, signed checkpoints, signed manifest and verify.py. */
  async evidencePack(params: { from?: string; to?: string } = {}): Promise<{ bytes: ArrayBuffer; filename: string | null }> {
    return this.t.getFile("/agp/ledger/evidence", params);
  }
}
