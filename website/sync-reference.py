#!/usr/bin/env python3
"""Regenerate docs/configuration.md and docs/reference.md from the server source.

Runs under plain python3 with the standard library only: the docs CI job has Node
but no Python dependencies. Nothing here imports the server or talks to a gateway.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "ignition_mcp"
DOCS = ROOT / "docs"
CATALOG = DOCS / "_generated" / "ign-catalog.json"

DASH = "—"

SUCCESS_ENVELOPE = '{"ok": true, "profile": "uat", "data": {"...": "..."}}'
FAILURE_ENVELOPE = (
    '{"ok": false, "profile": "uat", '
    '"error": {"code": "...", "message": "...", "endpoint": null, "hint": null}}'
)

Func = ast.FunctionDef | ast.AsyncFunctionDef


def die(message: str) -> None:
    print(f"sync-reference: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse(path: Path) -> ast.Module:
    if not path.is_file():
        die(f"missing source file: {path}")
    return ast.parse(path.read_text())


def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def cell(text: str) -> str:
    """One markdown table cell: no newlines, no unescaped pipes."""
    return " ".join(str(text).split()).replace("|", "\\|")


def find_function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    die(f"could not find `def {name}`")
    raise AssertionError("unreachable")


def signature(node: Func) -> str:
    args = node.args.args
    defaults: list[ast.expr | None] = [None] * (len(args) - len(node.args.defaults))
    defaults += list(node.args.defaults)
    rendered = []
    for arg, default in zip(args, defaults):
        part = arg.arg
        if arg.annotation is not None:
            part += ": " + ast.unparse(arg.annotation)
        if default is not None:
            part += " = " + ast.unparse(default)
        rendered.append(part)
    return f"{node.name}({', '.join(rendered)})"


def first_paragraph(node: Func) -> str:
    doc = ast.get_docstring(node) or ""
    return " ".join(doc.split("\n\n")[0].split())


def takes_confirm(node: Func) -> bool:
    return any(arg.arg == "confirm" for arg in node.args.args)


# -- configuration.md --------------------------------------------------------


def cli_flags() -> dict[str, str]:
    """Settings field name -> the `ign-mcp` flag that overrides it."""
    flags: dict[str, str] = {}
    for node in ast.walk(parse(SRC / "cli.py")):
        if not isinstance(node, ast.Call) or getattr(node.func, "attr", "") != "add_argument":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        flag = node.args[0].value
        if isinstance(flag, str) and flag.startswith("--"):
            flags[flag[2:].replace("-", "_")] = flag
    return flags


def settings_rows() -> list[tuple[str, str, str, str]]:
    flags = cli_flags()
    rows: list[tuple[str, str, str, str]] = []
    for node in ast.walk(parse(SRC / "config.py")):
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue
        name = node.target.id
        if name == "model_config":
            continue
        env = ""
        default: object = None
        if isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "Field":
            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
            env = str(kwargs.get("validation_alias") or "")
            default = kwargs.get("default")
        elif node.value is not None:
            default = ast.literal_eval(node.value)
        flag = flags.get(name, "")
        if not flag:
            env = ""  # no flag means it is not a documented override
        elif not env:
            env = "IGN_MCP_" + name.upper()
        rows.append((name, env, flag, "" if default is None else str(default)))
    if not rows:
        die("no Settings fields found in config.py")
    return rows


def configuration_md() -> str:
    lines = [
        "# Configuration",
        "",
        "Generated from the server source by `website/sync-reference.py`. Do not edit by hand.",
        "",
        "`ign-mcp` has four settings. Each takes a command-line flag or an environment",
        "variable, and the flag wins when both are set. Everything about the gateway itself",
        "(address, credentials, TLS) belongs to `ign`, not to this server.",
        "",
        "| Setting | Env var | CLI flag | Default |",
        "| --- | --- | --- | --- |",
    ]
    for name, env, flag, default in settings_rows():
        lines.append(
            f"| `{name}` | {f'`{env}`' if env else DASH} "
            f"| {f'`{flag}`' if flag else DASH} "
            f"| {f'`{default}`' if default else DASH} |"
        )
    lines += [
        "",
        "With neither `--profile` nor `IGNITION_PROFILE` set, the server starts",
        "`ign mcp serve` without a `--profile` argument and ign uses its own active profile.",
        "`min_ign_version` is not an override: it records the lowest ign version the server",
        "accepts, and startup fails when the ign on PATH is older.",
        "",
        "```sh",
        "uv run ign-mcp --profile uat --port 8765",
        "IGNITION_PROFILE=uat IGN_BIN=/opt/homebrew/bin/ign uv run ign-mcp",
        "```",
        "",
        "## Gateway credentials",
        "",
        "This server never reads a gateway credential. It launches `ign mcp serve` as a child",
        "process with the current environment, and ign resolves the credential for the",
        "profile it serves, in this order: `IGNITION_TOKEN_<PROFILE>`, then the profile's own",
        "`token_env` variable, then `IGNITION_TOKEN`, then the OS keyring, then",
        "`IGNITION_USER` with `IGNITION_PASSWORD`.",
        "",
        "Environment tokens come before the keyring. A bare `IGNITION_TOKEN` exported in your",
        "shell is therefore used for every profile and silently overrides the keyring",
        "credential the profile was adopted with. If calls fail with `auth_rejected` on a",
        "profile that works from the terminal, unset `IGNITION_TOKEN` and start the server",
        "again.",
        "",
        "Run `ign profile --help` to inspect or change profiles.",
    ]
    return "\n".join(lines)


# -- reference.md ------------------------------------------------------------


def composite_section() -> list[str]:
    register = find_function(parse(SRC / "workflows.py"), "register_workflows")
    tools = [n for n in register.body if isinstance(n, ast.AsyncFunctionDef)]
    if not tools:
        die("no composite tools found in register_workflows")
    lines = [
        "## Composite tools",
        "",
        "Defined in this server, not in ign. Each chains several ign calls and returns one",
        "result. See [Result shapes](#result-shapes) for the object they return.",
        "",
    ]
    for node in tools:
        lines += [
            f"### `{node.name}`",
            "",
            "```python",
            signature(node),
            "```",
            "",
            first_paragraph(node),
            "",
        ]
        if takes_confirm(node):
            lines += [
                f"Takes `confirm`. `{node.name}` does not change anything until it is `true`.",
                "",
            ]
    return lines


def resources_section() -> list[str]:
    register = find_function(parse(SRC / "resources.py"), "register_resources")
    rows: list[tuple[str, str, str]] = []
    for node in ast.walk(register):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "static"
            and len(node.args) == 3
        ):
            uri, tool, description = (ast.literal_eval(a) for a in node.args)
            rows.append((uri, tool, description))
    for node in register.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        uri = ""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and decorator.args:
                uri = ast.literal_eval(decorator.args[0])
        tool = ""
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and getattr(inner.func, "attr", "") == "call"
                and inner.args
                and isinstance(inner.args[0], ast.Constant)
            ):
                tool = inner.args[0].value
        rows.append((uri, tool, first_paragraph(node)))
    if not rows:
        die("no resources found in register_resources")
    lines = [
        "## Resources",
        "",
        "Read-only mirrors of the most-polled ign reads. Each read returns the ign envelope",
        "as JSON.",
        "",
        "| URI | ign tool | Contents |",
        "| --- | --- | --- |",
    ]
    lines += [f"| `{uri}` | `{tool}` | {cell(desc)} |" for uri, tool, desc in rows]
    return lines


def prompts_section() -> list[str]:
    register = find_function(parse(SRC / "prompts.py"), "register_prompts")
    prompts = [n for n in register.body if isinstance(n, ast.FunctionDef)]
    if not prompts:
        die("no prompts found in register_prompts")
    lines = [
        "## Prompts",
        "",
        "Runbooks. Each returns text naming the tools to call, in order, and the composite",
        "that shortcuts them.",
        "",
        "| Prompt | Purpose |",
        "| --- | --- |",
    ]
    lines += [f"| `{signature(p)}` | {cell(first_paragraph(p))} |" for p in prompts]
    return lines


def proxied_section() -> list[str]:
    lines = [
        "## Proxied ign tools",
        "",
        "Every tool named like an ign verb is forwarded to `ign mcp serve` unchanged, with",
        "ign's input schema and ign's result. A successful call returns:",
        "",
        "```json",
        SUCCESS_ENVELOPE,
        "```",
        "",
        "A failed call returns:",
        "",
        "```json",
        FAILURE_ENVELOPE,
        "```",
        "",
        "Destructive verbs carry a `confirm` boolean and refuse with the error code",
        "`confirmation_required` until it is `true`.",
        "",
    ]
    if not CATALOG.is_file():
        lines += [
            "The catalog is whatever the `ign mcp serve` on your PATH reports. Ask your MCP",
            "client to list tools to see it.",
        ]
        return lines
    data = json.loads(CATALOG.read_text())
    tools = data.get("tools", [])
    version = data.get("ign_version", "")
    lines += [
        f"The table below is a snapshot of the {len(tools)} tools reported by `ign mcp serve`",
        f"in ign {version}. Another ign version may report a different set; ask your MCP",
        "client to list tools for the authoritative answer.",
        "",
        "| Tool | Description |",
        "| --- | --- |",
    ]
    lines += [
        f"| `{cell(tool['name'])}` | {cell(tool.get('description', ''))} |"
        for tool in sorted(tools, key=lambda t: t["name"])
    ]
    return lines


def result_shapes_section() -> list[str]:
    return [
        "## Result shapes",
        "",
        "Composite tools do not return an ign envelope. They return their own object:",
        "",
        "```json",
        '{"ok": true, "steps": [{"tool": "status", "ok": true, "code": null}]}',
        "```",
        "",
        "`steps` records every ign call the composite made, in order. On failure the result",
        "also carries `step` (the ign tool that failed) and `error` (that tool's ign",
        "envelope), and the call is reported to the client as an error:",
        "",
        "```json",
        '{"ok": false, "steps": ["..."], "step": "project_sync", "error": '
        + FAILURE_ENVELOPE
        + "}",
        "```",
        "",
        "A composite that refuses rather than forwarding an ign failure uses the same shape",
        "with `step: null` and a synthesized error code: `confirmation_required` from",
        "`rig_fresh` called without `confirm: true`, `nothing_to_promote` from",
        "`deploy_project` when the two profiles already match, and `verification_failed`",
        "from `deploy_project` when the diff taken after the sync still shows added or",
        "changed resources.",
    ]


def reference_md() -> str:
    lines = [
        "# Tool reference",
        "",
        "Generated from the server source by `website/sync-reference.py`. Do not edit by hand.",
        "",
        "The server exposes three things it defines itself (composite tools, `ign://`",
        "resources, prompts) and one thing it forwards (every tool from `ign mcp serve`).",
        "",
    ]
    lines += composite_section()
    lines += [""] + resources_section()
    lines += [""] + prompts_section()
    lines += [""] + proxied_section()
    lines += [""] + result_shapes_section()
    return "\n".join(lines)


def main() -> None:
    if not DOCS.is_dir():
        die(f"missing docs directory: {DOCS}")
    write(DOCS / "configuration.md", configuration_md())
    write(DOCS / "reference.md", reference_md())


if __name__ == "__main__":
    main()
