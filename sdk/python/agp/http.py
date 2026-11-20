"""
AGP SDK — HTTP transport layer

Thin wrapper around httpx with:
- Automatic AGP error envelope parsing and exception raising
- Idempotency-Key header injection
- OAuth 2.0 client_credentials token fetch and caching
- Configurable timeouts and retries
"""
from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from .exceptions import AGPConnectionError, raise_for_response


class Transport:
    """
    Synchronous HTTP client. Wraps httpx.Client.

    Usage (unauthenticated):
        t = Transport("http://localhost:8099")

    Usage (OAuth client credentials):
        t = Transport("http://localhost:8099",
                      client_id="my-agent", client_secret="s3cr3t")
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_exp: float = 0.0

        self._client = httpx.Client(
            base_url=self._base,
            timeout=timeout,
            headers={"Content-Type": "application/json", **(headers or {})},
        )

    # ── Token management ──────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        if not self._client_id:
            return {}
        if time.time() >= self._token_exp - 30:
            self._fetch_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _fetch_token(self) -> None:
        try:
            r = self._client.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        if not r.is_success:
            body = r.json() if r.content else {}
            raise AGPConnectionError(
                f"Token request failed ({r.status_code}): {body.get('error_description', body)}"
            )
        data = r.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + data.get("expires_in", 3600)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Transport":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Core verbs ────────────────────────────────────────────────────────

    def post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        prefer: str | None = None,
        expected_status: int = 201,
        allow_status: tuple[int, ...] = (),
    ) -> dict[str, Any]:
        headers: dict[str, str] = {**self._auth_headers()}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if prefer:
            headers["Prefer"] = prefer
        try:
            r = self._client.post(path, json=body, headers=headers)
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        if r.status_code not in allow_status:       # a status the caller reads itself (a capability DENY)
            self._raise_if_error(r)
        return r.json()

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            r = self._client.put(path, json=body, headers=self._auth_headers())
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        self._raise_if_error(r)
        return r.json()

    def delete(self, path: str) -> dict[str, Any]:
        try:
            r = self._client.delete(path, headers=self._auth_headers())
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        self._raise_if_error(r)
        return r.json() if r.content else {}

    def get_file(self, path: str, *, params: dict[str, Any] | None = None) -> tuple[bytes, str | None]:
        """A download (an evidence pack): its bytes and the filename the server gave it."""
        try:
            r = self._client.get(path, params=params, headers=self._auth_headers())
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        self._raise_if_error(r)
        import re
        m = re.search(r'filename="([^"]+)"', r.headers.get("content-disposition", ""))
        return r.content, (m.group(1) if m else None)

    @property
    def base_url(self) -> str:
        return self._base

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            r = self._client.get(path, params=params, headers=self._auth_headers())
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        self._raise_if_error(r)
        return r.json()

    def patch(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {**self._auth_headers()}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        try:
            r = self._client.patch(path, json=body, headers=headers)
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        self._raise_if_error(r)
        return r.json()

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(r: httpx.Response) -> None:
        if r.is_success:
            return
        try:
            body = r.json()
        except Exception:
            body = {"error": {"code": "AGP_ERROR", "message": r.text}}
        raise_for_response(r.status_code, body)


class AsyncTransport:
    """
    Async HTTP client. Wraps httpx.AsyncClient.

    Usage:
        async with AsyncTransport("http://localhost:8099") as t:
            body = await t.post("/agp/tasks", {...})
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base,
            timeout=timeout,
            headers={"Content-Type": "application/json", **(headers or {})},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTransport":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        prefer: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if prefer:
            headers["Prefer"] = prefer
        try:
            r = await self._client.post(path, json=body, headers=headers)
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        Transport._raise_if_error(r)
        return r.json()

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            r = await self._client.get(path, params=params)
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        Transport._raise_if_error(r)
        return r.json()

    async def patch(
        self,
        path: str,
        body: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        try:
            r = await self._client.patch(path, json=body, headers=headers)
        except httpx.ConnectError as e:
            raise AGPConnectionError(str(e)) from e
        Transport._raise_if_error(r)
        return r.json()


def new_idempotency_key() -> str:
    return uuid.uuid4().hex
