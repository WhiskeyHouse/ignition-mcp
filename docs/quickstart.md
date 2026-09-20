# Quickstart

A first session against a running server. Start it with
`uv run ign-mcp --profile uat` and connect a client as shown in
[Installation](installation.md).

Ask your client to list tools. You should see the composite tools defined here
(`diagnose_gateway`, `deploy_project`, `rig_fresh`, `tag_snapshot`, `find_alarms`)
alongside every ign verb, proxied unchanged. The full list is in the
[Tool reference](reference.md).

## Read the gateway

Call `status` with no arguments. It is an ign verb, so the result is an ign
envelope:

```json
{"ok": true, "profile": "uat", "data": {"version": "8.3.2", "state": "RUNNING"}}
```

`diagnose_gateway` takes no arguments and does seven ign reads in one call:
`status`, `license_status`, `redundancy_status`, `gan_status`, `connections`,
`modules`, `doctor`. It returns its own object, not an ign envelope:

```json
{"ok": true, "verdict": "healthy",
 "steps": [{"tool": "status", "ok": true, "code": null},
           {"tool": "license_status", "ok": true, "code": null}]}
```

The verdict is `down` when `status` itself fails, `degraded` when a later step
fails, when a module reports a state other than `ACTIVE` or `RUNNING`, or when a
database connection has `enabled: false`, and `healthy` otherwise.

## Read a resource

Read the resource `ign://status`. It returns the same envelope `status` returns, as
JSON, without a tool call. The other resources are `ign://profiles`,
`ign://projects`, `ign://rig/status`, and `ign://logs/tail{?n}`, where `n` is the
number of log lines and defaults to 200.

## Use a prompt

Run the `health_check` prompt. It takes no arguments and returns a short runbook:
call `status`, stop if it failed, then call the six other reads, then report the
version, uptime, license mode, any module not running, any invalid database
connection, and any failed doctor check. It names `diagnose_gateway` as the one-call
shortcut.

The other prompts are `bring_up_rig`, `sync_project(project, profile_a, profile_b)`,
and `triage_alarm(path)`.

## A guarded call

Destructive ign verbs refuse until you pass `confirm: true`. Call `project_sync`
with `profile_a`, `profile_b`, and `project` but no `confirm`:

```json
{"ok": false, "profile": "uat",
 "error": {"code": "confirmation_required", "message": "...",
           "endpoint": null, "hint": "..."}}
```

Nothing happened on the gateway. Repeat the call with `confirm: true` added and it
executes.

`deploy_project` wraps that in a diff, sync, diff sequence and refuses early when
the two profiles already hold the same project:

```json
{"ok": false, "steps": [{"tool": "project_diff", "ok": true, "code": null}],
 "step": null,
 "error": {"ok": false, "profile": null,
           "error": {"code": "nothing_to_promote", "message": "...",
                     "endpoint": null, "hint": null}}}
```

## Snapshot some tags

`tag_snapshot` browses under a path and reads every atomic tag it finds. Providers
appear at the tag root, so start from one:

```json
{"path": "[default]Line1", "max_depth": 3, "max_tags": 500}
```

The result reports the root, how many browse calls it made, the tag values, and
whether it stopped at `max_tags`:

```json
{"ok": true, "root": "[default]Line1", "browsed": 2, "truncated": false,
 "tags": [{"path": "[default]Line1/Speed", "value": 42, "quality": "Good",
           "timestamp": "2026-09-20T00:00:00Z"}]}
```

`tags_browse` and `tags_read` need ign's WebDev routes deployed on the gateway. If
they are not, that step fails and `tag_snapshot` returns ign's error for it.

When something refuses or fails, see [Troubleshooting](troubleshooting.md).
