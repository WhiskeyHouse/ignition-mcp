"""Composite tools: several ign calls, one result. Python never touches a gateway."""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from ignition_mcp.ign import IgnBackend

PRIORITY_ORDER = ["Diagnostic", "Low", "Medium", "High", "Critical"]
HEALTHY_MODULE_STATES = frozenset({"ACTIVE", "RUNNING"})


def _rank(priority: str) -> int:
    """Index of `priority` in PRIORITY_ORDER, or -1 when unknown or blank."""
    try:
        return PRIORITY_ORDER.index(priority)
    except ValueError:
        return -1


class StepFailed(Exception):
    def __init__(self, step: str, envelope: dict[str, Any]) -> None:
        super().__init__(step)
        self.step = step
        self.envelope = envelope


class Runner:
    """Runs ign calls in order, records steps, stops on the first failure."""

    def __init__(self, backend: IgnBackend) -> None:
        self._backend = backend
        self.steps: list[dict[str, Any]] = []

    async def run(self, tool: str, args: dict[str, Any] | None = None) -> Any:
        env = await self._backend.call(tool, args)
        code = None if env.get("ok") else env.get("error", {}).get("code")
        self.steps.append({"tool": tool, "ok": bool(env.get("ok")), "code": code})
        if not env.get("ok"):
            raise StepFailed(tool, env)
        return env.get("data")

    def ok(self, **body: Any) -> ToolResult:
        return _result({"ok": True, "steps": self.steps, **body})

    def failed(self, exc: StepFailed, **body: Any) -> ToolResult:
        return _result(
            {"ok": False, "steps": self.steps, "step": exc.step, "error": exc.envelope, **body},
            is_error=True,
        )

    def refused(self, code: str, message: str, **body: Any) -> ToolResult:
        return self._synthetic(code, message, **body)

    def internal_error(self, exc: BaseException) -> ToolResult:
        """Last-resort result for a bug in a composite: still an envelope, never a raise."""
        return self._synthetic("internal_error", f"{type(exc).__name__}: {exc}")

    def _synthetic(self, code: str, message: str, **body: Any) -> ToolResult:
        env = {
            "ok": False,
            "profile": None,
            "error": {"code": code, "message": message, "endpoint": None, "hint": None},
        }
        return _result(
            {"ok": False, "steps": self.steps, "step": None, "error": env, **body}, is_error=True
        )


def _result(payload: dict[str, Any], is_error: bool = False) -> ToolResult:
    return ToolResult(content=json.dumps(payload), structured_content=payload, is_error=is_error)


def register_workflows(mcp: FastMCP, backend: IgnBackend) -> None:
    @mcp.tool
    async def diagnose_gateway() -> ToolResult:
        """Full gateway health read in one call: status, license, redundancy, GAN,
        connections, modules, doctor.

        Verdict is `down` when `status` itself fails, `degraded` when any later step
        fails or when any module reports a state outside {ACTIVE, RUNNING} or any
        database connection has `enabled: false`, and `healthy` otherwise."""
        r = Runner(backend)
        try:
            status = await r.run("status")
            license_ = await r.run("license_status")
            redundancy = await r.run("redundancy_status")
            gan = await r.run("gan_status")
            connections = await r.run("connections")
            modules = await r.run("modules")
            doctor = await r.run("doctor")
            module_items = modules.get("items", []) if isinstance(modules, dict) else []
            databases = connections.get("database", []) if isinstance(connections, dict) else []
            degraded = any(
                isinstance(m, dict)
                and m.get("state") is not None
                and m.get("state") not in HEALTHY_MODULE_STATES
                for m in module_items
            ) or any(isinstance(d, dict) and d.get("enabled") is False for d in databases)
            return r.ok(
                verdict="degraded" if degraded else "healthy",
                status=status,
                license=license_,
                redundancy=redundancy,
                gan=gan,
                connections=connections,
                modules=modules,
                doctor=doctor,
            )
        except StepFailed as e:
            return r.failed(e, verdict="down" if e.step == "status" else "degraded")
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def deploy_project(
        project: str,
        profile_a: str,
        profile_b: str,
        confirm: bool = False,
        delete: bool = False,
    ) -> ToolResult:
        """Promote `project` from gateway profile `profile_a` to `profile_b` via ign's
        project_sync. Refuses when the two profiles are already identical, and
        requires confirm: true to actually push (project_sync is destructive)."""
        r = Runner(backend)
        try:
            before = await r.run(
                "project_diff", {"profile_a": profile_a, "profile_b": profile_b, "project": project}
            )
            summary = before.get("summary", {})
            if summary.get("added", 0) + summary.get("changed", 0) + summary.get("removed", 0) == 0:
                return r.refused(
                    "nothing_to_promote",
                    f"{project} is identical on {profile_a} and {profile_b}",
                    summary=summary,
                )
            sync = await r.run(
                "project_sync",
                {
                    "profile_a": profile_a,
                    "profile_b": profile_b,
                    "project": project,
                    "all-changed": True,
                    "confirm": confirm,
                    "delete": delete,
                },
            )
            after = await r.run(
                "project_diff", {"profile_a": profile_a, "profile_b": profile_b, "project": project}
            )
            return r.ok(before=before, sync=sync, after=after)
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def rig_fresh(confirm: bool = False) -> ToolResult:
        """Tear down and bring up the active rig, then wait for the gateway:
        rig_down, rig_up, wait_gateway, status. Requires confirm: true.

        ign's `rig_down` verb is not itself guarded (unlike rig_reset,
        rig_restore, and rig_trial_reset), so this composite enforces its own
        confirmation gate before making any ign call, rather than forwarding
        `confirm` to rig_down."""
        r = Runner(backend)
        if not confirm:
            return r.refused(
                "confirmation_required",
                "rig_fresh is destructive (rig_down then rig_up); rerun with confirm: true",
            )
        try:
            await r.run("rig_down")
            await r.run("rig_up")
            await r.run("wait_gateway")
            status = await r.run("status")
            return r.ok(status=status)
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def tag_snapshot(path: str, max_depth: int = 3, max_tags: int = 500) -> ToolResult:
        """Browse under `path` (recursive, depth-limited) and read every atomic tag
        found, in one call. Recursion happens in Python: ign's tags_browse is not
        recursive."""
        r = Runner(backend)
        atomic: list[str] = []
        browsed = 0
        try:
            queue: list[tuple[str, int]] = [(path, 0)]
            while queue and len(atomic) < max_tags:
                current, depth = queue.pop(0)
                found = await r.run("tags_browse", {"path": current})
                browsed += 1
                for entry in found.get("entries", []):
                    tag_type = entry.get("tag_type")
                    if tag_type == "AtomicTag":
                        atomic.append(entry["path"])
                    elif (
                        entry.get("has_children")
                        and tag_type != "AtomicTag"
                        and depth + 1 < max_depth
                    ):
                        queue.append((entry["path"], depth + 1))
            atomic = atomic[:max_tags]
            tags = await r.run("tags_read", {"paths": atomic}) if atomic else {"results": []}
            return r.ok(
                root=path,
                browsed=browsed,
                tags=tags.get("results", []),
                truncated=len(atomic) >= max_tags,
            )
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def find_alarms(
        min_priority: str = "Diagnostic", path_contains: str | None = None
    ) -> ToolResult:
        """Active alarms filtered by minimum priority (Diagnostic|Low|Medium|High|Critical)
        and an optional source-path substring. Alarms whose priority is blank or
        unrecognised are kept only at the default `Diagnostic` floor."""
        r = Runner(backend)
        try:
            data = await r.run("tags_alarms_active")
            alarms = data.get("alarms", [])
            floor = _rank(min_priority)
            if floor < 0:
                floor = 0

            def keep(alarm: dict[str, Any]) -> bool:
                rank = _rank(alarm.get("priority", ""))
                if rank < floor and not (rank == -1 and floor == 0):
                    return False
                return path_contains is None or path_contains in alarm.get("source", "")

            kept = [a for a in alarms if keep(a)]
            return r.ok(alarms=kept, total=data.get("count", len(alarms)))
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)
