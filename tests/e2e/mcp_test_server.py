#!/usr/bin/env python3
"""
Simple MCP Test Server for E2E Testing.

A minimal MCP server implementation that provides test tools
for verifying MCP integration in NEST.

Usage:
    python mcp_test_server.py --port 7000

Provides tools:
- echo: Echoes back the input message
- add: Adds two numbers
- get_time: Returns current server time
"""

import argparse
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List


class MCPTestHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP test server."""

    # Available tools
    TOOLS = {
        "echo": {
            "name": "echo",
            "description": "Echoes back the input message",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to echo"}
                },
                "required": ["message"],
            },
        },
        "add": {
            "name": "add",
            "description": "Adds two numbers together",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        },
        "get_time": {
            "name": "get_time",
            "description": "Returns the current server time",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        "fail": {
            "name": "fail",
            "description": "Always fails - for testing error handling",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    }

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._send_json({"status": "ok", "server": "mcp-test-server"})
        elif self.path == "/sse":
            # SSE endpoint for MCP protocol
            self._send_sse_init()
        else:
            self._send_error(404, "Not found")

    def do_POST(self):
        """Handle POST requests (MCP JSON-RPC)."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
            return

        # Handle JSON-RPC request
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            # MCP initialize
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mcp-test-server", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            # List available tools
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": list(self.TOOLS.values())},
            }
        elif method == "tools/call":
            # Execute tool
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = self._execute_tool(tool_name, arguments)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        self._send_json(response)

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return result."""
        if tool_name == "echo":
            message = arguments.get("message", "")
            return f"Echo: {message}"
        elif tool_name == "add":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return f"Result: {a + b}"
        elif tool_name == "get_time":
            return f"Server time: {datetime.now().isoformat()}"
        elif tool_name == "fail":
            raise ValueError("This tool always fails for testing")
        else:
            return f"Unknown tool: {tool_name}"

    def _send_json(self, data: Dict):
        """Send JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, message: str):
        """Send error response."""
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse_init(self):
        """Initialize SSE connection."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        # Send initial event
        self.wfile.write(b'data: {"status": "connected"}\n\n')
        self.wfile.flush()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def main():
    """Run the MCP test server."""
    parser = argparse.ArgumentParser(description="MCP Test Server for E2E tests")
    parser.add_argument("--port", type=int, default=7000, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MCPTestHandler)
    print(f"MCP Test Server running on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
