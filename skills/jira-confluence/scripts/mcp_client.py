#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "httpx>=0.27",
#   "httpx-sse>=0.4",
#   "pyyaml>=6.0",
#   "pyobjc-framework-Security>=10.0; sys_platform == 'darwin'",
#   "pyobjc-framework-LocalAuthentication>=10.0; sys_platform == 'darwin'",
# ]
# requires-python = ">=3.12"
# ///
"""
Python MCP client for Atlassian MCP server.

This module implements the Model Context Protocol (MCP) to communicate
with mcp.atlassian.com using Streamable HTTP transport.

Usage:
    # List available tools
    python mcp_client.py list-tools

    # Call a specific tool
    python mcp_client.py call <tool_name> '{"arg": "value"}'
"""

import argparse
import json
import sys
import threading
import time
from typing import Any

import httpx
import yaml

# Import token functions from oauth module
from oauth import get_valid_token, AuthenticationError

# Import shared utilities
from common import yaml_output

# Import configuration
from config import MCP_URL, MCP_PROTOCOL_VERSION


class MCPError(Exception):
    """Base exception for MCP errors."""

    pass


class ProtocolError(MCPError):
    """MCP protocol error."""

    pass


class AtlassianMCPClient:
    """
    Python client for Atlassian MCP server.

    Implements MCP protocol over Streamable HTTP transport.
    The server requires:
    1. GET /v1/sse to establish SSE connection and receive session ID
    2. POST /v1/sse with Mcp-Session-Id header to send messages
    """

    def __init__(self, token: str | None = None):
        """
        Initialize MCP client.

        Args:
            token: OAuth access token. If None, reads from our OAuth storage.
        """
        if token:
            self.token = token
        else:
            try:
                self.token = get_valid_token()
            except AuthenticationError as e:
                raise AuthenticationError(
                    f"No token found: {e}. Run 'auth.py login' first."
                )

        self.session_id: str | None = None
        self._session_url: str | None = None
        self.request_id = 0
        self._initialized = False
        self._responses: dict[int, dict] = {}
        self._sse_thread: threading.Thread | None = None
        self._stop_sse = threading.Event()

    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _start_sse_listener(self):
        """Start background thread to listen for SSE events."""

        def listen():
            try:
                with httpx.Client(timeout=None) as client:
                    headers = self._get_headers()
                    headers["Accept"] = "text/event-stream"

                    # Use the session URL if we have one
                    url = self._session_url or MCP_URL

                    with client.stream(
                        "GET",
                        url,
                        headers=headers,
                    ) as response:
                        current_event = None
                        # Read SSE events
                        for line in response.iter_lines():
                            if self._stop_sse.is_set():
                                break

                            # Parse SSE format
                            if line.startswith("event:"):
                                current_event = line[6:].strip()
                            elif line.startswith("data:"):
                                data = line[5:].strip()
                                if data:
                                    # Handle endpoint event (contains session URL)
                                    if current_event == "endpoint":
                                        # data is like: /v1/sse?sessionId=XXX
                                        if "sessionId=" in data:
                                            session_id = data.split("sessionId=")[
                                                1
                                            ].split("&")[0]
                                            self.session_id = session_id
                                            self._session_url = (
                                                f"https://mcp.atlassian.com{data}"
                                            )
                                    else:
                                        # Try to parse as JSON-RPC response
                                        try:
                                            msg = json.loads(data)
                                            if "id" in msg:
                                                self._responses[msg["id"]] = msg
                                        except json.JSONDecodeError:
                                            pass
                            elif line == "":
                                current_event = None
            except Exception as e:
                if not self._stop_sse.is_set():
                    print(f"SSE listener error: {e}", file=sys.stderr)

        self._sse_thread = threading.Thread(target=listen, daemon=True)
        self._sse_thread.start()

    def connect(self) -> str:
        """
        Establish SSE connection and get session ID.

        Returns:
            Session ID
        """
        # Start SSE listener in background
        self._start_sse_listener()

        # Wait for session ID
        timeout = 10
        start = time.time()
        while not self.session_id and time.time() - start < timeout:
            time.sleep(0.1)

        if not self.session_id:
            raise ProtocolError("Failed to get session ID from SSE connection")

        return self.session_id

    def _send_request_impl(
        self,
        method: str,
        params: dict | None = None,
        request_id: int | None = None,
        timeout: float = 30.0,
    ) -> dict:
        """
        Send JSON-RPC request to MCP server (implementation).

        Args:
            method: MCP method name (e.g., "tools/list", "tools/call")
            params: Method parameters
            request_id: Request ID (generated if not provided)
            timeout: Timeout for waiting for response

        Returns:
            JSON-RPC result

        Raises:
            ProtocolError: On protocol errors
            AuthenticationError: On auth errors
        """
        # Ensure we have a session
        if not self.session_id:
            self.connect()

        if request_id is None:
            request_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            payload["params"] = params

        # Use session URL for POST requests
        url = self._session_url or MCP_URL

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Run 'auth.py login' to refresh token."
                )

            if response.status_code == 404:
                # Try reconnecting
                self.session_id = None
                self._session_url = None
                self.connect()
                url = self._session_url or MCP_URL
                response = client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                )

            if response.status_code not in (200, 202):
                raise ProtocolError(f"HTTP {response.status_code}: {response.text}")

            content_type = response.headers.get("Content-Type", "")

            # Handle SSE response
            if "text/event-stream" in content_type:
                return self._parse_sse_response(response.text, request_id)

            # Handle JSON response
            if "application/json" in content_type:
                result = response.json()
                if "error" in result:
                    raise ProtocolError(f"JSON-RPC error: {result['error']}")
                return result.get("result", {})

            # 202 Accepted - wait for response via SSE
            if response.status_code == 202:
                return self._wait_for_response(request_id, timeout=timeout)

            raise ProtocolError(f"Unexpected content type: {content_type}")

    def _parse_sse_response(self, text: str, request_id: int) -> dict:
        """Parse SSE response to extract JSON-RPC result."""
        result = None
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data:
                    try:
                        parsed = json.loads(data)
                        if parsed.get("id") == request_id:
                            if "result" in parsed:
                                result = parsed["result"]
                            elif "error" in parsed:
                                raise ProtocolError(
                                    f"JSON-RPC error: {parsed['error']}"
                                )
                    except json.JSONDecodeError:
                        continue

        if result is None:
            raise ProtocolError("No valid response in SSE stream")

        return result

    def _wait_for_response(self, request_id: int, timeout: float = 30.0) -> dict:
        """Wait for response to arrive via SSE."""
        start = time.time()
        while time.time() - start < timeout:
            if request_id in self._responses:
                msg = self._responses.pop(request_id)
                if "result" in msg:
                    return msg["result"]
                elif "error" in msg:
                    raise ProtocolError(f"JSON-RPC error: {msg['error']}")
            time.sleep(0.1)
        raise ProtocolError(f"Timeout waiting for response to request {request_id}")

    def _send_request_with_retry(self, method: str, params: dict | None = None) -> dict:
        """
        Send request with automatic retry on timeout.

        First attempt: 2 second timeout (fast fail for connection issues)
        On timeout: Check auth, reconnect, retry with 20 second timeout
        """
        # First attempt with short timeout
        try:
            return self._send_request_impl(method, params, timeout=2.0)
        except ProtocolError as e:
            if "Timeout" not in str(e):
                raise  # Re-raise non-timeout errors

            # Timeout occurred - try to recover
            print("Connection timeout, reconnecting...", file=sys.stderr)

            # Check auth status
            try:
                self.token = get_valid_token()
            except AuthenticationError:
                raise AuthenticationError(
                    "Authentication expired during retry. Run 'auth.py login'"
                )

            # Reset connection state and reconnect
            self.close()
            self.session_id = None
            self._session_url = None
            self._initialized = False
            self._responses = {}

            # Reinitialize
            self.initialize()

            # Retry with longer timeout
            try:
                return self._send_request_impl(method, params, timeout=20.0)
            except ProtocolError as retry_error:
                if "Timeout" in str(retry_error):
                    raise ProtocolError(
                        f"Request timed out after retry. "
                        f"The Atlassian MCP server may be slow or unavailable. "
                        f"Method: {method}"
                    )
                raise

    def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send request with automatic retry on timeout."""
        return self._send_request_with_retry(method, params)

    def close(self):
        """Close the SSE connection."""
        self._stop_sse.set()
        if self._sse_thread:
            self._sse_thread.join(timeout=2)

    def initialize(self) -> dict:
        """
        Send MCP initialize request.

        Returns:
            Server capabilities
        """
        params = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "atlassian-skill-python",
                "version": "1.0.0",
            },
        }
        result = self._send_request("initialize", params)
        self._initialized = True

        # Send initialized notification
        try:
            self._send_notification("notifications/initialized", {})
        except Exception:
            pass  # Notification may not be required

        return result

    def _send_notification(self, method: str, params: dict | None = None):
        """Send a notification (no response expected)."""
        if not self.session_id:
            self.connect()

        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            payload["params"] = params

        url = self._session_url or MCP_URL

        with httpx.Client(timeout=30.0) as client:
            client.post(
                url,
                json=payload,
                headers=self._get_headers(),
            )

    def list_tools(self) -> list[dict]:
        """
        List available tools on the MCP server.

        Returns:
            List of tool definitions
        """
        if not self._initialized:
            self.initialize()

        result = self._send_request("tools/list")
        return result.get("tools", [])

    def call_tool(
        self, name: str, arguments: dict | None = None, return_full_result: bool = False
    ) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments
            return_full_result: If True, return full MCP result including metadata

        Returns:
            Tool result content (or full result dict if return_full_result=True)
        """
        if not self._initialized:
            self.initialize()

        params = {"name": name}
        # Always include arguments (even if empty dict)
        if arguments is not None:
            params["arguments"] = arguments
        else:
            params["arguments"] = {}

        result = self._send_request("tools/call", params)

        # Return full result if requested (for debugging pagination)
        if return_full_result:
            return result

        # Extract content from result
        content = result.get("content", [])
        if content and len(content) == 1 and content[0].get("type") == "text":
            return content[0].get("text", "")
        return content


def cmd_list_tools(args):
    """List available MCP tools."""
    client = None
    try:
        client = AtlassianMCPClient()
        tools = client.list_tools()

        # Format output
        output = {
            "tools": [
                {
                    "name": t.get("name"),
                    "description": t.get("description", "")[:100],
                }
                for t in tools
            ],
            "count": len(tools),
        }
        yaml_output(output)

    except AuthenticationError as e:
        yaml.dump({"error": str(e)}, sys.stderr)
        sys.exit(1)
    except MCPError as e:
        yaml.dump({"error": str(e)}, sys.stderr)
        sys.exit(1)
    finally:
        if client:
            client.close()


def cmd_call_tool(args):
    """Call an MCP tool."""
    client = None
    try:
        client = AtlassianMCPClient()

        # Parse arguments
        arguments = None
        if args.arguments:
            try:
                arguments = json.loads(args.arguments)
            except json.JSONDecodeError as e:
                yaml.dump({"error": f"Invalid JSON arguments: {e}"}, sys.stderr)
                sys.exit(1)

        result = client.call_tool(args.tool_name, arguments)
        yaml_output({"result": result})

    except AuthenticationError as e:
        yaml.dump({"error": str(e)}, sys.stderr)
        sys.exit(1)
    except MCPError as e:
        yaml.dump({"error": str(e)}, sys.stderr)
        sys.exit(1)
    finally:
        if client:
            client.close()


def cmd_test(args):
    """Test MCP connection and list tools."""
    client = None
    try:
        print("Testing MCP connection to Atlassian...")

        client = AtlassianMCPClient()
        print(f"Token found: {client.token[:20]}...")

        print("\nConnecting to MCP server...")
        session_id = client.connect()
        print(f"Session ID: {session_id}")

        print("\nSending initialize request...")
        caps = client.initialize()
        print(f"Server: {caps.get('serverInfo', {})}")
        print(f"Protocol: {caps.get('protocolVersion', 'unknown')}")

        print("\nListing tools...")
        tools = client.list_tools()

        print(f"\nFound {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description', '')[:60]}...")

    except AuthenticationError as e:
        print(f"Auth error: {e}", file=sys.stderr)
        sys.exit(1)
    except MCPError as e:
        print(f"MCP error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if client:
            client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Atlassian MCP client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list-tools command
    subparsers.add_parser("list-tools", help="List available MCP tools")

    # call command
    call_parser = subparsers.add_parser("call", help="Call an MCP tool")
    call_parser.add_argument("tool_name", help="Name of the tool to call")
    call_parser.add_argument(
        "arguments",
        nargs="?",
        help="Tool arguments as JSON string",
    )

    # test command
    subparsers.add_parser("test", help="Test MCP connection")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "list-tools": cmd_list_tools,
        "call": cmd_call_tool,
        "test": cmd_test,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
