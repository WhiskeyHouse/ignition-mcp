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


async def test_unknown_argument_returns_invalid_arguments_without_restart(backend):
    gen_before = backend._gen
    env = await backend.call("rig_down", {"confirm": True})
    assert env["ok"] is False
    assert env["error"]["code"] == "invalid_arguments"
    assert "confirm" in env["error"]["message"]
    assert backend._gen == gen_before

    env = await backend.call("status")
    assert env["ok"] is True


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


async def test_non_executable_binary(tmp_path, scenario):
    """A file that exists but cannot be exec'd must fail as IgnUnavailable, not
    as a bare PermissionError out of asyncio."""
    import pytest

    from ignition_mcp.config import Settings
    from ignition_mcp.ign import IgnBackend, IgnUnavailable

    not_executable = tmp_path / "ign-not-executable"
    not_executable.write_text("#!/bin/sh\nexit 0\n")
    not_executable.chmod(0o600)
    b = IgnBackend(Settings(ign_bin=str(not_executable), profile="uat"))
    with pytest.raises(IgnUnavailable) as excinfo:
        await b.start()
    assert str(not_executable) in str(excinfo.value)


async def test_malformed_envelope_is_reported(settings, scenario):
    from ignition_mcp.ign import IgnBackend

    scenario("garbage_json")
    b = IgnBackend(settings)
    await b.start()
    try:
        env = await b.call("status")
    finally:
        await b.stop()
    assert env["ok"] is False
    assert env["error"]["code"] == "ign_unavailable"
    assert "malformed" in env["error"]["message"]


async def test_confirmed_destructive_call_is_never_replayed(settings, scenario):
    """The child dies mid-call: ign may already have acted, so the call must not
    be retried, but the session must still be usable afterwards."""
    from ignition_mcp.ign import IgnBackend

    scenario("crash_once")
    b = IgnBackend(settings)
    await b.start()
    try:
        env = await b.call(
            "project_sync",
            {"profile_a": "a", "profile_b": "b", "project": "p", "confirm": True},
        )
        assert env["ok"] is False
        assert env["error"]["code"] == "ign_unavailable"
        assert "may have executed" in env["error"]["hint"]

        after = await b.call("status")
        assert after["ok"] is True
    finally:
        await b.stop()


async def test_non_argument_protocol_error_is_protocol_error(settings, scenario):
    from ignition_mcp.ign import IgnBackend

    scenario("method_missing")
    b = IgnBackend(settings)
    await b.start()
    try:
        gen_before = b._gen
        env = await b.call("status")
        assert env["ok"] is False
        assert env["error"]["code"] == "protocol_error"
        assert "method not found" in env["error"]["message"]
        assert env["error"]["hint"] is None
        assert b._gen == gen_before
    finally:
        await b.stop()
