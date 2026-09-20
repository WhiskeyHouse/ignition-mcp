"""`ign-mcp` entrypoint. Local development only: no auth, loopback by default."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ignition_mcp.config import Settings
from ignition_mcp.ign import IgnBackend, IgnUnavailable
from ignition_mcp.server import build_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="ign-mcp", description="HTTP MCP front for `ign mcp serve`")
    p.add_argument("--host", help="bind host (default 127.0.0.1; keep loopback, there is no auth)")
    p.add_argument("--port", type=int, help="bind port (default 8765)")
    p.add_argument("--stdio", action="store_true", help="serve over stdio instead of HTTP")
    p.add_argument(
        "--profile", help="ign profile to serve (default: IGNITION_PROFILE / ign's active)"
    )
    p.add_argument("--ign-bin", help="path to the ign binary (default: IGN_BIN or `ign` on PATH)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    ns = parse_args(argv)
    overrides = {k: v for k, v in vars(ns).items() if v is not None and k != "stdio"}
    settings = Settings(**overrides)

    async def run() -> None:
        backend = IgnBackend(settings)
        try:
            await backend.start()
        except IgnUnavailable as e:
            print(f"ign-mcp: {e}", file=sys.stderr)
            raise SystemExit(1)
        server = build_server(settings, backend)
        try:
            if ns.stdio:
                await server.run_async(transport="stdio")
            else:
                await server.run_async(transport="http", host=settings.host, port=settings.port)
        finally:
            await backend.stop()

    asyncio.run(run())
