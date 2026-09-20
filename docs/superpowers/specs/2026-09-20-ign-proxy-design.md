# ignition-mcp as a local HTTP front for `ign mcp serve`

Date: 2026-09-20
Status: approved design, pre-implementation

## Goal

Replace the hand-written Python tool set (37 tools, FastMCP 2.12, own httpx
client) with a thin FastMCP 4 server that:

1. proxies the full `ign mcp serve` catalog (about 90 tools) over Streamable
   HTTP for clients that cannot spawn a binary or want to share one server;
2. adds composite workflow tools that chain several `ign` calls;
3. adds MCP resources and prompts for common runbooks.

`ignition-cli` (`ign`) stays the single source of truth for gateway access,
credentials, the `confirm` gate, and the JSON envelope. ignition-mcp never
talks to a gateway directly.

## Non-goals

- Client-to-MCP authentication. Local development only, loopback bind.
- Docker packaging.
- Any gateway REST or WebDev client in Python.
- Reproducing `ign` tools by hand. The catalog is whatever `ign` reports.

## Prerequisites

- `ign` on PATH (or `IGN_BIN`), version >= the first release whose
  `ign mcp serve` speaks protocol 2025-06-18 (ignition-cli 1.2.0).
- Gateway credentials configured for `ign` (profiles, keychain, or
  `IGNITION_TOKEN*` / `IGNITION_USER` / `IGNITION_PASSWORD` env).
- Python >= 3.11, `uv`.

## Architecture

```
MCP client (Claude Code, claude.ai connector, Cursor, agent)
        |  Streamable HTTP  127.0.0.1:8765/mcp   (or --stdio)
        v
ignition_mcp.server  (FastMCP 4)
   |-- mount(create_proxy(ign_client))     -> every ign tool, unchanged name
   |-- workflows.py                        -> composite tools
   |-- resources.py                        -> ign:// resources
   |-- prompts.py                          -> runbook prompts
        |
ignition_mcp.ign  (one shared ProxyClient over StdioTransport)
        |  newline JSON-RPC on stdio
        v
ign mcp serve  (Rust; profiles, keyring, env, confirm gate, envelope)
        |
   Ignition gateway(s)
```

### Package layout

```
src/ignition_mcp/
  __init__.py
  __main__.py     python -m ignition_mcp
  cli.py          argparse: --host --port --stdio --profile --ign-bin
  config.py       pydantic-settings: IGN_BIN, IGNITION_PROFILE, IGN_MCP_HOST, IGN_MCP_PORT
  ign.py          IgnBackend: spawn check, version probe, shared ProxyClient, call()
  server.py       build_server(settings) -> FastMCP
  workflows.py    composite tools
  resources.py    resources
  prompts.py      prompts
tests/
  fake_ign.py     stdio JSON-RPC stand-in for `ign mcp serve`
  conftest.py
  test_proxy.py
  test_workflows.py
  test_resources.py
  test_startup.py
```

Deleted: `mcp_server.py`, `run_server.sh`, `Dockerfile`,
`claude_code_config.json`, `ignition_tools_summary.json`,
`src/ignition_mcp/ignition_client.py`, `src/ignition_mcp/tools/`,
`src/ignition_mcp/main.py`, the old tests, and the `IGNITION_MCP_*` env
surface. `docs/` is rewritten to describe the new server.

## Components

### D2 Transport and entrypoint

`ign-mcp` console script (and `python -m ignition_mcp`). Defaults:
Streamable HTTP, host `127.0.0.1`, port `8765`, path `/mcp`. `--stdio`
serves the same server over stdio. `--profile` and `--ign-bin` override the
env settings. README states: local development only, no auth, keep the
loopback bind.

### D3 Proxy (`ign.py`)

- `IgnBackend.start()` runs `ign --version`, fails fast with the found and
  minimum versions if absent or too old.
- One `ProxyClient(StdioTransport(cmd=IGN_BIN, args=["--profile", P, "mcp",
  "serve"] , env=os.environ))` shared for the server lifetime. Session reuse
  is safe because `ign mcp serve` is stateless per `tools/call` and handles
  concurrent calls.
- `server.mount(create_proxy(backend.client))` with no prefix. Tool names,
  input schemas, the `confirm` property, and the response envelope pass
  through unchanged.
- `IgnBackend.call(name, args) -> dict` parses the single text block of an
  ign response into the envelope dict for use by workflows and resources.
- If the child exits, the next call restarts it once, then surfaces the
  error.

### D4 Composite tools (`workflows.py`)

Each returns one JSON object with `ok`, `steps` (list of `{tool, ok, code}`),
and a tool-specific body. On the first failing step the tool stops and
returns that step's ign envelope under `error` plus `step`.

| Tool | Steps | Body |
|------|-------|------|
| `diagnose_gateway` | status, license_status, redundancy_status, gan_status, connections, modules, doctor | `verdict`: `healthy` / `degraded` / `down`, plus each read |
| `deploy_project` (guarded) | workspace_status, project_sync, project_diff | refuses with `code: dirty_workspace` when uncommitted changes exist unless `confirm: true`; passes `confirm` to `project_sync` |
| `rig_fresh` (guarded) | rig_down, rig_up, wait_gateway, status | final status; `confirm` required |
| `tag_snapshot` | tags_browse (recursive, `max_depth` default 3, `max_tags` default 500), tags_read | `tags`: path, value, quality, timestamp |
| `find_alarms` | tags_alarms_active | filtered by `min_priority` and `path_contains` |

Guarded composites carry a `confirm: boolean` property that is not in
`required`, mirroring `ign`.

### D5 Resources (`resources.py`)

| URI | Backing tool | Notes |
|-----|--------------|-------|
| `ign://status` | status | |
| `ign://profiles` | profile_list | |
| `ign://projects` | project_list | |
| `ign://rig/status` | rig_status | |
| `ign://logs/tail{?n}` | logs | template, `n` default 200 |

Each returns the ign envelope as JSON text (`application/json`).

### D6 Prompts (`prompts.py`)

`health_check`, `bring_up_rig`, `sync_project(project)`, `triage_alarm(path)`.
Short runbooks naming the exact tools in order and the composite that does
the same in one call.

### D7 Errors and startup

- Missing or old `ign`: process exits 1 with message naming `IGN_BIN`, the
  found version, and the minimum.
- ign envelope errors are returned as tool results, never raised, so agents
  see the stable `code` slug.
- Child crash: one automatic restart, then error envelope
  `code: ign_unavailable`.

### D8 Tests

- `tests/fake_ign.py`: a Python script that speaks the ign stdio protocol
  (initialize, tools/list, tools/call) with a small canned catalog including
  one guarded tool. Installed on PATH via a `tmp_path` shim in `conftest.py`.
- `test_proxy.py`: catalog passthrough, a call, guarded refusal passthrough.
- `test_workflows.py`: `diagnose_gateway` verdict, `deploy_project` dirty
  refusal and confirm path, first-failing-step short-circuit.
- `test_resources.py`: `ign://status`, `ign://logs/tail?n=5`.
- `test_startup.py`: missing binary, version too old.
- All tests run against the server in-process via `fastmcp.Client`.

## Dependencies

`fastmcp>=4`, `pydantic-settings>=2`. Dev: `pytest`, `pytest-asyncio`,
`ruff`, `mypy`. `httpx`, `fastapi`, `uvicorn`, `mcp` direct pins removed.

## Docs

README rewritten: what it is, install (`uv sync`), run, add to Claude Code
(`claude mcp add --transport http ign-http http://127.0.0.1:8765/mcp`),
composite tool table, resource table, prompt list, local-only warning.
`docs/` reduced to what still applies.
