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

// ── Error code → class mapping ───────────────────────────────────────────────

const CODE_MAP: Record<string, (msg: string) => AGPError> = {
  AGP_NOT_FOUND:          (m) => new AGPNotFoundError(m),
  AGP_POLICY_DENIED:      (m) => new AGPPolicyDeniedError(m),
  AGP_TOKEN_REVOKED:      (m) => new AGPTokenRevokedError(m),
  AGP_TOKEN_EXPIRED:      (m) => new AGPTokenExpiredError(m),
  AGP_APPROVAL_REQUIRED:  (m) => new AGPApprovalRequiredError(m),
  AGP_SCOPE_VIOLATION:    (m) => new AGPConflictError(m, "AGP_SCOPE_VIOLATION"),
};

const STATUS_MAP: Record<number, (msg: string, code: string) => AGPError> = {
  400: (m, c) => new AGPBadRequestError(m, c),
  404: (m)    => new AGPNotFoundError(m),
  409: (m, c) => new AGPConflictError(m, c),
  422: (m, c) => new AGPUnprocessableError(m, c),
};

export function raiseForResponse(
  status: number,
  body: Record<string, unknown>,
): never {
  const error = (body["error"] as Record<string, string> | undefined) ?? {};
  const code    = error["code"]    ?? "AGP_ERROR";
  const message = error["message"] ?? `HTTP ${status}`;

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
