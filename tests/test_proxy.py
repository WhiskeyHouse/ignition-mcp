from conftest import client_with_scenario, envelope_of


async def test_catalog_passes_through(client):
    names = {t.name for t in await client.list_tools()}
    assert {"status", "project_sync", "tags_read", "logs"} <= names


async def test_guarded_schema_has_optional_confirm(client):
    tool = next(t for t in await client.list_tools() if t.name == "project_sync")
    assert "confirm" in tool.input_schema["properties"]
    assert "confirm" not in tool.input_schema.get("required", [])


async def test_call_passes_envelope_through(client):
    result = await client.call_tool("status", {})
    env = envelope_of(result)
    assert env == {
        "ok": True,
        "profile": "uat",
        "data": {"version": "8.3.2", "state": "RUNNING", "uptime_seconds": 120},
    }


async def test_guarded_refusal_passes_through(client):
    result = await client.call_tool("project_sync", {}, raise_on_error=False)
    env = envelope_of(result)
    assert env["ok"] is False
    assert env["error"]["code"] == "confirmation_required"
    assert "confirm: true" in env["error"]["message"]


async def test_proxied_tool_recovers_after_crash(settings, scenario):
    """Proxied tools bypass IgnBackend.call(), so their only crash recovery is
    the rebuild inside the `acquire` client factory."""
    async with client_with_scenario(settings, scenario, "crash_once") as c:
        await c.call_tool("status", {}, raise_on_error=False)  # may fail: child dies here
        second = envelope_of(await c.call_tool("status", {}, raise_on_error=False))
        third = envelope_of(await c.call_tool("status", {}, raise_on_error=False))
    assert second["ok"] is True
    assert third["ok"] is True
