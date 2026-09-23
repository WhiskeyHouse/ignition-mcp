from ignition_mcp.config import Settings


def test_defaults(monkeypatch):
    for key in ("IGN_BIN", "IGNITION_PROFILE", "IGN_MCP_HOST", "IGN_MCP_PORT"):
        monkeypatch.delenv(key, raising=False)
    s = Settings()
    assert s.ign_bin == "ign"
    assert s.profile is None
    assert s.host == "127.0.0.1"
    assert s.port == 8765
    assert s.min_ign_version == "1.3.0"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("IGN_BIN", "/opt/ign")
    monkeypatch.setenv("IGNITION_PROFILE", "uat")
    monkeypatch.setenv("IGN_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("IGN_MCP_PORT", "9000")
    s = Settings()
    assert s.ign_bin == "/opt/ign"
    assert s.profile == "uat"
    assert s.host == "0.0.0.0"
    assert s.port == 9000
