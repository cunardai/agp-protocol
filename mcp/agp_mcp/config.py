"""
AGP MCP — Configuration

Reads from environment variables so the server can be dropped into
any Claude Desktop / MCP host config without code changes.

Environment variables:
  AGP_BASE_URL   Base URL of the AGP governance server (required)
  AGP_API_KEY    Bearer token for authenticated servers (optional)
  AGP_TIMEOUT    HTTP timeout in seconds (default: 30)
"""

from __future__ import annotations

import os


class Config:
    base_url: str
    api_key: str | None
    timeout_ms: int

    def __init__(self) -> None:
        url = os.environ.get("AGP_BASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError(
                "AGP_BASE_URL environment variable is required. "
                "Set it to the URL of your AGP governance server, "
                "e.g. AGP_BASE_URL=http://localhost:8099"
            )
        self.base_url = url
        self.api_key = os.environ.get("AGP_API_KEY") or None
        self.timeout_ms = int(os.environ.get("AGP_TIMEOUT", "30")) * 1000

    @property
    def headers(self) -> dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}
