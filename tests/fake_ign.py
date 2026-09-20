#!/usr/bin/env python3
"""A stand-in for `ign` that speaks enough of `ign mcp serve` for tests.

Protocol: newline-delimited JSON-RPC 2.0 on stdio, exactly like ign.
Scenario via FAKE_IGN_SCENARIO: healthy (default) | license_down | dirty | crash_once.
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
                "databases": [{"name": "db", "status": "Valid"}],
                "opc": [],
            }
        )
    if name == "modules":
        return ok([{"name": "Perspective", "state": "RUNNING"}])
    if name == "doctor":
        return ok({"checks": [{"name": "disk", "ok": True}], "healthy": True})
    if name == "workspace_status":
        return ok(
            {
                "dirty": SCENARIO == "dirty",
                "changed": ["views/Main.json"] if SCENARIO == "dirty" else [],
            }
        )
    if name == "project_sync":
        return ok({"pushed": 3})
    if name == "project_diff":
        return ok({"changed": [], "added": [], "removed": []})
    if name in ("rig_down", "rig_up", "wait_gateway"):
        return ok({"done": name})
    if name == "rig_status":
        return ok({"containers": [{"name": "gw", "state": "running"}]})
    if name == "tags_browse":
        return ok(
            [
                {"path": "[default]Line1/Speed", "type": "AtomicTag"},
                {"path": "[default]Line1", "type": "Folder"},
                {"path": "[default]Line1/Count", "type": "AtomicTag"},
            ]
        )
    if name == "tags_read":
        paths = args.get("paths") or args.get("path") or []
        if isinstance(paths, str):
            paths = [paths]
        return ok(
            [
                {
                    "path": p,
                    "value": 42,
                    "quality": "Good",
                    "timestamp": "2026-09-20T00:00:00Z",
                }
                for p in paths
            ]
        )
    if name == "tags_alarms_active":
        return ok(
            [
                {"source": "[default]Line1/Speed", "priority": "High", "name": "OverSpeed"},
                {"source": "[default]Line2/Temp", "priority": "Low", "name": "Warm"},
            ]
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
        n = int(args.get("lines") or args.get("n") or 200)
        return ok([{"level": "INFO", "message": f"line {i}"} for i in range(n)])
    return fail("unknown_tool", f"no such tool {name}")


def catalog():
    tools = []
    for name in TOOLS:
        props = {}
        if name in GUARDED:
            props["confirm"] = {"type": "boolean"}
        if name == "tags_read":
            props["paths"] = {"type": "array", "items": {"type": "string"}}
        if name == "logs":
            props["lines"] = {"type": "integer"}
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
            env = envelope(msg["params"]["name"], msg["params"].get("arguments") or {})
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
