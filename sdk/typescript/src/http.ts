/**
 * AGP SDK — HTTP transport
 *
 * Uses the native fetch API (Node 18+). No external HTTP dependency.
 */

import { AGPConnectionError, raiseForResponse } from "./exceptions.js";

export interface TransportOptions {
  base_url: string;
  timeout_ms?: number;
  headers?: Record<string, string>;
  client_id?: string;
  client_secret?: string;
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function futureIso(days = 30): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

export class Transport {
  private readonly base: string;
  private readonly timeout: number;
  private readonly defaultHeaders: Record<string, string>;
  private readonly clientId?: string;
  private readonly clientSecret?: string;
  private token?: string;
  private tokenExp: number = 0;

  constructor(opts: TransportOptions) {
    this.base         = opts.base_url.replace(/\/$/, "");
    this.timeout      = opts.timeout_ms ?? 30_000;
    this.clientId     = opts.client_id;
    this.clientSecret = opts.client_secret;
    this.defaultHeaders = {
      "Content-Type": "application/json",
      ...opts.headers,
    };
  }

  // ── Token management ────────────────────────────────────────────────────

  private async authHeaders(): Promise<Record<string, string>> {
    if (!this.clientId) return {};
    if (Date.now() / 1000 >= this.tokenExp - 30) {
      await this.fetchToken();
    }
    return { Authorization: `Bearer ${this.token}` };
  }

  private async fetchToken(): Promise<void> {
    const body = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: this.clientId!,
      client_secret: this.clientSecret!,
    });
    const url = `${this.base}/oauth/token`;
    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });
    } catch (err) {
      throw new AGPConnectionError(err instanceof Error ? err.message : String(err));
    }
    if (!response.ok) {
      const detail = await response.json().catch(() => ({})) as Record<string, unknown>;
      throw new AGPConnectionError(
        `Token request failed (${response.status}): ${detail["error_description"] ?? JSON.stringify(detail)}`,
      );
    }
    const data = await response.json() as { access_token: string; expires_in?: number };
    this.token    = data.access_token;
    this.tokenExp = Date.now() / 1000 + (data.expires_in ?? 3600);
  }

  // ── Core verbs ─────────────────────────────────────────────────────────

  async post<T>(
    path: string,
    body: Record<string, unknown>,
    options: { idempotency_key?: string; prefer?: string } = {},
  ): Promise<T> {
    const headers: Record<string, string> = { ...this.defaultHeaders, ...await this.authHeaders() };
    if (options.idempotency_key) headers["Idempotency-Key"] = options.idempotency_key;
    if (options.prefer)          headers["Prefer"]          = options.prefer;
    return this._request<T>("POST", path, { headers, body });
  }

  async get<T>(
    path: string,
    params?: Record<string, string | number | boolean | undefined>,
  ): Promise<T> {
    const url = params ? `${path}?${this._buildQuery(params)}` : path;
    return this._request<T>("GET", url, { headers: { ...this.defaultHeaders, ...await this.authHeaders() } });
  }

  async patch<T>(
    path: string,
    body: Record<string, unknown>,
    options: { idempotency_key?: string } = {},
  ): Promise<T> {
    const headers: Record<string, string> = { ...this.defaultHeaders, ...await this.authHeaders() };
    if (options.idempotency_key) headers["Idempotency-Key"] = options.idempotency_key;
    return this._request<T>("PATCH", path, { headers, body });
  }

  // ── Internal ───────────────────────────────────────────────────────────

  private async _request<T>(
    method: string,
    path: string,
    opts: { headers: Record<string, string>; body?: Record<string, unknown> },
  ): Promise<T> {
    const url = `${this.base}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: opts.headers,
        body: opts.body != null ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        throw new AGPConnectionError(`Request timed out after ${this.timeout}ms`);
      }
      throw new AGPConnectionError(
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      clearTimeout(timer);
    }

    const json = await response.json().catch(() => ({})) as Record<string, unknown>;

    if (!response.ok) {
      raiseForResponse(response.status, json);
    }

    return json as T;
  }

  private _buildQuery(
    params: Record<string, string | number | boolean | undefined>,
  ): string {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) q.set(k, String(v));
    }
    return q.toString();
  }
}
