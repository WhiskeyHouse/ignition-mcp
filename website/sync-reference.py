import ast
from pathlib import Path


def root(name):
    return Path(__file__).resolve().parent.parent


def write(name, path, text):
    (root(name) / path).write_text(text.strip() + "\n")


# Generate references without loading credentials or executing tools.
tree = ast.parse((root("ignition-mcp") / "src/ignition_mcp/config.py").read_text())
rows = []
for node in ast.walk(tree):
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "id", "") == "Field"
    ):
        args = {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
        rows.append(
            f"| `IGNITION_MCP_{node.target.id.upper()}` | `{args.get('default', '')}` | "
            f"{args.get('description', '')} |"
        )
write(
    "ignition-mcp",
    "docs/configuration.md",
    "# Configuration\n\nSettings load from environment variables and the checkout’s `.env` file. "
    "The variables below match `src/ignition_mcp/config.py`.\n\n"
    "| Variable | Default | Purpose |\n| --- | --- | --- |\n"
    + "\n".join(rows)
    + "\n\nUse an API token for native gateway REST access. "
    "Leave optional WebDev paths empty until their gateway resources are deployed. "
    "Keep TLS verification enabled for normal use.\n\n"
    "See [installation](installation.md) and [WebDev setup](webdev-setup.md).",
)
parts = [
    "# Tool reference",
    "Function signatures and descriptions from `src/ignition_mcp/tools/`. "
    "The `ctx` parameter is supplied by the MCP server and is omitted below. "
    "Registration is defined in each module.",
]
for p in sorted((root("ignition-mcp") / "src/ignition_mcp/tools").glob("*.py")):
    for node in ast.parse(p.read_text()).body:
        if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
            args = []
            defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + node.args.defaults
            for arg, default in zip(node.args.args, defaults):
                if arg.arg == "ctx":
                    continue
                args.append(
                    arg.arg
                    + (": " + ast.unparse(arg.annotation) if arg.annotation else "")
                    + (" = " + ast.unparse(default) if default is not None else "")
                )
            parts.extend(
                [
                    "## " + node.name,
                    "```python\n" + node.name + "(" + ", ".join(args) + ")\n```",
                    ast.get_docstring(node) or "See the source implementation.",
                ]
            )
write("ignition-mcp", "docs/api-reference.md", "\n\n".join(parts))
