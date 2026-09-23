async def test_prompts_listed(client):
    names = {p.name for p in await client.list_prompts()}
    assert {
        "health_check",
        "bring_up_rig",
        "sync_project",
        "triage_alarm",
        "push_local_edits",
    } <= names


async def test_sync_project_names_tools(client):
    result = await client.get_prompt(
        "sync_project", {"project": "Demo", "profile_a": "uat", "profile_b": "prod"}
    )
    text = result.messages[0].content.text
    for tool in ("project_diff", "project_sync", "deploy_project"):
        assert tool in text
    for value in ("Demo", "uat", "prod"):
        assert value in text


async def test_triage_alarm_names_path(client):
    result = await client.get_prompt("triage_alarm", {"path": "[default]Line1/Speed"})
    text = result.messages[0].content.text
    assert "[default]Line1/Speed" in text and "tags_alarms_active" in text


async def test_push_local_edits_names_tools(client):
    result = await client.get_prompt("push_local_edits", {"path": "ws/Demo"})
    text = result.messages[0].content.text
    for needle in ("workspace_status", "workspace_push", "confirm: true", "push_workspace"):
        assert needle in text
    assert "ws/Demo" in text
