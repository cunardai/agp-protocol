"""
Entry point: python -m agp_mcp

Supports two transports:
  stdio (default) — for Claude Desktop and local MCP hosts
  SSE             — for remote MCP hosts (pass --sse flag)
  Streamable HTTP — for HTTP-based MCP hosts (pass --http flag)

Environment variables:
  AGP_BASE_URL   AGP server URL (required)
  AGP_API_KEY    Bearer token (optional)
  AGP_TIMEOUT    HTTP timeout seconds (default: 30)
  MCP_PORT        Port for SSE/HTTP transports (default: 8100)
"""

from __future__ import annotations

import argparse
import asyncio
import os

from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AGP MCP server — exposes AGP governance tools to MCP clients",
    )
    transport_group = parser.add_mutually_exclusive_group()
    transport_group.add_argument(
        "--sse",
        action="store_true",
        help="Use SSE transport (for remote MCP hosts)",
    )
    transport_group.add_argument(
        "--http",
        action="store_true",
        help="Use Streamable HTTP transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8100")),
        help="Port for SSE/HTTP transport (default: 8100)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE/HTTP transport (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    if args.sse:
        asyncio.run(mcp.run_sse_async())
    elif args.http:
        asyncio.run(mcp.run_streamable_http_async())
    else:
        # stdio — default for Claude Desktop
        asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
