"""
AGP SDK — Policy Packs (AGP 1.0, §7): a regulation or an organisation's own standard as PolicySets for the rules
engine. Official packs ship with the server; an org publishes its own (a version never changes) and installs packs
into its own PolicySets. A verdict names its rule and cites the provisions it implements.
"""
from __future__ import annotations

from typing import Any

from .http import Transport


class PacksClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def list(self) -> dict[str, Any]:
        return self._t.get("/agp/packs")

    def manifest(self, pack_id: str, version: str | None = None) -> dict[str, Any]:
        return self._t.get("/agp/packs/manifest", params={"pack_id": pack_id, **({"version": version} if version else {})})

    def publish(self, manifest: dict[str, Any] | str) -> dict[str, Any]:
        """A manifest (dict), or its YAML / JSON text."""
        return self._t.post("/agp/packs", {"manifest": manifest})

    def install(self, pack_id: str, version: str | None = None) -> dict[str, Any]:
        return self._t.post("/agp/packs/install", {"pack_id": pack_id, **({"version": version} if version else {})})

    def uninstall(self, pack_id: str) -> dict[str, Any]:
        """It stops applying; its PolicySets are kept, deprecated, as the record of what applied when."""
        return self._t.post("/agp/packs/uninstall", {"pack_id": pack_id})
