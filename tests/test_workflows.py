from contextlib import asynccontextmanager

from conftest import envelope_of
from fastmcp import Client

from ignition_mcp.ign import IgnBackend
from ignition_mcp.server import build_server


@asynccontextmanager
async def client_with_scenario(settings, scenario, name: str):
    """Build a fresh backend+client with `name` already baked into the fake
    ign subprocess's environment. The shared `client`/`backend` fixtures spawn
    the fake ign subprocess up front with the default `healthy` scenario, so
    calling `scenario(...)` inside a test body that only depends on those
    fixtures is too late: env vars are inherited at subprocess spawn, not
    polled afterward. Tests that need a non-default scenario build their own
    backend here, after setting the scenario, mirroring tests/test_backend.py.
    """
    scenario(name)
    backend = IgnBackend(settings)
    await backend.start()
    try:
        server = build_server(settings, backend)
        async with Client(server) as c:
            yield c
    finally:
        await backend.stop()


async def test_diagnose_gateway_healthy(client):
    out = envelope_of(await client.call_tool("diagnose_gateway", {}))
    assert out["ok"] is True
    assert out["verdict"] == "healthy"
    assert [s["tool"] for s in out["steps"]] == [
        "status",
        "license_status",
        "redundancy_status",
        "gan_status",
        "connections",
        "modules",
        "doctor",
    ]
    assert out["status"]["state"] == "RUNNING"


async def test_diagnose_gateway_short_circuits_on_first_failure(settings, scenario):
    async with client_with_scenario(settings, scenario, "license_down") as c:
        out = envelope_of(await c.call_tool("diagnose_gateway", {}, raise_on_error=False))
    assert out["ok"] is False
    assert out["step"] == "license_status"
    assert out["error"]["error"]["code"] == "gateway_error"
    assert [s["tool"] for s in out["steps"]] == ["status", "license_status"]
    assert out["steps"][-1] == {"tool": "license_status", "ok": False, "code": "gateway_error"}


async def test_deploy_project_refuses_when_nothing_to_promote(settings, scenario):
    async with client_with_scenario(settings, scenario, "identical") as c:
        out = envelope_of(
            await c.call_tool(
                "deploy_project",
                {"project": "Demo", "profile_a": "uat", "profile_b": "prod"},
                raise_on_error=False,
            )
        )
    assert out["ok"] is False
    assert out["error"]["error"]["code"] == "nothing_to_promote"
    assert [s["tool"] for s in out["steps"]] == ["project_diff"]


async def test_deploy_project_without_confirm_is_refused_by_ign(client):
    out = envelope_of(
        await client.call_tool(
            "deploy_project",
            {"project": "Demo", "profile_a": "uat", "profile_b": "prod"},
            raise_on_error=False,
        )
    )
    assert out["ok"] is False
    assert out["step"] == "project_sync"
    assert out["error"]["error"]["code"] == "confirmation_required"
    assert [s["tool"] for s in out["steps"]] == ["project_diff", "project_sync"]


async def test_deploy_project_confirm_path(client):
    out = envelope_of(
        await client.call_tool(
            "deploy_project",
            {"project": "Demo", "profile_a": "uat", "profile_b": "prod", "confirm": True},
        )
    )
    assert out["ok"] is True
    assert [s["tool"] for s in out["steps"]] == ["project_diff", "project_sync", "project_diff"]
    assert out["sync"]["synced"]


async def test_rig_fresh_requires_confirm(client):
    out = envelope_of(await client.call_tool("rig_fresh", {}, raise_on_error=False))
    assert out["ok"] is False and out["step"] == "rig_down"
    out = envelope_of(await client.call_tool("rig_fresh", {"confirm": True}))
    assert out["ok"] is True
    assert [s["tool"] for s in out["steps"]] == ["rig_down", "rig_up", "wait_gateway", "status"]


async def test_tag_snapshot(client):
    out = envelope_of(await client.call_tool("tag_snapshot", {"path": "[default]Line1"}))
    assert out["ok"] is True
    assert {t["path"] for t in out["tags"]} == {
        "[default]Line1/Speed",
        "[default]Line1/Count",
        "[default]Line1/Sub/Temp",
    }
    assert out["browsed"] == 2


async def test_find_alarms_filters(client):
    out = envelope_of(await client.call_tool("find_alarms", {"min_priority": "High"}))
    assert [a["name"] for a in out["alarms"]] == ["OverSpeed"]
    out = envelope_of(await client.call_tool("find_alarms", {"path_contains": "Line2"}))
    assert [a["name"] for a in out["alarms"]] == ["Warm"]


async def test_guarded_composites_confirm_not_required(client):
    tools = {t.name: t for t in await client.list_tools()}
    for name in ("deploy_project", "rig_fresh"):
        schema = tools[name].input_schema
        assert "confirm" in schema["properties"]
        assert "confirm" not in schema.get("required", [])
