# ignition-mcp

A local **Streamable HTTP** front for [`ign mcp serve`](https://github.com/WhiskeyHouse/ignition-cli),
plus composite workflow tools, `ign://` resources, and runbook prompts.

`ign` is the source of truth: every ign verb is proxied unchanged (the full ign tool catalog, 91 tools in ign 1.3.0),
credentials and profiles are ign's, and destructive verbs still require `confirm: true`.
This server never talks to a gateway itself.

> **Local development only.** There is no client authentication. Keep the default
> loopback bind (`127.0.0.1`). Do not expose it on a network.

## Watch it in use

### Ignition MCP + Agent

An agent inspects gateway health, reads batch conditions and traceability, and discusses hold readiness through Ignition MCP.

[![Ignition MCP + Agent recorded terminal walkthrough](website/static/demos/pi.gif?raw=true)](https://whiskeyhouse.github.io/ignition-mcp/docs/demos/)

[Open the recordings with playback controls and written summaries](https://whiskeyhouse.github.io/ignition-mcp/docs/demos/). Recorded against a fictional batch process; playback runs at 1.2×.

## Requirements

- `ign` >= 1.3.0 on PATH (or `IGN_BIN=/path/to/ign`) with a configured profile
- Python 3.11+, `uv`

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

## Upgrading from the previous server

`mcp_server.py`, `run_server.sh`, and the Docker image are gone; run `uv run ign-mcp`.
The `IGNITION_MCP_*` settings are gone too. The gateway URL and credentials now live in
`ign profile`, and the only settings left are the four in the table above.

Run `ign adopt --project ign-cli` once per gateway to deploy the WebDev routes the tag
and script verbs need.

Old tool names map onto ign verbs:

| Old | New |
|-----|-----|
| `get_gateway_info` | `status` |
| `list_projects` | `project_list` |
| `read_tags` | `tags_read` |
| `write_tag` | `tags_write` |
| `browse_tags` | `tags_browse` |
| `get_active_alarms` | `tags_alarms_active` |
| `run_gateway_script` | `script_run` |

## Composite tools

| Tool | Steps | Guarded |
|------|-------|---------|
| `diagnose_gateway()` | status, license_status, redundancy_status, gan_status, connections, modules, doctor → `verdict` healthy/degraded/down | no |
| `deploy_project(project, profile_a, profile_b, confirm=False, delete=False)` | project_diff → project_sync (all-changed) → project_diff; profile A→B promotion; refuses `nothing_to_promote` when identical and `verification_failed` when the second diff still shows added or changed resources; reports `pending_removals` when only removals are left and `delete` is false | `confirm` |
| `push_workspace(path=".", confirm=False, delete=False)` | workspace_status → workspace_push → workspace_status; local workspace to gateway push; refuses `workspace_conflict` (before any push, even with `confirm`) when a member changed on both sides, `nothing_to_push` when the workspace is clean, and `verification_failed` when the second status is still not clean and shows no `gateway_drift` | `confirm` |
| `rig_fresh(confirm=False)` | rig_down, rig_up, wait_gateway, status | `confirm` |
| `tag_snapshot(path, max_depth=3, max_tags=500, max_browses=50)` | tags_browse (recursed in Python, at most `max_browses` calls) + tags_read; reports `truncated` and `browse_budget_exhausted` | no |
| `find_alarms(min_priority="Diagnostic", path_contains=None)` | tags_alarms_active, filtered | no |

Results: `{"ok", "steps": [{tool, ok, code}], ...}`; on failure also `step` and `error` (the ign envelope).

## Resources

`ign://status`, `ign://profiles`, `ign://projects`, `ign://rig/status`, `ign://logs/tail{?n}`

## Prompts

`health_check`, `bring_up_rig`, `sync_project(project, profile_a, profile_b)`, `push_local_edits(path)`, `triage_alarm(path)`

## Develop

```bash
uv sync --extra dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
Tests use `tests/fake_ign.py`; no gateway needed.
