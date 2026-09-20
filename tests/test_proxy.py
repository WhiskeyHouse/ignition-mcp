from conftest import envelope_of


async def test_catalog_passes_through(client):
    names = {t.name for t in await client.list_tools()}
    assert {"status", "project_sync", "tags_read", "logs"} <= names


async def test_guarded_schema_has_optional_confirm(client):
    tool = next(t for t in await client.list_tools() if t.name == "project_sync")
    assert "confirm" in tool.inputSchema["properties"]
    assert "confirm" not in tool.inputSchema.get("required", [])


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
