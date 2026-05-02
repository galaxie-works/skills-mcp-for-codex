#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "httpx>=0.27",
#   "keyring>=25.0",
#   "pyyaml>=6.0",
#   "pyobjc-framework-Security>=10.0; sys_platform == 'darwin'",
#   "pyobjc-framework-LocalAuthentication>=10.0; sys_platform == 'darwin'",
# ]
# requires-python = ">=3.12"
# ///
"""
Atlassian authentication script.

Commands:
    login       - Authenticate via OAuth (pure Python, no Node.js required)
    setup-token - Setup using API token (env vars or arguments)
    status      - Check authentication status
    logout      - Clear stored tokens

Token storage:
    On macOS: Uses Touch ID / Face ID protected Keychain (biometric)
    On other systems: Uses file-based storage with fallback
"""

import argparse
import base64
import os
import sys
import time

import httpx
import keyring
import yaml

# Import OAuth client
from oauth import (
    AtlassianMCPOAuth,
    OAuthError,
    load_tokens,
    save_tokens,
    clear_tokens,
    clear_all as clear_oauth_storage,
    get_storage_type,
)

SERVICE_NAME = "atlassian-claude-skill"


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
        pass


def cmd_login(args):
    """Authenticate via OAuth (pure Python, no Node.js required)."""
    import json
    from mcp_client import AtlassianMCPClient, MCPError

    try:
        oauth = AtlassianMCPOAuth()
        tokens = oauth.login()
    except OAuthError as e:
        yaml.dump(
            {"error": str(e)},
            sys.stderr,
            default_flow_style=False,
        )
        sys.exit(1)

    # Store auth type
    set_stored_value("auth_type", "oauth")

    # Fetch accessible resources via MCP
    print("Fetching Atlassian cloud resources via MCP...")

    try:
        client = AtlassianMCPClient()
        result = client.call_tool("getAccessibleAtlassianResources")
        client.close()

        # Parse result (it's a JSON string)
        if isinstance(result, str):
            resources = json.loads(result)
        else:
            resources = result

    except MCPError as e:
        yaml.dump(
            {"error": f"Failed to fetch resources via MCP: {e}"},
            sys.stderr,
            default_flow_style=False,
        )
        sys.exit(1)

    if not resources:
        yaml.dump(
            {"error": "No accessible Atlassian sites found"},
            sys.stderr,
            default_flow_style=False,
        )
        sys.exit(1)

    # Deduplicate resources (MCP returns separate entries for Jira/Confluence scopes)
    seen = {}
    for r in resources:
        cloud_id = r["id"]
        if cloud_id not in seen:
            seen[cloud_id] = r
    resources = list(seen.values())

    # Handle site selection
    if len(resources) > 1:
        if args.site:
            selected = None
            for r in resources:
                if r["name"].lower() == args.site.lower() or r["url"] == args.site:
                    selected = r
                    break
            if selected is None:
                try:
                    idx = int(args.site) - 1
                    if 0 <= idx < len(resources):
                        selected = resources[idx]
                except ValueError:
                    pass
            if selected is None:
                yaml.dump(
                    {
                        "error": f"Site '{args.site}' not found",
                        "available_sites": [
                            {"index": i + 1, "name": r["name"], "url": r["url"]}
                            for i, r in enumerate(resources)
                        ],
                        "usage": "Use --site with site name, URL, or index number",
                    },
                    sys.stderr,
                    default_flow_style=False,
                )
                sys.exit(1)
        else:
            yaml.dump(
                {
                    "info": "Multiple Atlassian sites found, using first one",
                    "selected": {"name": resources[0]["name"], "url": resources[0]["url"]},
                    "available_sites": [
                        {"index": i + 1, "name": r["name"], "url": r["url"]}
                        for i, r in enumerate(resources)
                    ],
                    "tip": "Use --site to select a different site",
                },
                sys.stdout,
                default_flow_style=False,
            )
            selected = resources[0]
    else:
        selected = resources[0]

    set_stored_value("cloud_id", selected["id"])
    set_stored_value("site_name", selected["name"])
    set_stored_value("site_url", selected["url"])

    yaml.dump(
        {
            "status": "success",
            "storage": get_storage_type(),
            "site": {"name": selected["name"], "url": selected["url"]},
            "message": "Authentication complete! You can now use Jira and Confluence scripts.",
        },
        sys.stdout,
        default_flow_style=False,
    )


def cmd_setup_token(args):
    """Setup using API token from environment variables."""
    email = args.email or os.environ.get("ATLASSIAN_EMAIL")
    api_token = args.token or os.environ.get("ATLASSIAN_API_TOKEN")
    site_url = args.site_url or os.environ.get("ATLASSIAN_SITE_URL")

    missing = []
    if not email:
        missing.append("ATLASSIAN_EMAIL (or --email)")
    if not api_token:
        missing.append("ATLASSIAN_API_TOKEN (or --token)")
    if not site_url:
        missing.append("ATLASSIAN_SITE_URL (or --site-url)")

    if missing:
        yaml.dump(
            {
                "error": "Missing required values",
                "missing": missing,
                "usage": "Set environment variables or use command-line arguments",
                "example_env": {
                    "ATLASSIAN_EMAIL": "you@example.com",
                    "ATLASSIAN_API_TOKEN": "your-api-token",
                    "ATLASSIAN_SITE_URL": "https://yoursite.atlassian.net",
                },
            },
            sys.stderr,
            default_flow_style=False,
        )
        sys.exit(1)

    # Normalize site URL
    site_url = site_url.rstrip("/")

    # Verify credentials by fetching user info
    print("Verifying credentials...")

    auth_string = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    with httpx.Client() as client:
        response = client.get(
            f"{site_url}/rest/api/3/myself",
            headers={
                "Authorization": f"Basic {auth_string}",
                "Accept": "application/json",
            },
        )

        if response.status_code == 401:
            yaml.dump(
                {"error": "Invalid credentials. Check your email and API token."},
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)
        elif response.status_code != 200:
            yaml.dump(
                {"error": f"Failed to verify credentials: {response.text}"},
                sys.stderr,
                default_flow_style=False,
            )
            sys.exit(1)

        user_info = response.json()

    # Store credentials
    set_stored_value("auth_type", "basic")
    set_stored_value("api_email", email)
    set_stored_value("api_token", api_token)
    set_stored_value("site_url", site_url)
    set_stored_value(
        "site_name", site_url.replace("https://", "").replace(".atlassian.net", "")
    )

    yaml.dump(
        {
            "status": "success",
            "auth_type": "basic",
            "site_url": site_url,
            "user": user_info.get("displayName", email),
            "message": "API token authentication configured. You can now use Jira and Confluence scripts.",
        },
        sys.stdout,
        default_flow_style=False,
    )


def cmd_status(args):
    """Check authentication status."""
    auth_type = get_stored_value("auth_type") or "oauth"
    site_name = get_stored_value("site_name")
    site_url = get_stored_value("site_url")
    storage_type = get_storage_type()

    if auth_type == "basic":
        # Basic Auth (API token)
        api_email = get_stored_value("api_email")
        api_token = get_stored_value("api_token")

        if not api_email or not api_token:
            yaml.dump(
                {
                    "authenticated": False,
                    "storage": storage_type,
                    "message": "Not authenticated. Run 'auth.py login' or 'auth.py setup-token'",
                },
                sys.stdout,
                default_flow_style=False,
            )
            return

        yaml.dump(
            {
                "authenticated": True,
                "auth_type": "basic (API token)",
                "storage": storage_type,
                "site": {"name": site_name, "url": site_url},
                "user": api_email,
                "token_status": "valid (API tokens don't expire)",
            },
            sys.stdout,
            default_flow_style=False,
        )
    else:
        # OAuth (pure Python)
        tokens = load_tokens()

        if not tokens or "access_token" not in tokens:
            yaml.dump(
                {
                    "authenticated": False,
                    "storage": storage_type,
                    "message": "Not authenticated. Run 'auth.py login' or 'auth.py setup-token'",
                },
                sys.stdout,
                default_flow_style=False,
            )
            return

        expires_at = tokens.get("expires_at", 0)
        now = time.time()
        expires_in_seconds = int(expires_at - now)

        if expires_in_seconds <= 0:
            status = "expired (run 'auth.py login' to refresh)"
        elif expires_in_seconds < 300:
            status = "expiring_soon"
        else:
            status = "valid"

        yaml.dump(
            {
                "authenticated": True,
                "auth_type": "oauth",
                "storage": storage_type,
                "site": {"name": site_name, "url": site_url},
                "token_status": status,
                "expires_in_minutes": max(0, expires_in_seconds // 60),
            },
            sys.stdout,
            default_flow_style=False,
        )


def cmd_logout(args):
    """Clear all stored tokens and credentials."""
    keys_to_delete = [
        "access_token",
        "refresh_token",
        "expires_at",
        "cloud_id",
        "site_name",
        "site_url",
        "auth_type",
    ]

    for key in keys_to_delete:
        delete_stored_value(key)

    # Clear OAuth storage
    if args.all:
        clear_oauth_storage()
        delete_stored_value("api_email")
        delete_stored_value("api_token")
        yaml.dump(
            {"status": "success", "message": "All credentials and tokens cleared"},
            sys.stdout,
            default_flow_style=False,
        )
    else:
        clear_tokens()
        yaml.dump(
            {
                "status": "success",
                "message": "Tokens cleared. API token credentials retained.",
                "note": "Use --all to also remove API token credentials and OAuth client info",
            },
            sys.stdout,
            default_flow_style=False,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Atlassian authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # login command (OAuth - pure Python)
    login_parser = subparsers.add_parser(
        "login", help="Authenticate via OAuth (opens browser, pure Python)"
    )
    login_parser.add_argument(
        "--site", help="Select site by name, URL, or index (if multiple sites available)"
    )

    # setup-token command (API token / Basic Auth)
    token_parser = subparsers.add_parser(
        "setup-token", help="Setup using API token (reads from env vars or arguments)"
    )
    token_parser.add_argument(
        "--email", help="Atlassian account email (or set ATLASSIAN_EMAIL env var)"
    )
    token_parser.add_argument(
        "--token", help="API token (or set ATLASSIAN_API_TOKEN env var)"
    )
    token_parser.add_argument(
        "--site-url",
        help="Atlassian site URL e.g. https://yoursite.atlassian.net (or set ATLASSIAN_SITE_URL env var)",
    )

    # status command
    subparsers.add_parser("status", help="Check authentication status")

    # logout command
    logout_parser = subparsers.add_parser("logout", help="Clear stored tokens")
    logout_parser.add_argument(
        "--all", action="store_true", help="Also remove API token credentials and OAuth client info"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "login": cmd_login,
        "setup-token": cmd_setup_token,
        "status": cmd_status,
        "logout": cmd_logout,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
