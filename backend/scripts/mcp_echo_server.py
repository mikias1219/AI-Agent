#!/usr/bin/env python3
"""Minimal stdio MCP echo server for AURA tests and demo (INT-MCP-01).

Speaks newline-delimited JSON-RPC: initialize, tools/list, tools/call(echo).
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _reply(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = request.get("method")
        req_id = request.get("id")
        if method == "notifications/initialized" or req_id is None:
            continue
        if method == "initialize":
            _reply(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "aura-echo", "version": "0.1.0"},
                    },
                }
            )
            continue
        if method == "tools/list":
            _reply(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "echo",
                                "description": "Echo a message back (demo MCP tool).",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"message": {"type": "string"}},
                                    "required": ["message"],
                                },
                            }
                        ]
                    },
                }
            )
            continue
        if method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name != "echo":
                _reply(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Unknown tool {name}"},
                    }
                )
                continue
            text = str(arguments.get("message", ""))
            _reply(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                }
            )
            continue
        _reply(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )


if __name__ == "__main__":
    main()
