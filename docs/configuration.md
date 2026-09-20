# Configuration

Generated from the server source by `website/sync-reference.py`. Do not edit by hand.

`ign-mcp` has four settings. Each takes a command-line flag or an environment
variable, and the flag wins when both are set. Everything about the gateway itself
(address, credentials, TLS) belongs to `ign`, not to this server.

| Setting | Env var | CLI flag | Default |
| --- | --- | --- | --- |
| `ign_bin` | `IGN_BIN` | `--ign-bin` | `ign` |
| `profile` | `IGNITION_PROFILE` | `--profile` | — |
| `host` | `IGN_MCP_HOST` | `--host` | `127.0.0.1` |
| `port` | `IGN_MCP_PORT` | `--port` | `8765` |
| `min_ign_version` | — | — | `1.2.0` |

With neither `--profile` nor `IGNITION_PROFILE` set, the server starts
`ign mcp serve` without a `--profile` argument and ign uses its own active profile.
`min_ign_version` is not an override: it records the lowest ign version the server
accepts, and startup fails when the ign on PATH is older.

```sh
uv run ign-mcp --profile uat --port 8765
IGNITION_PROFILE=uat IGN_BIN=/opt/homebrew/bin/ign uv run ign-mcp
```

## Gateway credentials

This server never reads a gateway credential. It launches `ign mcp serve` as a child
process with the current environment, and ign resolves the credential for the
profile it serves, in this order: `IGNITION_TOKEN_<PROFILE>`, then the profile's own
`token_env` variable, then `IGNITION_TOKEN`, then the OS keyring, then
`IGNITION_USER` with `IGNITION_PASSWORD`.

Environment tokens come before the keyring. A bare `IGNITION_TOKEN` exported in your
shell is therefore used for every profile and silently overrides the keyring
credential the profile was adopted with. If calls fail with `auth_rejected` on a
profile that works from the terminal, unset `IGNITION_TOKEN` and start the server
again.

Run `ign profile --help` to inspect or change profiles.
