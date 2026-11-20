"""
AGP SDK — the principal register (E1): who acts, for whom, and whether they may. A status follows acting_for:
suspend a person and everything acting for them stops. Reinstating a person takes two different admins.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .http import Transport


class PrincipalsClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def register(self, *, principal_id: str, kind: str, display: str | None = None, acting_for: str | None = None,
                 **extra: Any) -> dict[str, Any]:
        body = {"principal_id": principal_id, "kind": kind, **({"display": display} if display else {}),
                **({"acting_for": acting_for} if acting_for else {}), **extra}
        return self._t.post("/agp/principals", body)

    def get(self, principal_id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/principals/{quote(principal_id, safe='')}")

    def list(self, **params: Any) -> dict[str, Any]:
        return self._t.get("/agp/principals", params={k: v for k, v in params.items() if v is not None})

    def history(self, principal_id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/principals/{quote(principal_id, safe='')}/history")

    def set_status(self, principal_id: str, *, status: str, reason: str, on_behalf_of: str | None = None) -> dict[str, Any]:
        """Restrict, suspend, revoke or reinstate. A person's reinstatement answers pending until a second admin asks."""
        return self._t.post(f"/agp/principals/{quote(principal_id, safe='')}/status",
                            {"status": status, "reason": reason, **({"on_behalf_of": on_behalf_of} if on_behalf_of else {})})
