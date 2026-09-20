# Installation

`ignition-mcp` is a local HTTP front for `ign mcp serve`. It does not talk to a
gateway itself: it starts `ign` as a child process and forwards every call to it.
So `ign` has to work on this machine first.

## Requirements

- `ign` 1.2.0 or newer on `PATH`, with a configured profile
- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)

## Check ign first

```sh
ign --version
ign --profile uat status
```

If `status` does not return `"ok": true`, fix the profile before going further.
Nothing in this server can work around a profile that cannot reach its gateway.
Use `ign profile --help` to list and edit profiles.

## Install

```sh
git clone https://github.com/WhiskeyHouse/ignition-mcp.git
cd ignition-mcp
uv sync
```

## Run

```sh
uv run ign-mcp --profile uat
```

That serves Streamable HTTP on `http://127.0.0.1:8765/mcp`. The startup check runs
`ign --version`; if `ign` is missing or older than 1.2.0, the process prints a
message to stderr and exits with status 1.

For a client that launches the server as a subprocess, use stdio instead:

```sh
uv run ign-mcp --profile uat --stdio
```

`--host`, `--port`, `--ign-bin`, and the matching environment variables are
described in [Configuration](configuration.md).

## Local development only

There is no client authentication of any kind. Anything that can reach the port can
run every ign verb the profile is authorized for, including destructive ones. Keep
the default loopback bind of `127.0.0.1`. Do not expose it on a network.

## Add it to Claude Code

With the server already running:

```sh
claude mcp add --transport http ign-http http://127.0.0.1:8765/mcp
```

## Add it to another MCP client

The repository ships `mcp.example.json` with the same connection:

```json
{
  "mcpServers": {
    "ign-http": { "type": "http", "url": "http://127.0.0.1:8765/mcp" }
  }
}
```

Copy that entry into your client's MCP configuration file.

Next: [Quickstart](quickstart.md).
