async def test_call_success(backend):
    env = await backend.call("status")
    assert env["ok"] is True
    assert env["profile"] == "uat"
    assert env["data"]["state"] == "RUNNING"


async def test_call_failure_is_returned_not_raised(backend):
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


async def test_concurrent_calls_survive_single_crash(settings, scenario):
    import asyncio

    from ignition_mcp.ign import IgnBackend

    scenario("crash_once")
    b = IgnBackend(settings)
    await b.start()
    try:
        results = await asyncio.gather(b.call("status"), b.call("status"))
        assert all(env["ok"] is True for env in results)
    finally:
        await b.stop()


async def test_non_json_payload_returns_envelope(settings, scenario):
    from ignition_mcp.ign import IgnBackend

    scenario("garbage_text")
    b = IgnBackend(settings)
    await b.start()
    try:
        env = await b.call("status")
    finally:
        await b.stop()
    assert env["ok"] is False
    assert env["error"]["code"] == "ign_unavailable"
    assert "non-envelope" in env["error"]["message"]
