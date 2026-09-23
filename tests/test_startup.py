import pytest

from ignition_mcp.config import Settings
from ignition_mcp.ign import IgnBackend, IgnUnavailable, parse_version


def test_parse_version():
    assert parse_version("ign 1.2.0\n") == (1, 2, 0)
    assert parse_version("ign 1.10.3") == (1, 10, 3)


async def test_missing_binary(tmp_path):
    s = Settings(ign_bin=str(tmp_path / "nope"))
    with pytest.raises(IgnUnavailable) as e:
        await IgnBackend(s).start()
    assert "IGN_BIN" in str(e.value)


async def test_too_old(ign_bin, scenario):
    scenario("healthy", version="1.1.9")
    s = Settings(ign_bin=ign_bin)
    with pytest.raises(IgnUnavailable) as e:
        await IgnBackend(s).start()
    assert "1.1.9" in str(e.value) and "1.3.0" in str(e.value)
