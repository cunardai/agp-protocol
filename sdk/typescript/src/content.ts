/**
 * AGP SDK — kept prompts and answers
 *
 * Kept in full apart from the ledger, with the org's retention; the ledger keeps only their hashes.
 * contentRef() computes the id and hash AGP will give text, so an event can name the content before it's
 * stored. Send text you serialised yourself: AGP hashes a string's UTF-8 bytes as they are.
 */
import { Transport } from "./http.js";
import type { ContentItem, KeptContent, StoredContent } from "./types.js";

async function sha256Hex(s: string): Promise<string> {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("");
}

/** The id and hashes AGP gives a text — cut to maxBytes (default 4 MB) when longer, with the whole's hash. */
export async function contentRef(text: string, maxBytes = 4 * 1024 * 1024): Promise<{ data: string; content_id: string; sha256: string; full_sha256: string; truncated: boolean }> {
  const full = `sha256:${await sha256Hex(text)}`;
  const bytes = new TextEncoder().encode(text);
  const data = bytes.length > maxBytes ? new TextDecoder().decode(bytes.subarray(0, Math.max(0, maxBytes - 4))) : text;
  const h = `sha256:${await sha256Hex(data)}`;
  return { data, content_id: `c_${h.slice(7, 47)}`, sha256: h, full_sha256: full, truncated: data !== text };
}

export class ContentClient {
  constructor(private readonly t: Transport) {}

  async store(items: ContentItem[]): Promise<{ stored: StoredContent[] }> {
    return this.t.post("/agp/content", { items });
  }

  /** Needs agp.content.read; the read is on the ledger. */
  async get(content_id: string): Promise<KeptContent> {
    return this.t.get(`/agp/content/${encodeURIComponent(content_id)}`);
  }

  async retention(): Promise<{ org_id: string; days: number }> {
    return this.t.get("/agp/content-retention");
  }

  async setRetention(days: number): Promise<{ org_id: string; days: number }> {
    return this.t.put("/agp/content-retention", { days });
  }
}
