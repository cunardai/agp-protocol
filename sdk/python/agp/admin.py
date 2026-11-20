"""
AGP SDK — administration: OAuth clients (never more scopes than yours), provisioning an org's first client
(agp.org.provision), and an object's version history.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .http import Transport


class AdminClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def list_clients(self) -> dict[str, Any]:
        return self._t.get("/agp/auth/clients")

    def register_client(self, *, client_id: str, scopes: list[str], client_secret: str | None = None,
                        description: str | None = None) -> dict[str, Any]:
        """Its secret is in the answer only — keep it."""
        return self._t.post("/agp/auth/clients", {"client_id": client_id, "scopes": scopes,
                                                  **({"client_secret": client_secret} if client_secret else {}),
                                                  **({"description": description} if description else {})})

    def delete_client(self, client_id: str) -> dict[str, Any]:
        return self._t.delete(f"/agp/auth/clients/{quote(client_id, safe='')}")

    def provision_org_client(self, org_id: str, *, client_id: str, scopes: list[str], description: str | None = None) -> dict[str, Any]:
        """An org's first client — once (409 after)."""
        return self._t.post(f"/agp/orgs/{quote(org_id, safe='')}/clients",
                            {"client_id": client_id, "scopes": scopes, **({"description": description} if description else {})})

    def versions(self, resource_type: str, id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/versions/{resource_type}/{quote(id, safe='')}")
