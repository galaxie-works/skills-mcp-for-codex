# /// script
# dependencies = [
#   "keyring>=25.0",
#   "pyyaml>=6.0"
# ]
# requires-python = ">=3.12"
# ///
"""
Shared utilities for Atlassian API scripts.
Provides HTTP client with automatic token refresh and YAML output formatting.
Supports both OAuth (pure Python) and Basic Auth (API token).
"""

import base64
import functools
import json
import sys
import time
from contextlib import contextmanager
from typing import Any, Callable, TextIO, Generator, NoReturn

import keyring
import yaml

# Import OAuth token handling
from oauth import (
    load_tokens,
    save_tokens,
    load_client_info,
    AtlassianMCPOAuth,
    OAuthError,
)

# Import configuration
from config import SERVICE_NAME


class AtlassianError(Exception):
    """Base exception for Atlassian API errors."""

    pass


class AuthenticationError(AtlassianError):
    """Token expired, invalid, or missing."""

    pass


class NotFoundError(AtlassianError):
    """Resource not found."""

    pass


class RateLimitError(AtlassianError):
    """API rate limit exceeded."""

    pass


class ConfigurationError(AtlassianError):
    """Missing configuration."""

    pass


def get_stored_value(key: str) -> str | None:
    """Retrieve a value from Keychain."""
    return keyring.get_password(SERVICE_NAME, key)


def set_stored_value(key: str, value: str) -> None:
    """Store a value in Keychain."""
    keyring.set_password(SERVICE_NAME, key, value)


def delete_stored_value(key: str) -> None:
    """Delete a value from Keychain."""
    try:
        keyring.delete_password(SERVICE_NAME, key)
    except keyring.errors.PasswordDeleteError:
        pass  # Key doesn't exist


def get_auth_type() -> str:
    """Get the configured authentication type ('basic' or 'oauth')."""
    return get_stored_value("auth_type") or "oauth"


def get_basic_auth_header() -> str:
    """
    Get Basic Auth header value for API token authentication.
    Raises AuthenticationError if credentials not configured.
    """
    email = get_stored_value("api_email")
    api_token = get_stored_value("api_token")

    if not email or not api_token:
        raise AuthenticationError(
            "API token not configured. Run: uv run scripts/auth.py setup-token"
        )

    auth_string = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return f"Basic {auth_string}"


def get_valid_token() -> str:
    """
    Get a valid OAuth access token, refreshing if necessary.
    Raises AuthenticationError if no valid token available.
    Only used for OAuth auth type.
    """
    tokens = load_tokens()
    if not tokens:
        raise AuthenticationError(
            "Not authenticated. Run: uv run scripts/auth.py login"
        )

    access_token = tokens.get("access_token")
    if not access_token:
        raise AuthenticationError(
            "No access token found. Run: uv run scripts/auth.py login"
        )

    expires_at = tokens.get("expires_at", 0)

    # Check if token is expired or expiring within 5 minutes
    if time.time() > expires_at - 300:
        # Try to refresh
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise AuthenticationError(
                "Token expired and no refresh token. Run: uv run scripts/auth.py login"
            )

        client_info = load_client_info()
        if not client_info:
            raise AuthenticationError(
                "No client info. Run: uv run scripts/auth.py login"
            )

        oauth = AtlassianMCPOAuth()
        try:
            new_tokens = oauth.refresh_tokens(refresh_token, client_info["client_id"])
            save_tokens(new_tokens)
            access_token = new_tokens["access_token"]
        except OAuthError as e:
            raise AuthenticationError(
                f"Token refresh failed: {e}. Run: uv run scripts/auth.py login"
            )

    return access_token


def get_cloud_id() -> str:
    """Get the stored cloud ID."""
    cloud_id = get_stored_value("cloud_id")
    if not cloud_id:
        raise ConfigurationError(
            "No cloud ID stored. Run: uv run scripts/auth.py login"
        )
    return cloud_id


def yaml_output(data: Any, stream: TextIO = sys.stdout) -> None:
    """
    Output data as YAML to stdout.
    Uses pure block style for all structures (no inline JSON-like formatting).
    """

    # Custom representer to force block style for dicts
    def represent_dict(dumper, data):
        return dumper.represent_mapping(
            "tag:yaml.org,2002:map", data.items(), flow_style=False
        )

    # Custom representer to force block style for lists
    def represent_list(dumper, data):
        return dumper.represent_sequence(
            "tag:yaml.org,2002:seq", data, flow_style=False
        )

    # Create custom dumper class
    class BlockStyleDumper(yaml.SafeDumper):
        pass

    BlockStyleDumper.add_representer(dict, represent_dict)
    BlockStyleDumper.add_representer(list, represent_list)

    yaml.dump(
        data,
        stream,
        Dumper=BlockStyleDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def error_output(message: str) -> NoReturn:
    """Output error message as YAML to stderr and exit."""
    yaml.dump({"error": message}, sys.stderr, default_flow_style=False)
    sys.exit(1)


# ---------------------------------------------------------------------------
# MCP Utilities - shared functions for MCP client operations
# ---------------------------------------------------------------------------


def parse_mcp_result(result: Any) -> tuple[dict | list | None, str | None]:
    """
    Parse MCP tool result, handling JSON strings, lists and error responses.

    Returns:
        (parsed_result, error_message) - error_message is None if no error
    """
    # Handle list of content blocks (MCP returns list when multiple content items)
    if isinstance(result, list) and result:
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "{}")
                try:
                    result = json.loads(text)
                    break
                except json.JSONDecodeError:
                    if "Failed to" in text or "Error" in text:
                        return None, text
                    return None, f"Invalid response: {text[:100]}"
        else:
            # No text block found
            return None, "No text content in MCP response"

    # Parse JSON string if needed
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            # Check if it looks like an error message
            if "Failed to" in result or "Error" in result:
                return None, result
            return None, f"Invalid response: {result[:100]}"

    # Check for MCP error response format: {"error": true, "message": "..."}
    if isinstance(result, dict) and result.get("error"):
        return None, result.get("message", "Operation failed")

    return result, None


@contextmanager
def mcp_client_context() -> Generator[Any, None, None]:
    """
    Context manager for MCP client lifecycle.

    Usage:
        with mcp_client_context() as client:
            result = client.call_tool(...)

    Yields:
        AtlassianMCPClient instance
    """
    # Import here to avoid circular imports
    from mcp_client import AtlassianMCPClient

    client = AtlassianMCPClient()
    try:
        yield client
    finally:
        client.close()


def command_handler(func: Callable) -> Callable:
    """
    Decorator for consistent error handling in CLI commands.

    Handles AuthenticationError, MCPError, and generic exceptions,
    outputting errors in YAML format and exiting with code 1.
    """
    # Import here to avoid circular imports
    from mcp_client import MCPError, AuthenticationError as MCPAuthError

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (AuthenticationError, MCPAuthError) as e:
            yaml.dump(
                {
                    "error": {
                        "message": str(e),
                        "hint": "Run: uv run scripts/auth.py login",
                    }
                },
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)
        except MCPError as e:
            yaml.dump(
                {"error": {"message": f"MCP error: {e}"}},
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)
        except ConfigurationError as e:
            yaml.dump(
                {
                    "error": {
                        "message": str(e),
                        "hint": "Run: uv run scripts/auth.py login",
                    }
                },
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)
        except Exception as e:
            yaml.dump(
                {"error": {"message": str(e)}},
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)

    return wrapper


def call_mcp_with_retry(
    client, tool_name: str, params: dict, rate_limiter: Any = None, max_retries: int = 3
) -> tuple[dict | list | None, str | None]:
    """
    Call MCP tool with exponential backoff retry on failure.

    Args:
        client: MCP client instance
        tool_name: Name of the MCP tool to call
        params: Parameters to pass to the tool
        rate_limiter: Optional AdaptiveRateLimiter instance for rate state updates
        max_retries: Maximum number of retry attempts

    Returns:
        (parsed_result, error_message) - error_message is None if successful
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            result = client.call_tool(tool_name, params)
            data, err = parse_mcp_result(result)
            if err:
                raise Exception(err)
            if rate_limiter:
                rate_limiter.on_success()
            return data, None
        except Exception as e:
            last_error = e
            if rate_limiter:
                rate_limiter.on_failure()
            if attempt < max_retries - 1:
                wait_time = (rate_limiter.state.delay if rate_limiter else 1.0) * (
                    attempt + 1
                )
                print(
                    f"Request failed, retrying in {wait_time:.1f}s...", file=sys.stderr
                )
                time.sleep(wait_time)
    return None, str(last_error)
