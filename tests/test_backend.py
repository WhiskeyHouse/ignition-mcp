async def test_call_success(backend):
    env = await backend.call("status")
    assert env["ok"] is True
    assert env["profile"] == "uat"
    assert env["data"]["state"] == "RUNNING"


async def test_call_failure_is_returned_not_raised(backend, scenario):
    env = await backend.call("project_sync", {})
    assert env["ok"] is False
    assert env["error"]["code"] == "confirmation_required"


async def test_restart_once_after_crash(settings, scenario):
    from ignition_mcp.ign import IgnBackend

    scenario("crash_once")
    b = IgnBackend(settings)
    await b.start()
    try:
        env = await b.call("status")
        assert env["ok"] is True
    finally:
        await b.stop()
