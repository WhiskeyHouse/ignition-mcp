"""Composite tools: several ign calls, one result. Python never touches a gateway."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from ignition_mcp.ign import IgnBackend

PRIORITY_ORDER = ["Diagnostic", "Low", "Medium", "High", "Critical"]
HEALTHY_MODULE_STATES = frozenset({"ACTIVE", "RUNNING"})
FAILED_DOCTOR_STATUS = "Fail"
BASELINE_NOTE = (
    "ign does not advance the workspace baseline on push; pushed members now read as "
    "`conflict` in workspace_status until you re-run `ign workspace checkout` for this "
    "project. Run push_workspace again only after a fresh checkout."
)
LOCAL_DELETE = {"deleted": {"local": True}}


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
        fails, when any module reports a state outside {ACTIVE, RUNNING}, when any
        database connection has `enabled: false`, or when any doctor check reports
        status `Fail`, and `healthy` otherwise."""
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
            checks = doctor.get("checks", []) if isinstance(doctor, dict) else []
            degraded = (
                any(
                    isinstance(m, dict)
                    and m.get("state") is not None
                    and m.get("state") not in HEALTHY_MODULE_STATES
                    for m in module_items
                )
                or any(isinstance(d, dict) and d.get("enabled") is False for d in databases)
                or any(
                    isinstance(c, dict) and c.get("status") == FAILED_DOCTOR_STATUS for c in checks
                )
            )
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
        requires confirm: true to actually push (project_sync is destructive).

        The second project_diff is a verification, not a report: resources still
        added or changed on `profile_b` mean the sync did not land, and the result
        is `verification_failed`. Resources only left over on `profile_b` are
        reported as `pending_removals`, since removing them needs delete: true."""
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
            after_summary = after.get("summary", {}) if isinstance(after, dict) else {}
            still_added = after_summary.get("added", 0)
            still_changed = after_summary.get("changed", 0)
            if still_added + still_changed > 0:
                return r.refused(
                    "verification_failed",
                    f"{project} still differs on {profile_b} after project_sync "
                    f"(added={still_added}, changed={still_changed})",
                    before=before,
                    sync=sync,
                    after=after,
                )
            body: dict[str, Any] = {}
            still_removed = after_summary.get("removed", 0)
            if still_removed > 0 and not delete:
                body["pending_removals"] = still_removed
            return r.ok(before=before, sync=sync, after=after, **body)
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
    async def push_workspace(
        path: str = ".", confirm: bool = False, delete: bool = False
    ) -> ToolResult:
        """Push the local workspace at `path` to its gateway project via ign's
        workspace_push. Refuses when any member changed on both sides or when the
        workspace already matches the gateway, and requires confirm: true to
        actually push (workspace_push is destructive).

        Conflicts are refused before any push is attempted, even with confirm:
        true, because ign can never confirm them. The second workspace_status is a
        verification of the pushed members only: a written member still
        `local_edit`, or a deleted member still a local deletion, means the push
        did not land and the result is `verification_failed`. ign never advances
        the workspace baseline on push, so pushed members read as `conflict`
        afterwards until a fresh `ign workspace checkout`; that is success, and the
        result says so in `note`. Local deletions are pushed only with delete:
        true."""
        r = Runner(backend)
        try:
            before = await r.run("workspace_status", {"path": path})
            rows = before.get("rows", [])
            conflicts = [
                row.get("path")
                for row in rows
                if isinstance(row, dict) and row.get("kind") == "conflict"
            ]
            if conflicts:
                return r.refused(
                    "workspace_conflict",
                    f"{len(conflicts)} member(s) changed on both sides; reconcile locally, "
                    "then re-run `ign workspace checkout` for this project before pushing. "
                    "A conflict immediately after a successful push is expected: ign does "
                    "not advance the workspace baseline on push, so re-checkout first",
                    conflicts=conflicts,
                )
            if before.get("clean") is True:
                return r.refused(
                    "nothing_to_push",
                    f"workspace at {path} matches the gateway",
                    status=before,
                )
            push = await r.run(
                "workspace_push", {"path": path, "delete": delete, "confirm": confirm}
            )
            after = await r.run("workspace_status", {"path": path})
            wrote = list(push.get("wrote", []))
            deleted = list(push.get("deleted", []))
            kinds = {
                row.get("path"): row.get("kind")
                for row in after.get("rows", [])
                if isinstance(row, dict)
            }
            not_landed = [p for p in wrote if kinds.get(p) == "local_edit"]
            not_landed += [p for p in deleted if kinds.get(p) == LOCAL_DELETE]
            if not_landed:
                return r.refused(
                    "verification_failed",
                    f"workspace_push reported {len(not_landed)} member(s) pushed that "
                    f"workspace_status still shows as local changes: {', '.join(not_landed)}",
                    before=before,
                    push=push,
                    after=after,
                )
            return r.ok(
                before=before,
                push=push,
                after=after,
                pushed=wrote + deleted,
                note=BASELINE_NOTE,
            )
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def tag_snapshot(
        path: str, max_depth: int = 3, max_tags: int = 500, max_browses: int = 50
    ) -> ToolResult:
        """Browse under `path` (recursive, depth-limited) and read every atomic tag
        found, in one call. Recursion happens in Python: ign's tags_browse is not
        recursive, so `max_browses` caps how many tags_browse calls one snapshot
        may spend.

        `truncated` is true only when something was actually left out: atomic tags
        dropped past `max_tags`, or folders never visited because `max_depth` or
        `max_browses` ran out. `browse_budget_exhausted` says which of those it
        was."""
        r = Runner(backend)
        atomic: list[str] = []
        browsed = 0
        dropped = False
        unvisited = False
        budget_exhausted = False
        try:
            queue: list[tuple[str, int]] = [(path, 0)]
            while queue:
                if browsed >= max_browses:
                    budget_exhausted = True
                    unvisited = True
                    break
                if len(atomic) >= max_tags:
                    unvisited = True
                    break
                current, depth = queue.pop(0)
                found = await r.run("tags_browse", {"path": current})
                browsed += 1
                for entry in found.get("entries", []):
                    tag_type = entry.get("tag_type")
                    if tag_type == "AtomicTag":
                        if len(atomic) < max_tags:
                            atomic.append(entry["path"])
                        else:
                            dropped = True
                    elif entry.get("has_children"):
                        if depth + 1 < max_depth:
                            queue.append((entry["path"], depth + 1))
                        else:
                            unvisited = True
            tags = await r.run("tags_read", {"paths": atomic}) if atomic else {"results": []}
            return r.ok(
                root=path,
                browsed=browsed,
                tags=tags.get("results", []),
                truncated=dropped or unvisited,
                browse_budget_exhausted=budget_exhausted,
            )
        except StepFailed as e:
            return r.failed(e)
        except Exception as exc:
            return r.internal_error(exc)

    @mcp.tool
    async def find_alarms(
        min_priority: Literal["Diagnostic", "Low", "Medium", "High", "Critical"] = "Diagnostic",
        path_contains: str | None = None,
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
