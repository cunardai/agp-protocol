/**
 * AGP SDK — Exception hierarchy
 *
 * Maps HTTP status codes + AGP error codes to typed Error subclasses.
 */

export class AGPError extends Error {
  readonly code: string;
  readonly http_status: number | undefined;
  readonly retryable: boolean;

  constructor(message: string, options: {
    code?: string;
    http_status?: number;
    retryable?: boolean;
  } = {}) {
    super(message);
    this.name = "AGPError";
    this.code = options.code ?? "AGP_ERROR";
    this.http_status = options.http_status;
    this.retryable = options.retryable ?? false;
  }
}

export class AGPNotFoundError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_NOT_FOUND", http_status: 404 });
    this.name = "AGPNotFoundError";
  }
}

export class AGPBadRequestError extends AGPError {
  constructor(message: string, code = "AGP_INVALID_REQUEST") {
    super(message, { code, http_status: 400 });
    this.name = "AGPBadRequestError";
  }
}

export class AGPConflictError extends AGPError {
  constructor(message: string, code = "AGP_CONFLICT") {
    super(message, { code, http_status: 409 });
    this.name = "AGPConflictError";
  }
}

export class AGPUnprocessableError extends AGPError {
  constructor(message: string, code = "AGP_INVALID_REQUEST") {
    super(message, { code, http_status: 422 });
    this.name = "AGPUnprocessableError";
  }
}

export class AGPPolicyDeniedError extends AGPUnprocessableError {
  constructor(message: string) {
    super(message, "AGP_POLICY_DENIED");
    this.name = "AGPPolicyDeniedError";
  }
}

export class AGPTokenRevokedError extends AGPUnprocessableError {
  constructor(message: string) {
    super(message, "AGP_TOKEN_REVOKED");
    this.name = "AGPTokenRevokedError";
  }
}

export class AGPTokenExpiredError extends AGPUnprocessableError {
  constructor(message: string) {
    super(message, "AGP_TOKEN_EXPIRED");
    this.name = "AGPTokenExpiredError";
  }
}

export class AGPApprovalRequiredError extends AGPUnprocessableError {
  constructor(message: string) {
    super(message, "AGP_APPROVAL_REQUIRED");
    this.name = "AGPApprovalRequiredError";
  }
}

export class AGPServerError extends AGPError {
  constructor(message: string, http_status = 500) {
    super(message, { code: "AGP_SERVER_ERROR", http_status, retryable: true });
    this.name = "AGPServerError";
  }
}

export class AGPConnectionError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_CONNECTION_ERROR", retryable: true });
    this.name = "AGPConnectionError";
  }
}

export class AGPUnauthorizedError extends AGPError {
  constructor(message: string, code = "AGP_UNAUTHORIZED") {
    super(message, { code, http_status: 401 });
    this.name = "AGPUnauthorizedError";
  }
}

export class AGPForbiddenError extends AGPError {
  constructor(message: string, code = "AGP_FORBIDDEN") {
    super(message, { code, http_status: 403 });
    this.name = "AGPForbiddenError";
  }
}

/** A principal (or whom it acts for) is restricted, suspended or revoked — or, when the register is
 *  required, not registered (AGP_PRINCIPAL_UNKNOWN). */
export class AGPPrincipalBlockedError extends AGPForbiddenError {
  constructor(message: string, code = "AGP_PRINCIPAL_BLOCKED") {
    super(message, code);
    this.name = "AGPPrincipalBlockedError";
  }
}

/** A record that can't be written twice (decisions, approvals, receipts, revocations…). */
export class AGPImmutableError extends AGPConflictError {
  constructor(message: string) {
    super(message, "AGP_IMMUTABLE");
    this.name = "AGPImmutableError";
  }
}

/** The ledger couldn't record the act, so it wasn't carried out (fail closed). Retry. */
export class AGPLedgerUnavailableError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_LEDGER_UNAVAILABLE", http_status: 503, retryable: true });
    this.name = "AGPLedgerUnavailableError";
  }
}

/** The server has no auth configured, so it refuses everything (it fails closed). */
export class AGPAuthNotConfiguredError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_AUTH_NOT_CONFIGURED", http_status: 503 });
    this.name = "AGPAuthNotConfiguredError";
  }
}

/** 423 — the org is read-only (an integrity failure): writes refused until people reinstate it. */
export class AGPOrgReadOnlyError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_ORG_READ_ONLY", http_status: 423 });
    this.name = "AGPOrgReadOnlyError";
  }
}

/** 429 — too many requests; retry after the server's Retry-After. */
export class AGPRateLimitedError extends AGPError {
  constructor(message: string) {
    super(message, { code: "AGP_RATE_LIMITED", http_status: 429, retryable: true });
    this.name = "AGPRateLimitedError";
  }
}

/** 422 — a tainted attested context blocks the gate until its trust is promoted (§8.4). */
export class AGPTaintDetectedError extends AGPUnprocessableError {
  constructor(message: string) {
    super(message, "AGP_TAINT_DETECTED");
    this.name = "AGPTaintDetectedError";
  }
}

// ── Error code → class mapping ───────────────────────────────────────────────

const CODE_MAP: Record<string, (msg: string) => AGPError> = {
  AGP_NOT_FOUND:          (m) => new AGPNotFoundError(m),
  AGP_POLICY_DENIED:      (m) => new AGPPolicyDeniedError(m),
  AGP_TOKEN_REVOKED:      (m) => new AGPTokenRevokedError(m),
  AGP_TOKEN_EXPIRED:      (m) => new AGPTokenExpiredError(m),
  AGP_APPROVAL_REQUIRED:  (m) => new AGPApprovalRequiredError(m),
  AGP_SCOPE_VIOLATION:    (m) => new AGPConflictError(m, "AGP_SCOPE_VIOLATION"),
  AGP_IMMUTABLE:          (m) => new AGPImmutableError(m),
  AGP_PRINCIPAL_BLOCKED:  (m) => new AGPPrincipalBlockedError(m),
  AGP_PRINCIPAL_UNKNOWN:  (m) => new AGPPrincipalBlockedError(m, "AGP_PRINCIPAL_UNKNOWN"),
  AGP_LEDGER_UNAVAILABLE: (m) => new AGPLedgerUnavailableError(m),
  AGP_AUTH_NOT_CONFIGURED:(m) => new AGPAuthNotConfiguredError(m),
  AGP_ORG_READ_ONLY:      (m) => new AGPOrgReadOnlyError(m),
  AGP_RATE_LIMITED:       (m) => new AGPRateLimitedError(m),
  AGP_TAINT_DETECTED:     (m) => new AGPTaintDetectedError(m),
};

const STATUS_MAP: Record<number, (msg: string, code: string) => AGPError> = {
  400: (m, c) => new AGPBadRequestError(m, c),
  401: (m, c) => new AGPUnauthorizedError(m, c),
  403: (m, c) => new AGPForbiddenError(m, c),
  404: (m)    => new AGPNotFoundError(m),
  409: (m, c) => new AGPConflictError(m, c),
  422: (m, c) => new AGPUnprocessableError(m, c),
  423: (m)    => new AGPOrgReadOnlyError(m),
  429: (m)    => new AGPRateLimitedError(m),
};

export function raiseForResponse(
  status: number,
  body: Record<string, unknown>,
): never {
  // AGP errors are {error: {code, message}}; OAuth's token endpoint answers {error: "<code>", error_description}.
  const raw = body["error"];
  const error = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, string>;
  const code    = error["code"]    ?? (typeof raw === "string" ? raw : "AGP_ERROR");
  const message = error["message"] ?? (body["error_description"] as string | undefined) ?? `HTTP ${status}`;

  if (code in CODE_MAP) {
    throw CODE_MAP[code]!(message);
  }
  if (status in STATUS_MAP) {
    throw STATUS_MAP[status]!(message, code);
  }
  if (status >= 500) {
    throw new AGPServerError(message, status);
  }
  throw new AGPError(message, { code, http_status: status });
}
