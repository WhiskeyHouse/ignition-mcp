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
from mcp.shared.exceptions import MCPError
from mcp_types import CONNECTION_CLOSED, INVALID_PARAMS, REQUEST_TIMEOUT

from ignition_mcp.config import Settings

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
VERSION_TIMEOUT = 10.0
PING_TIMEOUT = 5.0

# `Client.call_tool` raises `MCPError` (fastmcp's `McpError`) both for a real
# JSON-RPC error response from a healthy child (e.g. unknown/invalid tool
# arguments) and for transport-level failures (request timeout, connection
# closed mid-call). Only the latter two codes mean the child may be dead and
# should go through `call()`'s restart path; every other `MCPError` code is a
# protocol-level error that must be reported back to the caller as-is.
_TRANSPORT_MCP_ERROR_CODES = frozenset({CONNECTION_CLOSED, REQUEST_TIMEOUT})

# Replaying a call whose `confirm` was true could execute a destructive
# operation twice, so the restart path never retries one.
DESTRUCTIVE_RETRY_HINT = (
    "the ign child died during a confirmed destructive call; the operation may "
    "have executed — inspect gateway/rig state before retrying"
)


class IgnUnavailable(RuntimeError):
    code = "ign_unavailable"


def parse_version(text: str) -> tuple[int, ...]:
    m = _VERSION_RE.search(text)
    if not m:
        raise IgnUnavailable(f"could not parse ign version from {text!r}")
    return tuple(int(g) for g in m.groups())


def _unavailable_envelope(message: str, hint: str | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "profile": None,
        "error": {"code": IgnUnavailable.code, "message": message, "endpoint": None, "hint": hint},
    }


def envelope_problem(env: Any) -> str | None:
    """Why `env` is not a well-formed ign envelope, or None when it is.

    Only the envelope's own frame is checked: `ok` must be a boolean and a
    failure must carry `error.code` and `error.message` as strings. `data` is
    ign's to shape and stays opaque here.
    """
    if not isinstance(env, dict):
        return f"top level is {type(env).__name__}, not an object"
    ok = env.get("ok")
    if not isinstance(ok, bool):
        return f"`ok` is {type(ok).__name__}, not a boolean"
    if ok:
        return None
    error = env.get("error")
    if not isinstance(error, dict):
        return f"`ok` is false but `error` is {type(error).__name__}, not an object"
    for field in ("code", "message"):
        if not isinstance(error.get(field), str):
            return f"`error.{field}` is {type(error.get(field)).__name__}, not a string"
    return None


def _protocol_error_envelope(exc: MCPError) -> dict[str, Any]:
    return {
        "ok": False,
        "profile": None,
        "error": {
            "code": "protocol_error",
            "message": str(exc),
            "endpoint": None,
            "hint": None,
        },
    }


def _invalid_arguments_envelope(exc: MCPError) -> dict[str, Any]:
    return {
        "ok": False,
        "profile": None,
        "error": {
            "code": "invalid_arguments",
            "message": f"{type(exc).__name__}: {exc}",
            "endpoint": None,
            "hint": "check the tool's inputSchema; ign rejected the arguments",
        },
    }


class IgnBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Client | None = None
        self._lock = asyncio.Lock()
        self._path: str | None = None
        self._gen = 0

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
        try:
            proc = await asyncio.create_subprocess_exec(
                path, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except (OSError, ValueError) as e:
            # Not executable, wrong architecture, not a real program: spawning
            # raises rather than returning a process.
            raise IgnUnavailable(
                f"could not execute ign at {path!r}: {type(e).__name__}: {e}"
            ) from e
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=VERSION_TIMEOUT)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise IgnUnavailable(
                f"ign --version timed out after {VERSION_TIMEOUT:g}s (IGN_BIN={path})"
            ) from None
        if proc.returncode != 0:
            raise IgnUnavailable(f"ign --version exited {proc.returncode} (IGN_BIN={path})")
        found = parse_version(out.decode())
        minimum = parse_version(self._settings.min_ign_version)
        if found < minimum:
            raise IgnUnavailable(
                f"ign {'.'.join(map(str, found))} is too old; need >= "
                f"{self._settings.min_ign_version} (IGN_BIN={path})"
            )
        self._path = path
        client = self._new_client()
        try:
            await client.__aenter__()
        except Exception as e:
            self._client = None
            with contextlib.suppress(Exception):
                await client.__aexit__(None, None, None)
            raise IgnUnavailable(
                f"ign mcp serve failed to start (IGN_BIN={path}): {type(e).__name__}: {e}"
            ) from e
        self._client = client
        self._gen += 1

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

    async def _rebuild_locked(self) -> None:
        """Replace the client with a fresh subprocess session. Caller holds `_lock`."""
        if self._path is None:
            raise IgnUnavailable("backend not started")
        await self._drop_client_for_restart()
        self._client = self._new_client()
        await self._client.__aenter__()
        self._gen += 1

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

    async def _is_alive(self) -> bool:
        """Is the ign child still answering? Caller holds `_lock`.

        `Client.is_connected()` only reports that a session object exists; it stays
        True after the subprocess dies while the session context is still held. A
        ping is the cheapest call that actually reaches the child, so it is the
        liveness signal.
        """
        if self._client is None or not self._client.is_connected():
            return False
        try:
            await asyncio.wait_for(self._client.ping(), timeout=PING_TIMEOUT)
        except Exception:
            return False
        return True

    async def acquire(self) -> Client:
        """Return a live client, rebuilding the ign session if the child has died.

        This is the proxy's `client_factory`: proxied tools go straight to the
        transport and never pass through `call()`, so this is their only crash
        recovery.
        """
        async with self._lock:
            if not await self._is_alive():
                await self._rebuild_locked()
            return self.client

    # -- calls ---------------------------------------------------------

    async def call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        gen = self._gen
        try:
            return await self._call_once(name, args or {})
        except IgnUnavailable:
            raise
        except MCPError as exc:
            if exc.code not in _TRANSPORT_MCP_ERROR_CODES:
                # A JSON-RPC error response from a healthy child: report it,
                # don't restart. Only -32602 means ign rejected the arguments;
                # any other code is a protocol-level fault of its own.
                if exc.code == INVALID_PARAMS:
                    return _invalid_arguments_envelope(exc)
                return _protocol_error_envelope(exc)
            return await self._restart_and_retry(name, args or {}, gen, exc)
        except Exception as exc:  # child died mid-session: restart once
            return await self._restart_and_retry(name, args or {}, gen, exc)

    async def _restart_and_retry(
        self, name: str, args: dict[str, Any], gen: int, first: BaseException
    ) -> dict[str, Any]:
        async with self._lock:
            if self._gen == gen:  # nobody else has rebuilt this session yet
                try:
                    await self._rebuild_locked()
                except Exception as e:  # pragma: no cover - defensive
                    return _unavailable_envelope(
                        f"ign restart failed: {type(e).__name__}: {e} "
                        f"(after: {type(first).__name__}: {first})"
                    )
        if args.get("confirm") is True:
            # The session is rebuilt so later calls work, but this one is not
            # replayed: the child may have died after ign acted on it.
            return _unavailable_envelope(
                f"ign died during a confirmed {name}: {type(first).__name__}: {first}",
                hint=DESTRUCTIVE_RETRY_HINT,
            )
        try:
            return await self._call_once(name, args)
        except Exception as second:
            return _unavailable_envelope(f"ign unavailable: {type(second).__name__}: {second}")

    async def _call_once(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            client = self.client
        result = await client.call_tool(name, args, raise_on_error=False)
        if result.content:
            text = getattr(result.content[0], "text", None)
            if text is None:
                return _unavailable_envelope(
                    "ign returned a non-envelope payload: "
                    f"{type(result.content[0]).__name__} block carries no text"
                )
        else:
            text = ""
        try:
            env = json.loads(text)
        except json.JSONDecodeError:
            return _unavailable_envelope(f"ign returned a non-envelope payload: {text[:200]!r}")
        problem = envelope_problem(env)
        if problem is not None:
            return _unavailable_envelope(
                f"ign returned a malformed envelope: {problem} ({text[:200]!r})"
            )
        return env
