#!/usr/bin/env python3
"""A stand-in for `ign` that speaks enough of `ign mcp serve` for tests.

Protocol: newline-delimited JSON-RPC 2.0 on stdio, exactly like ign.
Scenario via FAKE_IGN_SCENARIO: healthy (default) | license_down | dirty | crash_once |
identical | module_faulted | garbage_shapes | garbage_text.
"""

import json
import os
import sys

VERSION = os.environ.get("FAKE_IGN_VERSION", "1.2.0")
SCENARIO = os.environ.get("FAKE_IGN_SCENARIO", "healthy")
PROFILE = None
for i, a in enumerate(sys.argv):
    if a == "--profile" and i + 1 < len(sys.argv):
        PROFILE = sys.argv[i + 1]

GUARDED = {"project_sync", "rig_down", "restart"}
TOOLS = [
    "status",
    "license_status",
    "redundancy_status",
    "gan_status",
    "connections",
    "modules",
    "doctor",
    "workspace_status",
    "project_sync",
    "project_diff",
    "rig_down",
    "rig_up",
    "wait_gateway",
    "rig_status",
    "tags_browse",
    "tags_read",
    "tags_alarms_active",
    "profile_list",
    "project_list",
    "logs",
    "restart",
]


def ok(data):
    return {"ok": True, "profile": PROFILE, "data": data}


def fail(code, message, hint=None):
    return {
        "ok": False,
        "profile": PROFILE,
        "error": {"code": code, "message": message, "endpoint": None, "hint": hint},
    }


def envelope(name, args):
    if name in GUARDED and not args.get("confirm"):
        return fail(
            "confirmation_required",
            f"{name} is destructive; rerun with confirm: true to confirm",
            'Set {"confirm": true} in the tool arguments to execute it.',
        )
    if name == "status":
        return ok({"version": "8.3.2", "state": "RUNNING", "uptime_seconds": 120})
    if name == "license_status":
        if SCENARIO == "license_down":
            return fail("gateway_error", "license service unavailable")
        return ok({"mode": "trial", "remaining_seconds": 7000})
    if name == "redundancy_status":
        return ok({"role": "Independent"})
    if name == "gan_status":
        return ok({"connections": []})
    if name == "connections":
        return ok(
            {
                "database": [
                    {"name": "db", "enabled": True, "healthchecks": [], "extra": {}},
                ],
                "opc": [],
            }
        )
    if name == "modules":
        state = "FAULTED" if SCENARIO == "module_faulted" else "ACTIVE"
        return ok(
            {
                "items": [
                    {
                        "id": "com.inductiveautomation.perspective",
                        "name": "Perspective",
                        "state": state,
                    }
                ],
                "quarantined": False,
            }
        )
    if name == "doctor":
        return ok({"checks": [{"name": "disk", "ok": True}], "healthy": True})
    if name == "workspace_status":
        dirty = SCENARIO == "dirty"
        changed = ["views/Main.json"] if dirty else []
        return ok(
            {
                "project": "Demo",
                "clean": not dirty,
                "rows": [{"path": p, "kind": "modified"} for p in changed],
            }
        )
    if name == "project_sync":
        return ok(
            {
                "scope": "project",
                "profile_a": args.get("profile_a"),
                "profile_b": args.get("profile_b"),
                "project": args.get("project"),
                "synced": ["views/Main.json"],
                "removed": [],
            }
        )
    if name == "project_diff":
        if SCENARIO == "identical":
            summary = {"same": 10, "added": 0, "removed": 0, "changed": 0}
        else:
            summary = {"same": 10, "added": 1, "removed": 0, "changed": 2}
        return ok(
            {
                "scope": "project",
                "profile_a": args.get("profile_a"),
                "profile_b": args.get("profile_b"),
                "project": args.get("project"),
                "project_meta": [],
                "summary": summary,
            }
        )
    if name in ("rig_down", "rig_up", "wait_gateway"):
        return ok({"done": name})
    if name == "rig_status":
        return ok({"containers": [{"name": "gw", "state": "running"}]})
    if name == "tags_browse":
        if SCENARIO == "garbage_shapes":
            return ok("not-a-dict")
        path = args.get("path")
        by_path = {
            "[default]Line1": [
                {
                    "path": "[default]Line1/Speed",
                    "name": "Speed",
                    "tag_type": "AtomicTag",
                    "has_children": False,
                },
                {
                    "path": "[default]Line1/Sub",
                    "name": "Sub",
                    "tag_type": "Folder",
                    "has_children": True,
                },
                {
                    "path": "[default]Line1/Count",
                    "name": "Count",
                    "tag_type": "AtomicTag",
                    "has_children": False,
                },
            ],
            "[default]Line1/Sub": [
                {
                    "path": "[default]Line1/Sub/Temp",
                    "name": "Temp",
                    "tag_type": "AtomicTag",
                    "has_children": False,
                },
            ],
        }
        entries = by_path.get(path, [])
        return ok(
            {
                "project": "Demo",
                "path": path,
                "filter": args.get("filter"),
                "include_properties": args.get("include-properties", False),
                "entries": entries,
            }
        )
    if name == "tags_read":
        paths = args.get("paths") or []
        if isinstance(paths, str):
            paths = [paths]
        return ok(
            {
                "project": "Demo",
                "results": [
                    {
                        "path": p,
                        "value": 42,
                        "quality": "Good",
                        "timestamp": "2026-09-20T00:00:00Z",
                    }
                    for p in paths
                ],
            }
        )
    if name == "tags_alarms_active":
        return ok(
            {
                "project": "ign-cli",
                "alarms": [
                    {
                        "event_id": "1",
                        "source": "[default]Line1/Speed",
                        "state": "Active",
                        "priority": "High",
                        "name": "OverSpeed",
                    },
                    {
                        "event_id": "2",
                        "source": "[default]Line2/Temp",
                        "state": "Active",
                        "priority": "Low",
                        "name": "Warm",
                    },
                    {
                        "event_id": "3",
                        "source": "[default]Line3/Flow",
                        "state": "Active",
                        "priority": "",
                        "name": "NoPriority",
                    },
                ],
                "count": 3,
            }
        )
    if name == "profile_list":
        return ok(
            {
                "active": PROFILE,
                "profiles": [{"name": "uat", "url": "http://localhost:18188/"}],
            }
        )
    if name == "project_list":
        return ok([{"name": "Demo", "enabled": True}])
    if name == "logs":
        n = int(args.get("limit") or 200)
        return ok([{"level": "INFO", "message": f"line {i}"} for i in range(n)])
    return fail("unknown_tool", f"no such tool {name}")


STR = {"type": "string"}
BOOL = {"type": "boolean"}
STR_LIST = {"type": "array", "items": {"type": "string"}}

# The properties each ign verb really advertises, so the proxied schemas the tests
# assert against match what `ign mcp serve` publishes.
PROPERTIES = {
    "project_diff": {"profile_a": STR, "profile_b": STR, "project": STR},
    "project_sync": {
        "profile_a": STR,
        "profile_b": STR,
        "project": STR,
        "all-changed": BOOL,
        "delete": BOOL,
        "resource": STR,
    },
    "tags_browse": {"path": STR, "filter": STR},
    "tags_read": {"paths": STR_LIST},
    "tags_alarms_active": {"priority": STR, "source": STR, "state": STR},
    "workspace_status": {"path": STR},
    "logs": {"limit": {"type": "string"}},
}


def catalog():
    tools = []
    for name in TOOLS:
        props = dict(PROPERTIES.get(name, {}))
        if name in GUARDED:
            props["confirm"] = BOOL
        tools.append(
            {
                "name": name,
                "description": f"fake {name}",
                "inputSchema": {"type": "object", "properties": props},
            }
        )
    return tools


def serve():
    calls = 0
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        msg = json.loads(raw)
        mid = msg.get("id")
        method = msg.get("method")
        if method == "initialize":
            out = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-ign", "version": VERSION},
            }
        elif method == "tools/list":
            out = {"tools": catalog()}
        elif method == "tools/call":
            calls += 1
            if (
                SCENARIO == "crash_once"
                and calls == 1
                and not os.path.exists(os.environ["FAKE_IGN_CRASH_MARK"])
            ):
                open(os.environ["FAKE_IGN_CRASH_MARK"], "w").close()
                os._exit(3)
            called = msg["params"]["name"]
            if SCENARIO == "garbage_text" and called == "status":
                out = {"content": [{"type": "text", "text": "not json"}], "isError": False}
            else:
                env = envelope(called, msg["params"].get("arguments") or {})
                out = {
                    "content": [{"type": "text", "text": json.dumps(env)}],
                    "isError": not env["ok"],
                }
        elif method == "ping":
            out = {}
        else:
            if mid is None:
                continue
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": mid,
                        "error": {"code": -32601, "message": "method not found"},
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
            continue
        if mid is None:
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": out}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    if "--version" in sys.argv:
        print(f"ign {VERSION}")
    elif "mcp" in sys.argv and "serve" in sys.argv:
        serve()
    else:
        sys.exit(2)
