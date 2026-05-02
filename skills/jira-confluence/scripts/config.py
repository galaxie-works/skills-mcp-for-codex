# /// script
# dependencies = []
# requires-python = ">=3.12"
# ///
"""Configuration constants for Atlassian scripts."""

# Keychain service name for credential storage
SERVICE_NAME = "atlassian-claude-skill"

# MCP server configuration
MCP_URL = "https://mcp.atlassian.com/v1/sse"
MCP_PROTOCOL_VERSION = "2025-06-18"

# Timeouts in seconds
TIMEOUT_FAST = 2.0  # Initial attempt (fast fail for connection issues)
TIMEOUT_NORMAL = 30.0  # Standard operations
TIMEOUT_SLOW = 60.0  # Large operations (file uploads, bulk ops)
