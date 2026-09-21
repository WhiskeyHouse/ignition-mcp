---
sidebar_position: 3
title: Recorded walkthroughs
---

# Recorded walkthroughs

These are real terminal recordings of an isolated Ignition gateway with synthetic batch data. Playback runs at 1.2× with long idle pauses shortened. Use the player controls to pause, seek, or open fullscreen.

## Ignition MCP + Agent

An agent checks gateway health, discovers tags, reads batch conditions and traceability IDs, then discusses hold readiness and questions for the operator.

<div class="terminal-demo"><iframe class="terminal-demo-frame" src="/ignition-mcp/demos/index.html?demo=pi" title="Ignition MCP + Agent terminal walkthrough" loading="lazy" allowfullscreen></iframe></div>

[Download the terminal recording](pathname:///ignition-mcp/demos/pi.cast).

## About the sample

BlendTank01 uses fictional batch, material-lot, and enterprise-order identifiers. Temperature is 68.4°C against a 72°C setpoint, with agitation at 180 RPM. These are static memory tags; one snapshot cannot establish a trend or diagnose equipment.

The agent uses four read-only Ignition MCP tools: `status`, `project_list`, `tags_browse`, and `tags_read`. The walkthrough makes no changes to the gateway.
