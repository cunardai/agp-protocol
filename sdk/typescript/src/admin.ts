/**
 * AGP SDK — clients, provisioning and object history
 */
import { Transport } from "./http.js";
import type { OAuthClient, ObjectVersion } from "./types.js";

export class AdminClient {
  constructor(private readonly t: Transport) {}

  async listClients(): Promise<{ items: OAuthClient[] }> {
    return this.t.get("/agp/auth/clients");
  }

  /** A client in your org. The secret is returned once. */
  async registerClient(params: { client_id: string; scopes: string[]; client_secret?: string; description?: string }): Promise<OAuthClient & { client_secret: string }> {
    return this.t.post("/agp/auth/clients", params);
  }

  /** Deleting a client ends its tokens at once; its id is never reused. */
  async deleteClient(client_id: string): Promise<void> {
    await this.t.delete(`/agp/auth/clients/${encodeURIComponent(client_id)}`);
  }

  /** With agp.org.provision: the first client of an org that has none. One client per org keeps AGP's
   *  separation of orgs even against the product that hosts them. */
  async provisionOrgClient(org_id: string, params: { client_id: string; scopes: string[]; description?: string }): Promise<OAuthClient & { client_secret: string }> {
    return this.t.post(`/agp/orgs/${encodeURIComponent(org_id)}/clients`, params);
  }

  /** Every version of an object, oldest first, and whether its history holds. */
  async versions(resource_type: string, id: string): Promise<{ resource_type: string; id: string; write_once: boolean; verify: { ok: boolean }; items: ObjectVersion[] }> {
    return this.t.get(`/agp/versions/${encodeURIComponent(resource_type)}/${encodeURIComponent(id)}`);
  }
}
