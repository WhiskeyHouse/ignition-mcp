# First requests

After [connecting a client](quickstart.md), ask it to call `get_gateway_info` and summarize the returned gateway information. Inspect the tool result alongside the answer.

Use `get_module_health` to inspect module state or `list_projects` to list projects. These are useful first requests because they do not change the gateway configuration.

For runtime tag values, configure the relevant [WebDev endpoint](webdev-setup.md) before using `read_tags`. The [tool reference](api-reference.md) lists the current parameters and function documentation.

A response from a configured development gateway is needed to verify an end-to-end connection. Unit tests alone do not verify your gateway's routes or permissions.
