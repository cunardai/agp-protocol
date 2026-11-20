/**
 * AGP SDK — Policy Packs (AGP 1.0, spec/studio-extensions.md §7)
 *
 * A regulation, or an organisation's own standard, as one document of PolicySets for the rules engine. Official
 * packs ship with the server; an org publishes its own (a version never changes) and installs packs into its own
 * PolicySets. A verdict names the rule and cites the provisions it implements.
 */
import { Transport } from "./http.js";
import type { PackInstall, PolicyPackManifest, PolicyPackSummary } from "./types.js";

export class PacksClient {
  constructor(private readonly t: Transport) {}

  async list(): Promise<{ items: PolicyPackSummary[] }> {
    return this.t.get("/agp/packs");
  }

  async manifest(pack_id: string, version?: string): Promise<Record<string, unknown>> {
    return this.t.get("/agp/packs/manifest", { pack_id, ...(version ? { version } : {}) });
  }

  /** Publish for this org — a manifest object, or its YAML / JSON text. */
  async publish(manifest: PolicyPackManifest | string): Promise<Record<string, unknown>> {
    return this.t.post("/agp/packs", { manifest });
  }

  /** Its PolicySets made in this org (the latest version by default); the version it replaces is deprecated. */
  async install(pack_id: string, version?: string): Promise<PackInstall> {
    return this.t.post("/agp/packs/install", { pack_id, ...(version ? { version } : {}) });
  }

  /** It stops applying; its PolicySets are kept, deprecated, as the record of what applied when. */
  async uninstall(pack_id: string): Promise<PackInstall> {
    return this.t.post("/agp/packs/uninstall", { pack_id });
  }
}
