"""
§17 Authentication & Authorisation — AGP Conformance Tests

These tests verify the OAuth 2.0 client credentials flow and scope enforcement.

Auth is opt-in on the reference server — it is enabled by setting AGP_AUTH_SECRET.
When auth is disabled (no AGP_AUTH_SECRET), all requests pass through and these
tests are skipped automatically.

To run with auth enabled, start the server with:
    AGP_AUTH_SECRET=test-secret \\
    AGP_CLIENT_ID=conformance-client \\
    AGP_CLIENT_SECRET=conformance-secret \\
    uvicorn main:app --port 8099

Then run:
    pytest tests/test_09_auth.py --base-url=http://localhost:8099
"""
import pytest
import requests


# ── Helpers ───────────────────────────────────────────────────────────────────

TOKEN_ENDPOINT = "/oauth/token"
CLIENT_ID      = "conformance-client"
CLIENT_SECRET  = "conformance-secret"

ALL_SCOPES = [
    "agp.registry.read",
    "agp.registry.write",
    "agp.decision.read",
    "agp.decision.write",
    "agp.execution.read",
    "agp.execution.write",
    "agp.approval.write",
    "agp.policy.write",
    "agp.revocation.write",
]


def _token_request(base_url: str, **form_fields) -> requests.Response:
    return requests.post(
        f"{base_url}{TOKEN_ENDPOINT}",
        data={"grant_type": "client_credentials", **form_fields},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _auth_enabled(base_url: str) -> bool:
    """Return True if the server has auth enabled."""
    r = requests.get(f"{base_url}/agp/tasks")
    return r.status_code == 401


@pytest.fixture(scope="module", autouse=True)
def require_auth(base_url):
    """Skip the entire module if auth is not enabled on the server."""
    if not _auth_enabled(base_url):
        pytest.skip("Auth not enabled on this server (AGP_AUTH_SECRET not set)")


@pytest.fixture(scope="module")
def token(base_url) -> str:
    """Obtain a valid token for the conformance client."""
    r = _token_request(base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    assert r.status_code == 200, f"Could not obtain conformance token: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def authed(base_url, token) -> requests.Session:
    """A requests Session pre-loaded with a valid bearer token."""
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    s.headers["Content-Type"] = "application/json"
    return s


# ── §17.1 Token endpoint ──────────────────────────────────────────────────────

class TestTokenEndpoint:
    """§17.1 — POST /oauth/token"""

    def test_valid_credentials_return_200(self, base_url):
        """§17.1.1 — Valid client credentials return 200 with token response."""
        r = _token_request(base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        assert r.status_code == 200

    def test_response_shape(self, base_url):
        """§17.1.2 — Token response contains required RFC 6749 fields."""
        r = _token_request(base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        body = r.json()
        assert "access_token" in body
        assert body.get("token_type", "").lower() == "bearer"
        assert isinstance(body.get("expires_in"), int)
        assert body["expires_in"] > 0

    def test_scope_returned(self, base_url):
        """§17.1.3 — Token response includes granted scopes."""
        r = _token_request(base_url, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        body = r.json()
        assert "scope" in body
        granted = set(body["scope"].split())
        assert granted, "scope must be non-empty"

    def test_wrong_secret_returns_401(self, base_url):
        """§17.1.4 — Invalid client secret returns 401 invalid_client."""
        r = _token_request(base_url, client_id=CLIENT_ID, client_secret="wrong-secret")
        assert r.status_code == 401
        body = r.json()
        assert body.get("error") == "invalid_client"

    def test_unknown_client_returns_401(self, base_url):
        """§17.1.5 — Unknown client_id returns 401 invalid_client."""
        r = _token_request(base_url, client_id="nobody", client_secret="anything")
        assert r.status_code == 401
        body = r.json()
        assert body.get("error") == "invalid_client"

    def test_wrong_grant_type_returns_400(self, base_url):
        """§17.1.6 — Unsupported grant_type returns 400."""
        r = requests.post(
            f"{base_url}{TOKEN_ENDPOINT}",
            data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 400
        assert r.json().get("error") == "unsupported_grant_type"

    def test_scope_narrowing(self, base_url):
        """§17.1.7 — Requesting a subset of scopes returns only those scopes."""
        requested = "agp.registry.read agp.registry.write"
        r = _token_request(
            base_url,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope=requested,
        )
        assert r.status_code == 200
        granted = set(r.json()["scope"].split())
        assert granted == {"agp.registry.read", "agp.registry.write"}

    def test_invalid_scope_returns_400(self, base_url):
        """§17.1.8 — Requesting only unknown scopes returns 400 invalid_scope."""
        r = _token_request(
            base_url,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope="agp.does.not.exist",
        )
        assert r.status_code == 400
        assert r.json().get("error") == "invalid_scope"


# ── §17.2 Missing / malformed token → 401 ────────────────────────────────────

class TestUnauthorized:
    """§17.2 — Requests without a valid token are rejected with 401."""

    PROTECTED_ENDPOINTS = [
        ("GET",  "/agp/tasks"),
        ("GET",  "/agp/decision/contexts/ctx_missing"),
        ("GET",  "/agp/action-envelopes/act_missing"),
    ]

    def test_no_auth_header_returns_401(self, base_url):
        """§17.2.1 — Missing Authorization header returns 401."""
        r = requests.get(f"{base_url}/agp/tasks")
        assert r.status_code == 401

    def test_401_uses_agp_error_envelope(self, base_url):
        """§17.2.2 — 401 response uses AGP error envelope."""
        r = requests.get(f"{base_url}/agp/tasks")
        body = r.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_malformed_token_returns_401(self, base_url):
        """§17.2.3 — A malformed bearer token returns 401."""
        r = requests.get(
            f"{base_url}/agp/tasks",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert r.status_code == 401

    def test_wrong_scheme_returns_401(self, base_url):
        """§17.2.4 — Using Basic auth scheme instead of Bearer returns 401."""
        r = requests.get(
            f"{base_url}/agp/tasks",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert r.status_code == 401

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_protected_endpoints_require_auth(self, base_url, method, path):
        """§17.2.5 — All protected endpoints reject unauthenticated requests."""
        r = requests.request(method, f"{base_url}{path}")
        assert r.status_code == 401, f"{method} {path} should return 401 without auth"


# ── §17.3 Insufficient scope → 403 ───────────────────────────────────────────

class TestForbidden:
    """§17.3 — Valid token with missing scope returns 403."""

    def test_read_only_token_cannot_write(self, base_url):
        """§17.3.1 — Read-only token rejected on write endpoint."""
        r = _token_request(
            base_url,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope="agp.registry.read",
        )
        assert r.status_code == 200
        read_token = r.json()["access_token"]

        r = requests.post(
            f"{base_url}/agp/tasks",
            json={"principal_id": "agent-001", "principal_type": "autonomous_agent",
                  "operation_type": "data_read"},
            headers={"Authorization": f"Bearer {read_token}",
                     "Content-Type": "application/json"},
        )
        assert r.status_code == 403

    def test_403_uses_agp_error_envelope(self, base_url):
        """§17.3.2 — 403 response uses AGP error envelope."""
        r = _token_request(
            base_url,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope="agp.registry.read",
        )
        read_token = r.json()["access_token"]

        r = requests.post(
            f"{base_url}/agp/tasks",
            json={"principal_id": "agent-001"},
            headers={"Authorization": f"Bearer {read_token}",
                     "Content-Type": "application/json"},
        )
        assert r.status_code == 403
        body = r.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    def test_execution_scope_rejected_on_registry(self, base_url):
        """§17.3.3 — Execution scope token cannot access registry write."""
        r = _token_request(
            base_url,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scope="agp.execution.read agp.execution.write",
        )
        exec_token = r.json()["access_token"]

        r = requests.post(
            f"{base_url}/agp/tasks",
            json={"principal_id": "agent-001"},
            headers={"Authorization": f"Bearer {exec_token}",
                     "Content-Type": "application/json"},
        )
        assert r.status_code == 403


# ── §17.4 Authenticated requests succeed ─────────────────────────────────────

class TestAuthorizedAccess:
    """§17.4 — Valid token with correct scope allows access."""

    def test_authed_list_tasks_returns_200(self, base_url, authed):
        """§17.4.1 — GET /agp/tasks with valid token returns 200."""
        r = authed.get(f"{base_url}/agp/tasks")
        assert r.status_code == 200

    def test_authed_create_task_returns_201(self, base_url, authed):
        """§17.4.2 — POST /agp/tasks with valid token and scope returns 201."""
        r = authed.post(f"{base_url}/agp/tasks", json={
            "principal_id":      "conformance-agent",
            "requested_outcome": "auth conformance test",
            "risk_tier":         "low",
            "created_at":        "2024-01-01T00:00:00Z",
        })
        assert r.status_code == 201
        assert "task_id" in r.json()
