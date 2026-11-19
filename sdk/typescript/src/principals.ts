/**
 * AGP SDK — the principal register (E1)
 *
 * Who acts, for whom, and whether they may. A status follows acting_for: suspend a person and everything
 * acting for them stops. Reinstating a person takes two different admins — a product signing in for all
 * its admins with one client names the admin acting (on_behalf_of).
 */
import { Transport } from "./http.js";
import type { Principal, PrincipalKind, PrincipalStatus } from "./types.js";

export class PrincipalsClient {
  constructor(private readonly t: Transport) {}

  async register(params: { principal_id: string; kind: PrincipalKind; display?: string; acting_for?: string;
                           risk_tier?: string; client_id?: string; external_ref?: string }): Promise<Principal> {
    return this.t.post("/agp/principals", params);
  }

  async get(principal_id: string): Promise<Principal> {
    return this.t.get(`/agp/principals/${encodeURIComponent(principal_id)}`);
  }

  async list(params: { kind?: PrincipalKind; status?: PrincipalStatus; acting_for?: string; limit?: number; cursor?: string } = {}): Promise<{ items: Principal[] }> {
    return this.t.get("/agp/principals", params);
  }

  async history(principal_id: string): Promise<{ principal_id: string; verify: { ok: boolean }; items: Record<string, unknown>[] }> {
    return this.t.get(`/agp/principals/${encodeURIComponent(principal_id)}/history`);
  }

  /** Restrict, suspend, revoke or reinstate. A person's reinstatement answers { pending: true } until a
   *  second, different admin asks too. */
  async setStatus(principal_id: string, params: { status: PrincipalStatus; reason: string; on_behalf_of?: string }): Promise<Principal & { pending?: boolean }> {
    return this.t.post(`/agp/principals/${encodeURIComponent(principal_id)}/status`, params);
  }
}
