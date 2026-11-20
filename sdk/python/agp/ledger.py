"""
AGP SDK — the ledger (AGP 1.0): report a product's acts, read (masked), verify, checkpoints, evidence packs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .http import Transport


class LedgerClient:
    def __init__(self, transport: Transport):
        self._t = transport

    def report(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Acts a product reports (POST /agp/events): AGP sets the actor, the org and source "reported".
        Each needs a client_event_id (a retry records it once); batched by 500."""
        now = datetime.now(timezone.utc).isoformat()
        stamped = [{"client_event_id": str(uuid.uuid4()), "observed_at": now, **e} for e in events]
        out: dict[str, Any] = {"recorded": 0, "duplicates": 0, "event_ids": []}
        for i in range(0, len(stamped), 500):
            r = self._t.post("/agp/events", {"events": stamped[i:i + 500]})
            out["recorded"] += r["recorded"]; out["duplicates"] += r["duplicates"]; out["event_ids"] += r["event_ids"]
        return out

    def events(self, *, task_id: str | None = None, outcome: str | None = None, limit: int | None = None,
               cursor: str | None = None, order: str | None = None, raw: bool = False) -> dict[str, Any]:
        """Masked as read; raw=True needs agp.execution.admin. order="desc" for the newest first."""
        params = {k: v for k, v in {"task_id": task_id, "outcome": outcome, "limit": limit, "cursor": cursor,
                                    "order": order, "raw": "true" if raw else None}.items() if v is not None}
        return self._t.get("/agp/ledger-events", params=params)

    def verify(self) -> dict[str, Any]:
        return self._t.get("/agp/ledger/verify")

    def checkpoint_key(self) -> dict[str, Any]:
        return self._t.get("/agp/ledger/checkpoint-key")

    def seal(self) -> dict[str, Any]:
        return self._t.post("/agp/ledger/checkpoints", {})

    def checkpoints(self) -> dict[str, Any]:
        return self._t.get("/agp/ledger/checkpoints")

    def verify_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        return self._t.get(f"/agp/ledger/checkpoints/{checkpoint_id}/verify")

    def evidence_pack(self, *, from_: str | None = None, to: str | None = None) -> tuple[bytes, str | None]:
        """The org's range as a zip an auditor checks offline (its own verify.py inside)."""
        return self._t.get_file("/agp/ledger/evidence", params={k: v for k, v in {"from": from_, "to": to}.items() if v})
