#!/bin/bash
cd "/Users/pmannion/Documents/whiskeyhouse/ignition-mcp"
source .venv/bin/activate
export PYTHONPATH="/Users/pmannion/Documents/whiskeyhouse/ignition-mcp/src:$PYTHONPATH"
python -m ignition_mcp.main