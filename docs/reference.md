# Tool reference

Generated from the server source by `website/sync-reference.py`. Do not edit by hand.

The server exposes three things it defines itself (composite tools, `ign://`
resources, prompts) and one thing it forwards (every tool from `ign mcp serve`).

## Composite tools

Defined in this server, not in ign. Each chains several ign calls and returns one
result. See [Result shapes](#result-shapes) for the object they return.

### `diagnose_gateway`

```python
diagnose_gateway()
```

Full gateway health read in one call: status, license, redundancy, GAN, connections, modules, doctor.

### `deploy_project`

```python
deploy_project(project: str, profile_a: str, profile_b: str, confirm: bool = False, delete: bool = False)
```

Promote `project` from gateway profile `profile_a` to `profile_b` via ign's project_sync. Refuses when the two profiles are already identical, and requires confirm: true to actually push (project_sync is destructive).

Takes `confirm`. `deploy_project` does not change anything until it is `true`.

### `rig_fresh`

```python
rig_fresh(confirm: bool = False)
```

Tear down and bring up the active rig, then wait for the gateway: rig_down, rig_up, wait_gateway, status. Requires confirm: true.

Takes `confirm`. `rig_fresh` does not change anything until it is `true`.

### `push_workspace`

```python
push_workspace(path: str = '.', confirm: bool = False, delete: bool = False)
```

Push the local workspace at `path` to its gateway project via ign's workspace_push. Refuses when any member changed on both sides or when the workspace already matches the gateway, and requires confirm: true to actually push (workspace_push is destructive).

Takes `confirm`. `push_workspace` does not change anything until it is `true`.

### `tag_snapshot`

```python
tag_snapshot(path: str, max_depth: int = 3, max_tags: int = 500, max_browses: int = 50)
```

Browse under `path` (recursive, depth-limited) and read every atomic tag found, in one call. Recursion happens in Python: ign's tags_browse is not recursive, so `max_browses` caps how many tags_browse calls one snapshot may spend.

### `find_alarms`

```python
find_alarms(min_priority: Literal['Diagnostic', 'Low', 'Medium', 'High', 'Critical'] = 'Diagnostic', path_contains: str | None = None)
```

Active alarms filtered by minimum priority (Diagnostic|Low|Medium|High|Critical) and an optional source-path substring. Alarms whose priority is blank or unrecognised are kept only at the default `Diagnostic` floor.


## Resources

Read-only mirrors of the most-polled ign reads. Each read returns the ign envelope
as JSON.

| URI | ign tool | Contents |
| --- | --- | --- |
| `ign://status` | `status` | Gateway status envelope (ign status). |
| `ign://profiles` | `profile_list` | Configured ign profiles and the active one. |
| `ign://projects` | `project_list` | Projects on the active gateway. |
| `ign://rig/status` | `rig_status` | Docker rig container status. |
| `ign://logs/tail{?n}` | `logs` | Last n gateway log lines (ign logs). |

## Prompts

Runbooks. Each returns text naming the tools to call, in order, and the composite
that shortcuts them.

| Prompt | Purpose |
| --- | --- |
| `health_check()` | Daily gateway health check runbook. |
| `bring_up_rig()` | Bring a Docker test rig to a fresh, reachable gateway. |
| `sync_project(project: str, profile_a: str, profile_b: str)` | Promote a project from one gateway profile to another safely. |
| `push_local_edits(path: str)` | Push local workspace edits to the gateway safely. |
| `triage_alarm(path: str)` | Investigate an active alarm on a tag path. |

## Proxied ign tools

Every tool named like an ign verb is forwarded to `ign mcp serve` unchanged, with
ign's input schema and ign's result. A successful call returns:

```json
{"ok": true, "profile": "uat", "data": {"...": "..."}}
```

A failed call returns:

```json
{"ok": false, "profile": "uat", "error": {"code": "...", "message": "...", "endpoint": null, "hint": null}}
```

Destructive verbs carry a `confirm` boolean and refuse with the error code
`confirmation_required` until it is `true`.

The table below is a snapshot of the 91 tools reported by `ign mcp serve`
in ign 1.3.0. Another ign version may report a different set; ask your MCP
client to list tools for the authoritative answer.

| Tool | Description |
| --- | --- |
| `adopt` | Adopt this profile's gateway: native login → mint an Administrator-level API key (idempotent by name) → wire the gateway's read/write permissions → live-probe the key → persist the credential (OS keyring, env-var fallback). Re-run on an adopted gateway is an all-skip no-op. Composition flags ride the bootstrap: --project deploys the CLI's WebDev routes, --checkout lands every enabled project locally, --bake saves a restore-ready gwbk |
| `api_call` | Call any gateway REST endpoint raw: `--method`/`--path` are the request, `--data`/`--header`/`--query` shape it, and the envelope's `data.result.data` is the gateway's JSON VERBATIM (no field dropped, no value coerced, key order preserved — the README's documented contract exception). Auth-pattern headers (`Authorization`, `X-Ignition-API-Token`, `Cookie`) are refused pre-I/O — credentials come from the profile |
| `backup_download` | Download a gwbk backup (streamed to disk) |
| `backup_restore` | Restore a gwbk onto THIS gateway — destructive, refused without --yes; the gateway restarts and blocks for minutes after the restore |
| `connections` | List database/OPC connections with healthcheck status as reported |
| `diagnostics_bundle_download` | Download the bundle ZIP (streamed to disk; the request rides a 300 s per-request timeout — the 30 s client default would truncate MB-sized bundles) |
| `diagnostics_bundle_generate` | Start bundle generation (POST, no body) — the 200 answer IS the fresh status (live capture: `{"state":"Generating"}`); generation takes ~2–6 s on a fresh rig, so pair with `wait` |
| `diagnostics_bundle_status` | The bundle status: `state` rides the CAPTURED vocabulary (`Generating` / `Valid` — unknown future states pass through verbatim, never refused); `fileSize` (bytes) appears only when `Valid` |
| `diagnostics_bundle_wait` | Poll the status until a terminal captured state (`Valid`) — an UNKNOWN state (outside the captured vocabulary) keeps polling honestly until the deadline; deadline expiry is exit 4 `network_error` (the restart-wait convention, no new slug) with the last observed state in the message |
| `doctor` | Diagnose the gateway setup: URL, liveness, commissioning, auth, permissions, write, WebDev route, rig — exits 0 whenever the diagnosis completes (failing checks are data) |
| `e2e_doctor` | Diagnose the browser-E2E setup: node (≥20), npm, @playwright/test in the scaffold, a downloaded chromium, the gateway's testing bundle, and the gateway's trial state. Read-only and offline-safe — **exits 0 whenever the diagnosis completes**, so every finding is a `checks[]` row rather than an exit code. The two gateway rows report `skip` when no profile resolves or no --project is given |
| `e2e_init` | Scaffold a Playwright E2E suite into DIR (default ./e2e): a runner config, a global setup that logs in through `ign session login` and gates on `ign testing run`, gateway tag/ script helpers, an example suite, a .gitignore, and a README — then `npm install`. **Idempotent**: an existing file is reported `skipped` and never overwritten. Requires the global --yes; without it the verb writes nothing, spawns nothing, and refuses exit 2 after previewing every file and both commands |
| `eam_history` | EAM task run history (the gateway's own newest-first order) |
| `eam_task_cancel` | Cancel a task's PENDING execution (TASK-scoped). Refused exit 2 without --yes with the blast-radius preview in the message; nothing pending is an honest no-op (`fired: false`), a `canCancel: false` row reports the gateway's own refusal |
| `eam_task_delete` | Delete a task definition — signature-keyed (the gateway refuses a stale signature), behind the same --yes guard. Refused exit 2 without --yes with the blast-radius preview in the message |
| `eam_task_force` | Force-dispatch a task NOW — destructive, refused without --yes (it dispatches to the agent targets immediately). The confirmation prompt (and every refusal) carries the blast-radius preview line |
| `eam_task_modify` | Rewrite targeted keys of a task definition — the full-record read-modify-write (every key the gateway answered rides back; only the targeted keys change). Rename is deliberately ABSENT (the wire answers PUT-rename with 404 — see README's create-new + delete-old composite). Refused exit 2 without --yes with the blast-radius preview in the message |
| `eam_task_new` | Create a task definition (scheduleMode defaults to OnDemand — never auto-fires) |
| `eam_task_resume` | Resume a suspended task definition — the suspend inverse (TASK-scoped, like suspend). Refused exit 2 without --yes with the blast-radius preview in the message |
| `eam_task_suspend` | Suspend a task definition's scheduled dispatches — TASK-scoped runtime verb (there is NO agent-level suspend on the wire; an "agent" is suspended by suspending its tasks). Refused exit 2 without --yes, the blast-radius preview in the refusal message; on a stock gateway the runtime seam honestly refuses `eam_not_controller` (exit 6) |
| `eam_tasks` | Task definitions: bare `ign eam tasks` lists; with a name shows one definition + its scheduled state |
| `gan_status` | The GAN overview: total/running connections, in/out byte rates, remote gateways — all zeros are healthy data on a non-GAN gateway (the capture IS the canonical shape) |
| `license_status` | License inventory + trial state in ONE command: the hardware-key item rows and effective stamp ride the `/licenses` read, the license mode + countdown ride the trial companion (the mode is NOT on the licenses payload — capture fact) |
| `lint` | Lint local project files by delegating to ignition-lint (PATH discovery) — doctor posture: findings are DATA, exit 0 whenever the tool ran; --strict passes the tool's exit code through for CI |
| `logs` | Query, tail, and download gateway logs; manage logger levels |
| `logs_download` | Download the log archive — a SQLite .idb, never a zip |
| `logs_loggers` | List loggers / manage logger levels |
| `logs_loggers_reset` | Reset ALL logger levels to defaults — refused without --yes |
| `logs_loggers_set` | Set one logger's level — a mutation, refused without --yes |
| `metrics` | Gateway performance metrics (current gauges + thread counts) |
| `modules` | List gateway modules (healthy by default) |
| `profile_add` | Add (or overwrite) a gateway profile |
| `profile_list` | List configured profiles |
| `profile_use` | Switch the active profile |
| `project_copy` | Copy a project with all its resources |
| `project_delete` | Delete a project — destructive, refused without --yes |
| `project_diff` | Compare a project across two gateway profiles — statuses are B-relative-to-A (`added` = in B only, `removed` = in A only, `changed` = differing after resource.json normalization) |
| `project_export` | Export a project as a ZIP archive (streams to disk) |
| `project_import` | Import a project from a ZIP archive |
| `project_list` | List every runnable project: name, title, enabled, parent, inheritable (inheritance info from the items themselves) |
| `project_new` | Create a project (only provided fields ride the create body) |
| `project_rename` | Rename a project (native rename, not copy+delete) |
| `project_set` | Set project fields — --parent IS the inheritance move (reparent) |
| `project_sync` | Promote selected resources from profile A into profile B (direction is ALWAYS A→B) — destructive on B: the whole project is overwrite-imported, refused without --yes |
| `redundancy_status` | The flat redundancy status: role, project state, peer connection, config access, sync/failover pending, uptime (ms since gateway start — capture-proven) and last-sync (the `-1` never-synced sentinel on fresh rigs) |
| `resource_delete` | Delete one resource — destructive, refused without --yes |
| `resource_get` | Read one resource: JSON pretty-printed, text raw — binary (data.bin-class) resources refuse with exit 6 |
| `resource_list` | List a project's resources (one path per line in human mode) |
| `resource_put` | Write one resource (upsert: created if absent, replaced if present) — JSON if parseable (application/json), else UTF-8 text (text/plain); binary-looking input refuses |
| `restart` | Restart the gateway — destructive, refused without --yes; --wait polls until RUNNING |
| `rig_down` | Stop the rig (compose down --remove-orphans; volumes KEPT — `reset` owns the teardown half) |
| `rig_logs` | Stream the rig's container logs (compose logs passthrough — raw lines, no envelope in any mode; the third streaming exception, README-documented) |
| `rig_reset` | Tear the rig down AND remove its volumes (down -v --remove-orphans), then bring it back up fresh — destructive, refused without --yes; no stale project/trial state survives |
| `rig_restore` | Restore a gwbk onto the rig's gateway — destructive, refused without --yes; synchronous restore + restart, then a witnessed RUNNING wait |
| `rig_snapshot` | Snapshot the rig's gateway: native gwbk (roaming backup, streamed) + per-project exports + manifest.json, composed in a timestamped directory — repeatable state |
| `rig_status` | Structured status: services, ports, volumes (allowlist JSON; a down rig is exit-0 data) |
| `rig_trial_reset` | Reset an EXPIRED trial to a fresh window — destructive, refused without --yes. Mechanism ladder: API-token POST (IGNITION_TOKEN) → native gateway login (--user / IGNITION_USER + IGNITION_PASSWORD). Non-expired trials refuse (trial_not_expired) |
| `rig_trial_status` | Show the trial state: licenseMode, trialState, seconds left, expired — plus the banners cross-check. No credential needed (the endpoints answer unauthenticated — fresh-rig friendly) |
| `rig_up` | Bring the rig up (compose up -d --wait) and wait for the gateway: RUNNING, or uncommissioned-as-data (exit 0 + wizard hint in warnings) |
| `script_run` | Execute gateway-side Python (Jython) — non-interactive, the route's entire purpose |
| `session_login` | Log in to the gateway and return the live session: the `webui-sid-*` cookie name and value, the CSRF token for `X-CSRF-Token`, the gateway URL, and `storage_state` — a Playwright `storageState` document ready to write straight to disk and point `use.storageState` at. The password is env-only (`IGNITION_PASSWORD`; missing exits 3, rejected exits 5). The cookie value and CSRF token are exposed ONLY under the global --json flag |
| `sessions` | List gateway sessions (designers, Perspective, Vision) — or terminate one via the `terminate` subcommand |
| `sessions_terminate` | Terminate (designer: prune / vision: close) a session — destructive, refused without --yes |
| `status` | Gateway status: identity, platform, uptime, license (incl. trial countdown) |
| `tags_alarms_ack` | Acknowledge alarms (explicit --username: the 3-arg wire form needs it). NOT --yes-guarded — acknowledging never un-acknowledges anything |
| `tags_alarms_active` | List active alarms — eventId/source/state/priority/name |
| `tags_alarms_history` | Query alarm history — requires a journal-provisioned gateway (default rigs refuse with the provisioning hint naming the missing chain) |
| `tags_browse` | Browse tags as a tree (Property children filtered by default) — providers appear at the root; needs the deployed routes (`ign webdev deploy`) — or run fully OFFLINE against an export via --from-export |
| `tags_config_create` | Create a tag from a JSON definition file (`-` = stdin) — aborts on an existing node (collision policy 'a') |
| `tags_config_delete` | Delete tag configurations — destructive, refused without --yes (the guard fires before ANY resolution: zero network work) |
| `tags_config_get` | Get a tag's configuration as (pretty) JSON — stringified value/defaultValue sub-dicts re-parsed into real JSON |
| `tags_export` | Export tag subtrees — json writes the gateway's native JSON interchange (the lossless round-trip); xml passes the gateway's own XML through byte-for-byte; csv is CLI-GENERATED and LOSSY (no alarms, legacy 48-column set, numeric enums — the gateway cannot export CSV) |
| `tags_history_query` | Query historical tag values — t_stamp + one column per tag; structurally safe anywhere (data requires a provisioned historian) |
| `tags_import` | Import a tag export into a target provider — json is the native interchange; xml/csv ride the gateway's importTags passthrough. A loss scan reports what xml/csv would drop or coerce BEFORE the import and refuses exit 2 unless --yes. Collision behavior: abort (default) refuses on collisions; overwrite replaces them (destructive: requires --yes) |
| `tags_provider_create` | Create a STANDARD tag provider (DB-backed providers are out of scope at MVP) |
| `tags_provider_delete` | Delete a tag provider — destructive, refused without --yes |
| `tags_provider_list` | List the gateway's tag providers (tag counts + health) |
| `tags_read` | Read one or more tag values (quality and timestamp included) — needs the deployed routes |
| `tags_udt_def` | Get a UDT definition (parameters + nested children, recursive) |
| `tags_udt_types` | List the provider's UDT types |
| `tags_write` | Write a value to a tag — the value is parsed as a JSON scalar (number/bool/null); anything unparseable is sent as a string; arrays/objects refuse — needs the deployed routes |
| `testing_run` | Run the gateway-side Jython test suite and return the machine verdict (exit 0 green, exit 6 red with the FULL results still in the envelope) |
| `version` | Print version information (CLI always; gateway check when a profile resolves) |
| `wait_gateway` | Wait until the gateway reports RUNNING (unauthenticated StatusPing — works even when auth is broken or absent) |
| `wait_module` | Wait until a module reports ACTIVE |
| `wait_restart` | Wait for a restart to complete — restart-aware: shares `restart --wait`'s semantics (non-RUNNING observed once → RUNNING; a 5 s floor guards the all-RUNNING case) |
| `webdev_deploy` | Deploy the embedded route bundle into the dedicated project (overwrite-replace — the CLI owns that project wholesale) |
| `webdev_status` | Probe every route's version handshake — a READ: exit 0 whenever the sweep completes, per-route degradation is data |
| `workspace_checkout` | Check out a project's resources to a local tree — mapped paths + the recorded `.ign-workspace.json` manifest + an idempotent `.gitignore` (manifest committed; codec artifacts ignored). Read-only on the wire: one export GET, zero imports |
| `workspace_push` | Push local edits to the gateway — guarded (refused without --yes; the refusal message IS the blast-radius preview); conflicts refuse EVEN WITH --yes (manual reconciliation); deletions need --delete (default: reported, skipped); untracked files are never imported; an empty selection writes nothing |
| `workspace_status` | Report workspace drift against the gateway — states are PUSH-RELATIVE (each row names what push would do: write / leave / refuse); the project comes from the workspace manifest, never re-typed. Read-only: one export GET |

## Result shapes

Composite tools do not return an ign envelope. They return their own object:

```json
{"ok": true, "steps": [{"tool": "status", "ok": true, "code": null}]}
```

`steps` records every ign call the composite made, in order. On failure the result
also carries `step` (the ign tool that failed) and `error` (that tool's ign
envelope), and the call is reported to the client as an error:

```json
{"ok": false, "steps": ["..."], "step": "project_sync", "error": {"ok": false, "profile": "uat", "error": {"code": "...", "message": "...", "endpoint": null, "hint": null}}}
```

A composite that refuses rather than forwarding an ign failure uses the same shape
with `step: null` and a synthesized error code: `confirmation_required` from
`rig_fresh` called without `confirm: true`, `nothing_to_promote` from
`deploy_project` when the two profiles already match, `workspace_conflict` and
`nothing_to_push` from `push_workspace` when a member changed on both sides or the
workspace already matches the gateway, and `verification_failed` from
`deploy_project` or `push_workspace` when the check taken after the push still
shows changes that did not land.
