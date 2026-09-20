"""The one seam to `ign`: version probe, a shared stdio session, and `call()`."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from ignition_mcp.config import Settings

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class IgnUnavailable(RuntimeError):
    code = "ign_unavailable"


def parse_version(text: str) -> tuple[int, ...]:
    m = _VERSION_RE.search(text)
    if not m:
        raise IgnUnavailable(f"could not parse ign version from {text!r}")
    return tuple(int(g) for g in m.groups())


def _unavailable_envelope(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "profile": None,
        "error": {"code": IgnUnavailable.code, "message": message, "endpoint": None, "hint": None},
    }


class IgnBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    # -- lifecycle -----------------------------------------------------

    async def start(self) -> None:
        path = shutil.which(self._settings.ign_bin) or (
            self._settings.ign_bin if os.path.isfile(self._settings.ign_bin) else None
        )
        if path is None:
            raise IgnUnavailable(
                f"ign binary not found at {self._settings.ign_bin!r}; "
                "set IGN_BIN or add ign to PATH"
            )
        proc = await asyncio.create_subprocess_exec(
            path, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        found = parse_version(out.decode())
        minimum = parse_version(self._settings.min_ign_version)
        if found < minimum:
            raise IgnUnavailable(
                f"ign {'.'.join(map(str, found))} is too old; need >= "
                f"{self._settings.min_ign_version} (IGN_BIN={path})"
            )
        self._path = path
        self._client = self._new_client()
        await self._client.__aenter__()

    async def stop(self) -> None:
        if self._client is not None:
            old, self._client = self._client, None
            await old.__aexit__(None, None, None)

    async def _drop_client_for_restart(self) -> None:
        """Discard the (presumably dead) client without letting teardown raise.

        Used only from the restart path in `call()`, which must never let a
        transport-teardown exception escape and break the envelope contract.
        """
        old, self._client = self._client, None
        if old is not None:
            with contextlib.suppress(Exception):
                await old.__aexit__(None, None, None)

    def _new_client(self) -> Client:
        args: list[str] = []
        if self._settings.profile:
            args += ["--profile", self._settings.profile]
        args += ["mcp", "serve"]
        return Client(StdioTransport(command=self._path, args=args, env=dict(os.environ)))

    @property
    def client(self) -> Client:
        if self._client is None:
            raise IgnUnavailable("backend not started")
        return self._client

    # -- calls ---------------------------------------------------------

    async def call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return await self._call_once(name, args or {})
        except IgnUnavailable:
            raise
        except Exception as first:  # child died mid-session: restart once
            async with self._lock:
                await self._drop_client_for_restart()
                try:
                    self._client = self._new_client()
                    await self._client.__aenter__()
                except Exception as e:  # pragma: no cover - defensive
                    return _unavailable_envelope(
                        f"ign restart failed: {type(e).__name__}: {e} "
                        f"(after: {type(first).__name__}: {first})"
                    )
            try:
                return await self._call_once(name, args or {})
            except Exception as second:
                return _unavailable_envelope(f"ign unavailable: {type(second).__name__}: {second}")

    async def _call_once(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            client = self.client
        result = await client.call_tool(name, args, raise_on_error=False)
        text = result.content[0].text if result.content else ""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return _unavailable_envelope(f"ign returned a non-envelope payload: {text[:200]!r}")
