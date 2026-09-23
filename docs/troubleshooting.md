# Troubleshooting

Almost every failure here is an ign failure that the server forwarded. The first
question is always whether the same thing works from a terminal:

```sh
ign --profile uat status
```

## The server will not start

`ign-mcp` probes `ign --version` before it serves anything. On failure it prints one
line to stderr, prefixed `ign-mcp:`, and exits with status 1.

- `ign binary not found at 'ign'; set IGN_BIN or add ign to PATH` — `ign` is not on
  `PATH`. Set `IGN_BIN` to the full path, or pass `--ign-bin /path/to/ign`.
- `ign 1.1.0 is too old; need >= 1.3.0` — upgrade ign. The server does not run
  against older versions.
- `ign --version timed out after 10s` or `ign --version exited 1` — the binary at
  that path is not a working ign. Run it yourself and see what it says.

## Port 8765 is already in use

The bind fails at startup. Either stop the other `ign-mcp` process or move this one:

```sh
uv run ign-mcp --profile uat --port 8766
```

Then update the client's URL to match. If you registered the server with
`claude mcp add`, remove and re-add it with the new port.

## `auth_rejected`

ign reached the gateway and the gateway refused the credential. The usual cause is
credential resolution, not a bad gateway.

A bare `IGNITION_TOKEN` in the environment is used for every profile and is checked
before the OS keyring. If the profile was adopted with a keyring credential, that
stray variable silently replaces it. Unset it and start the server again:

```sh
unset IGNITION_TOKEN
uv run ign-mcp --profile uat
```

Per-profile variables (`IGNITION_TOKEN_UAT` for profile `uat`) are checked first and
are the safe way to override one profile. The full order is in
[Configuration](configuration.md).

## `ign_unavailable`

The ign child process died or stopped answering. The server restarts it once
automatically and retries the call; `ign_unavailable` means the retry failed too.

Check ign directly with `ign --profile uat status`. If that works, restart
`ign-mcp`. The error message carries the underlying exception type, which is worth
reading before restarting anything.

A call you sent with `confirm: true` is never retried. If the child dies during
one, the result says the operation may have executed and the hint tells you to
inspect gateway or rig state before sending it again. The session itself is
rebuilt, so the next call works normally.

This code also covers a reply that is not a well-formed ign envelope. There are
two messages. `ign returned a non-envelope payload` means the reply was not JSON
at all. `ign returned a malformed envelope` means it was JSON but not the
`{ok, profile, data|error}` shape. Both quote what came back, and both usually
mean the ign on `IGN_BIN` is not the version this server expects.

## `protocol_error`

ign answered with a JSON-RPC error that is not about the arguments, for example an
unknown method. The message is ign's own; there is no hint and the child is not
restarted, because it is answering fine. Check that `IGN_BIN` points at an ign new
enough to know the verb you called, and compare `ign --version` against the
requirement in [Installation](installation.md).

## `invalid_arguments`

ign rejected the arguments. The message carries ign's own text and the hint says to
check the tool's input schema. Ask your client to show the schema for that tool and
compare argument names; they are ign's names, not renamed here.

One case looks like a bug and is not. `rig_down` is not in ign's guarded set, so it
does not accept a `confirm` argument at all. Sending `confirm: true` to it is an
unknown argument and fails this way. Call it without it. For a guarded teardown and rebuild of a rig, use the
`rig_fresh` composite, which gates itself.

## `confirmation_required`

A destructive verb was called without `confirm: true`. Nothing was changed. Repeat
the call with `confirm: true`.

From `rig_fresh`, this comes from the composite itself rather than from ign, so the
result has `step: null` and no ign call was made at all.

## `nothing_to_promote`

`deploy_project` compared the two profiles first and found no added, changed, or
removed resources, so it refused rather than running a destructive sync that would
do nothing. The result's `summary` shows the counts it saw. If you expected a
difference, check that `profile_a`, `profile_b`, and `project` name what you meant.

## `verification_failed`

`deploy_project` ran the sync, diffed the two profiles again, and the project still
has added or changed resources on `profile_b`. The sync did not land. The message
carries both counts and the result carries `before`, `sync`, and `after`, so compare
the two summaries. The usual causes are a resource the gateway rejected and a
project that changed on `profile_a` while the sync ran.

Resources that exist only on `profile_b` are a different matter: `project_sync` does
not remove them unless `delete: true`. That case succeeds and reports the count as
`pending_removals` instead.

## Seeing ign's own diagnostics

The ign child writes its stderr to the terminal running `ign-mcp`, so leave that
terminal visible. For more detail, run the same verb directly with ign's verbose
flags, which also write to stderr:

```sh
ign -vv --profile uat status
```

`ign doctor` diagnoses URL, liveness, commissioning, auth, permissions, write
access, and the WebDev route in one pass, and is the fastest way to tell a profile
problem from a gateway problem.
