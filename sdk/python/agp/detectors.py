"""
AGP SDK — detectors (E2), the org's status, step-up, who's stopped (AGP 1.0, §4, §9).
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .http import Transport


class DetectorsClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def settings(self) -> dict[str, Any]:
        return self._t.get("/agp/detectors")

    def propose_settings(self, detectors: dict[str, dict[str, Any]], requested_by: str) -> dict[str, Any]:
        """A two-person action (detector.settings): answers with the approval request; applies once granted."""
        return self._t.put("/agp/detectors", {"detectors": detectors, "requested_by": requested_by})

    def signals(self, *, detector: str | None = None, principal_id: str | None = None, limit: int | None = None) -> dict[str, Any]:
        return self._t.get("/agp/anomaly-signals", params={k: v for k, v in {"detector": detector, "principal_id": principal_id, "limit": limit}.items() if v is not None})

    def org_status(self) -> dict[str, Any]:
        return self._t.get("/agp/org-status")

    def ask_to_reinstate_org(self, reason: str, requested_by: str) -> dict[str, Any]:
        """Two of the org's people — or one of them and the hub operator (see org_status()["reinstated_by"])."""
        return self._t.post("/agp/org-status", {"status": "active", "reason": reason, "requested_by": requested_by})

    def clear_step_up(self, principal_id: str, *, how: str, on_behalf_of: str | None = None) -> dict[str, Any]:
        """how: "signed_in_again" (a product, when the person signs in) or "cleared_by_person"."""
        return self._t.post(f"/agp/principals/{quote(principal_id, safe='')}/step-up/clear",
                            {"how": how, **({"on_behalf_of": on_behalf_of} if on_behalf_of else {})})

    def blocked(self) -> dict[str, Any]:
        return self._t.get("/agp/principals-blocked")

    def status_stream_url(self) -> str:
        """Server-Sent Events of status changes (GET, with the client's bearer token)."""
        return f"{self._t.base_url}/agp/status-stream"
