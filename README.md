# ignition-mcp

A local **Streamable HTTP** front for [`ign mcp serve`](https://github.com/WhiskeyHouse/ignition-cli),
plus composite workflow tools, `ign://` resources, and runbook prompts.

`ign` is the source of truth: every ign verb is proxied unchanged (the full ign tool catalog, 91 tools in ign 1.2.0),
credentials and profiles are ign's, and destructive verbs still require `confirm: true`.
This server never talks to a gateway itself.

> **Local development only.** There is no client authentication. Keep the default
> loopback bind (`127.0.0.1`). Do not expose it on a network.

## Requirements

- `ign` >= 1.2.0 on PATH (or `IGN_BIN=/path/to/ign`) with a configured profile
- Python 3.11+, `uv`

`ign workspace push` cannot be confirmed over MCP in ign 1.2.0 (the verb is not in
ign's guarded set), so there is no local-workspace push composite yet.

## Run

```bash
uv sync
uv run ign-mcp --profile uat            # http://127.0.0.1:8765/mcp
uv run ign-mcp --stdio                  # same server over stdio
```

Add to Claude Code:

```bash
claude mcp add --transport http ign-http http://127.0.0.1:8765/mcp
```

Or point a client at the included `mcp.example.json`.

## Settings

| Env | Flag | Default |
|-----|------|---------|
| `IGN_BIN` | `--ign-bin` | `ign` |
| `IGNITION_PROFILE` | `--profile` | ign's active profile |
| `IGN_MCP_HOST` | `--host` | `127.0.0.1` |
| `IGN_MCP_PORT` | `--port` | `8765` |

Gateway credentials: see `ign profile --help` (keychain or `IGNITION_TOKEN*` env).

## Composite tools

| Tool | Steps | Guarded |
|------|-------|---------|
| `diagnose_gateway()` | status, license_status, redundancy_status, gan_status, connections, modules, doctor → `verdict` healthy/degraded/down | no |
| `deploy_project(project, profile_a, profile_b, confirm=False, delete=False)` | project_diff → project_sync (all-changed) → project_diff; profile A→B promotion; refuses `nothing_to_promote` when identical | `confirm` |
| `rig_fresh(confirm=False)` | rig_down, rig_up, wait_gateway, status | `confirm` |
| `tag_snapshot(path, max_depth=3, max_tags=500)` | tags_browse (recursed in Python) + tags_read | no |
| `find_alarms(min_priority="Diagnostic", path_contains=None)` | tags_alarms_active, filtered | no |

Results: `{"ok", "steps": [{tool, ok, code}], ...}`; on failure also `step` and `error` (the ign envelope).

## Resources

`ign://status`, `ign://profiles`, `ign://projects`, `ign://rig/status`, `ign://logs/tail{?n}`

## Prompts

`health_check`, `bring_up_rig`, `sync_project(project, profile_a, profile_b)`, `triage_alarm(path)`

## Develop

```bash
uv sync --extra dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
Tests use `tests/fake_ign.py`; no gateway needed.
