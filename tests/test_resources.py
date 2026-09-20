import json


async def test_static_resources_listed(client):
    uris = {str(r.uri) for r in await client.list_resources()}
    assert {"ign://status", "ign://profiles", "ign://projects", "ign://rig/status"} <= uris


async def test_status_resource(client):
    content = await client.read_resource("ign://status")
    env = json.loads(content[0].text)
    assert env["ok"] is True and env["data"]["state"] == "RUNNING"


async def test_logs_tail_template(client):
    templates = {str(t.uriTemplate) for t in await client.list_resource_templates()}
    assert "ign://logs/tail{?n}" in templates
    content = await client.read_resource("ign://logs/tail?n=5")
    env = json.loads(content[0].text)
    assert len(env["data"]) == 5
