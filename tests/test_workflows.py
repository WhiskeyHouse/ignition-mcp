from conftest import client_with_scenario, envelope_of


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
    assert out["ok"] is False
    assert out["step"] is None
    assert out["error"]["error"]["code"] == "confirmation_required"
    assert out["steps"] == []
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
    out = envelope_of(await client.call_tool("find_alarms", {}))
    assert [a["name"] for a in out["alarms"]] == ["OverSpeed", "Warm", "NoPriority"]
    out = envelope_of(await client.call_tool("find_alarms", {"min_priority": "High"}))
    assert [a["name"] for a in out["alarms"]] == ["OverSpeed"]
    out = envelope_of(await client.call_tool("find_alarms", {"path_contains": "Line2"}))
    assert [a["name"] for a in out["alarms"]] == ["Warm"]


async def test_diagnose_gateway_degraded_on_faulted_module(settings, scenario):
    async with client_with_scenario(settings, scenario, "module_faulted") as c:
        out = envelope_of(await c.call_tool("diagnose_gateway", {}))
    assert out["ok"] is True
    assert out["verdict"] == "degraded"


async def test_composite_never_raises(settings, scenario):
    async with client_with_scenario(settings, scenario, "garbage_shapes") as c:
        result = await c.call_tool("tag_snapshot", {"path": "[default]Line1"}, raise_on_error=False)
    out = envelope_of(result)
    assert out["ok"] is False
    assert out["step"] is None
    assert out["error"]["error"]["code"] == "internal_error"


async def test_guarded_composites_confirm_not_required(client):
    tools = {t.name: t for t in await client.list_tools()}
    for name in ("deploy_project", "rig_fresh", "push_workspace"):
        schema = tools[name].input_schema
        assert "confirm" in schema["properties"]
        assert "confirm" not in schema.get("required", [])


async def test_diagnose_gateway_degraded_on_failed_doctor_check(settings, scenario):
    async with client_with_scenario(settings, scenario, "doctor_fail") as c:
        out = envelope_of(await c.call_tool("diagnose_gateway", {}))
    assert out["ok"] is True
    assert out["verdict"] == "degraded"


async def test_deploy_project_fails_verification_when_diff_remains(settings, scenario):
    async with client_with_scenario(settings, scenario, "sync_incomplete") as c:
        out = envelope_of(
            await c.call_tool(
                "deploy_project",
                {"project": "Demo", "profile_a": "uat", "profile_b": "prod", "confirm": True},
                raise_on_error=False,
            )
        )
    assert out["ok"] is False
    assert out["error"]["error"]["code"] == "verification_failed"
    assert "changed=1" in out["error"]["error"]["message"]
    assert [s["tool"] for s in out["steps"]] == ["project_diff", "project_sync", "project_diff"]


async def test_deploy_project_reports_pending_removals(settings, scenario):
    async with client_with_scenario(settings, scenario, "pending_removals") as c:
        out = envelope_of(
            await c.call_tool(
                "deploy_project",
                {"project": "Demo", "profile_a": "uat", "profile_b": "prod", "confirm": True},
            )
        )
    assert out["ok"] is True
    assert out["pending_removals"] == 2


async def test_deploy_project_clean_verification_has_no_pending_removals(client):
    out = envelope_of(
        await client.call_tool(
            "deploy_project",
            {"project": "Demo", "profile_a": "uat", "profile_b": "prod", "confirm": True},
        )
    )
    assert out["ok"] is True
    assert "pending_removals" not in out


async def test_tag_snapshot_exact_size_is_not_truncated(client):
    out = envelope_of(
        await client.call_tool("tag_snapshot", {"path": "[default]Line1", "max_tags": 3})
    )
    assert out["ok"] is True
    assert len(out["tags"]) == 3
    assert out["truncated"] is False
    assert out["browse_budget_exhausted"] is False


async def test_tag_snapshot_browse_budget(client):
    out = envelope_of(
        await client.call_tool("tag_snapshot", {"path": "[default]Line1", "max_browses": 1})
    )
    assert out["ok"] is True
    assert out["browsed"] == 1
    assert out["truncated"] is True
    assert out["browse_budget_exhausted"] is True
    assert {t["path"] for t in out["tags"]} == {
        "[default]Line1/Speed",
        "[default]Line1/Count",
    }


async def test_tag_snapshot_drops_tags_past_max_tags(client):
    out = envelope_of(
        await client.call_tool("tag_snapshot", {"path": "[default]Line1", "max_tags": 1})
    )
    assert out["ok"] is True
    assert len(out["tags"]) == 1
    assert out["truncated"] is True
    assert out["browse_budget_exhausted"] is False


async def test_find_alarms_priority_is_an_enum(client):
    tools = {t.name: t for t in await client.list_tools()}
    prop = tools["find_alarms"].input_schema["properties"]["min_priority"]
    enum = prop.get("enum") or next(
        (v.get("enum") for v in prop.get("anyOf", []) if v.get("enum")), None
    )
    assert enum == ["Diagnostic", "Low", "Medium", "High", "Critical"]


async def test_push_workspace_without_confirm_is_refused_by_ign(client):
    out = envelope_of(
        await client.call_tool("push_workspace", {"path": "ws/Demo"}, raise_on_error=False)
    )
    assert out["ok"] is False
    assert out["step"] == "workspace_push"
    assert out["error"]["error"]["code"] == "confirmation_required"
    assert [s["tool"] for s in out["steps"]] == ["workspace_status", "workspace_push"]


async def test_push_workspace_confirm_path(client):
    out = envelope_of(
        await client.call_tool("push_workspace", {"path": "ws/Demo", "confirm": True})
    )
    assert out["ok"] is True
    assert [s["tool"] for s in out["steps"]] == [
        "workspace_status",
        "workspace_push",
        "workspace_status",
    ]
    assert out["push"]["wrote"]
    assert out["before"]["clean"] is False
    assert out["after"]["clean"] is True


async def test_push_workspace_refuses_conflicts_even_with_confirm(settings, scenario):
    async with client_with_scenario(settings, scenario, "ws_conflict") as c:
        out = envelope_of(
            await c.call_tool(
                "push_workspace", {"path": "ws/Demo", "confirm": True}, raise_on_error=False
            )
        )
    assert out["ok"] is False
    assert out["step"] is None
    assert out["error"]["error"]["code"] == "workspace_conflict"
    assert out["conflicts"] == ["views/Main.json"]
    assert [s["tool"] for s in out["steps"]] == ["workspace_status"]


async def test_push_workspace_refuses_when_clean(settings, scenario):
    async with client_with_scenario(settings, scenario, "ws_clean") as c:
        out = envelope_of(
            await c.call_tool(
                "push_workspace", {"path": "ws/Demo", "confirm": True}, raise_on_error=False
            )
        )
    assert out["ok"] is False
    assert out["error"]["error"]["code"] == "nothing_to_push"
    assert "ws/Demo" in out["error"]["error"]["message"]
    assert out["status"]["clean"] is True
    assert [s["tool"] for s in out["steps"]] == ["workspace_status"]


async def test_push_workspace_fails_verification_when_edits_remain(settings, scenario):
    async with client_with_scenario(settings, scenario, "ws_push_incomplete") as c:
        out = envelope_of(
            await c.call_tool(
                "push_workspace", {"path": "ws/Demo", "confirm": True}, raise_on_error=False
            )
        )
    assert out["ok"] is False
    assert out["error"]["error"]["code"] == "verification_failed"
    assert [s["tool"] for s in out["steps"]] == [
        "workspace_status",
        "workspace_push",
        "workspace_status",
    ]
    assert out["after"]["clean"] is False
    assert out["push"]["wrote"]
    assert out["before"]["rows"]
