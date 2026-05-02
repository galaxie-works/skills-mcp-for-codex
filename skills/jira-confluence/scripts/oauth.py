#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "httpx>=0.27",
#   "pyyaml>=6.0",
#   "pyobjc-framework-Security>=10.0; sys_platform == 'darwin'",
#   "pyobjc-framework-LocalAuthentication>=10.0; sys_platform == 'darwin'",
# ]
# requires-python = ">=3.12"
# ///
"""
OAuth 2.0 client for Atlassian MCP server.

Implements:
- OAuth 2.0 Authorization Code flow with PKCE (RFC7636)
- Dynamic Client Registration (RFC7591)
- Token refresh
- Biometric-protected token storage (macOS Touch ID / Face ID)

No Node.js or mcp-remote dependency required.
"""

import base64
import hashlib
import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import yaml

# Atlassian MCP OAuth endpoints (from discovery)
OAUTH_METADATA_URL = "https://mcp.atlassian.com/.well-known/oauth-authorization-server"
AUTHORIZATION_ENDPOINT = "https://mcp.atlassian.com/v1/authorize"
TOKEN_ENDPOINT = "https://cf.mcp.atlassian.com/v1/token"
REGISTRATION_ENDPOINT = "https://cf.mcp.atlassian.com/v1/register"

# Local storage
CONFIG_DIR = os.path.expanduser("~/.atlassian-mcp")
CLIENT_INFO_FILE = os.path.join(CONFIG_DIR, "client_info.json")
TOKENS_FILE = os.path.join(CONFIG_DIR, "tokens.json")

# Default callback port
DEFAULT_CALLBACK_PORT = 9876

# OAuth scopes for Jira and Confluence access
DEFAULT_SCOPES = [
    "read:jira-work",
    "read:jira-user",
    "read:confluence-content.all",
    "read:confluence-space.summary",
    "read:confluence-user",
    "write:jira-work",  # Create/edit issues, post comments, transitions
    "offline_access",  # Needed for refresh tokens
]


class OAuthError(Exception):
    """OAuth error."""
    pass


class AuthenticationError(OAuthError):
    """Authentication failed."""
    pass


# --- PKCE Implementation ---


def generate_pkce() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate 32 random bytes for code_verifier
    # Use URL-safe base64 encoding without padding
    random_bytes = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(random_bytes).rstrip(b"=").decode("ascii")

    # Create code_challenge = base64url(SHA256(code_verifier))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


# --- OAuth Callback Server ---


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback."""

    # Class variables to store callback data
    auth_code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None

    def do_GET(self):
        """Handle OAuth callback GET request."""
        parsed = urlparse(self.path)

        if parsed.path not in ("/callback", "/oauth/callback"):
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)

        if "error" in params:
            OAuthCallbackHandler.error = params.get("error", ["Unknown error"])[0]
            OAuthCallbackHandler.error_description = params.get(
                "error_description", [""]
            )[0]
            self._send_html_response(
                "<h1>Authentication Failed</h1>"
                f"<p>Error: {OAuthCallbackHandler.error}</p>"
                f"<p>{OAuthCallbackHandler.error_description}</p>"
                "<p>You can close this window.</p>"
            )
            return

        OAuthCallbackHandler.auth_code = params.get("code", [None])[0]
        OAuthCallbackHandler.state = params.get("state", [None])[0]

        self._send_html_response(
            "<h1>Authentication Successful!</h1>"
            "<p>You can close this window and return to the terminal.</p>"
        )

    def _send_html_response(self, body: str):
        """Send HTML response."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = f"<html><body>{body}</body></html>"
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def wait_for_callback(port: int, timeout: int = 120) -> tuple[str, str]:
    """
    Start local server and wait for OAuth callback.

    Args:
        port: Port to listen on
        timeout: Timeout in seconds

    Returns:
        Tuple of (auth_code, state)

    Raises:
        OAuthError: On error or timeout
    """
    # Reset handler state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.state = None
    OAuthCallbackHandler.error = None
    OAuthCallbackHandler.error_description = None

    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.timeout = timeout

    print(f"Waiting for OAuth callback on http://localhost:{port}/callback ...")

    # Wait for callback
    start_time = time.time()
    while (
        OAuthCallbackHandler.auth_code is None and OAuthCallbackHandler.error is None
    ):
        if time.time() - start_time > timeout:
            server.server_close()
            raise OAuthError("OAuth callback timeout")
        server.handle_request()

    server.server_close()

    if OAuthCallbackHandler.error:
        raise OAuthError(
            f"OAuth error: {OAuthCallbackHandler.error} - "
            f"{OAuthCallbackHandler.error_description}"
        )

    if not OAuthCallbackHandler.auth_code:
        raise OAuthError("No authorization code received")

    return OAuthCallbackHandler.auth_code, OAuthCallbackHandler.state or ""


# --- Storage Functions ---
# Supports biometric-protected storage on macOS with fallback to file-based storage


def _use_biometric_storage() -> bool:
    """Check if biometric storage should be used."""
    try:
        from biometric_keychain import is_biometric_available
        return is_biometric_available()
    except ImportError:
        return False


def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_client_info() -> dict | None:
    """
    Load client info.

    Tries biometric keychain first (macOS), falls back to file storage.
    """
    # Try biometric storage first
    if _use_biometric_storage():
        try:
            from biometric_keychain import load_client_info_biometric, BiometricAuthCanceled
            result = load_client_info_biometric()
            if result:
                return result
            # If not in biometric storage, check file (migration case)
        except BiometricAuthCanceled:
            print("Biometric authentication canceled.")
            return None
        except Exception:
            pass  # Fall through to file storage

    # File-based fallback
    if not os.path.exists(CLIENT_INFO_FILE):
        return None
    try:
        with open(CLIENT_INFO_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_client_info(client_info: dict):
    """
    Save client info.

    Uses biometric keychain on macOS, falls back to file storage.
    """
    # Try biometric storage first
    if _use_biometric_storage():
        try:
            from biometric_keychain import save_client_info_biometric
            save_client_info_biometric(client_info)
            # Also remove old file if it exists (migration)
            if os.path.exists(CLIENT_INFO_FILE):
                os.remove(CLIENT_INFO_FILE)
            return
        except Exception as e:
            print(f"Biometric storage failed, using file: {e}")

    # File-based fallback
    ensure_config_dir()
    with open(CLIENT_INFO_FILE, "w") as f:
        json.dump(client_info, f, indent=2)


def load_tokens() -> dict | None:
    """
    Load OAuth tokens.

    Tries biometric keychain first (macOS with Touch ID protection),
    falls back to file storage for other environments.
    """
    # Try biometric storage first
    if _use_biometric_storage():
        try:
            from biometric_keychain import load_tokens_biometric, BiometricAuthCanceled
            result = load_tokens_biometric()
            if result:
                return result
            # If not in biometric storage, check file (migration case)
        except BiometricAuthCanceled:
            print("Biometric authentication canceled.")
            return None
        except Exception:
            pass  # Fall through to file storage

    # File-based fallback
    if not os.path.exists(TOKENS_FILE):
        return None
    try:
        with open(TOKENS_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_tokens(tokens: dict):
    """
    Save OAuth tokens.

    Uses biometric keychain on macOS (Touch ID protected),
    falls back to file storage for other environments.
    """
    # Add expires_at if not present
    if "expires_at" not in tokens and "expires_in" in tokens:
        tokens["expires_at"] = time.time() + tokens["expires_in"]

    # Try biometric storage first
    if _use_biometric_storage():
        try:
            from biometric_keychain import save_tokens_biometric
            save_tokens_biometric(tokens)
            # Also remove old file if it exists (migration)
            if os.path.exists(TOKENS_FILE):
                os.remove(TOKENS_FILE)
            return
        except Exception as e:
            print(f"Biometric storage failed, using file: {e}")

    # File-based fallback
    ensure_config_dir()
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def clear_tokens():
    """Clear stored tokens from both biometric and file storage."""
    # Clear biometric storage
    if _use_biometric_storage():
        try:
            from biometric_keychain import clear_tokens_biometric
            clear_tokens_biometric()
        except Exception:
            pass

    # Clear file storage
    if os.path.exists(TOKENS_FILE):
        os.remove(TOKENS_FILE)


def clear_all():
    """Clear all stored data from both biometric and file storage."""
    # Clear biometric storage
    if _use_biometric_storage():
        try:
            from biometric_keychain import clear_all_biometric
            clear_all_biometric()
        except Exception:
            pass

    # Clear file storage
    for f in [CLIENT_INFO_FILE, TOKENS_FILE]:
        if os.path.exists(f):
            os.remove(f)


def get_storage_type() -> str:
    """Return the current storage type being used."""
    if _use_biometric_storage():
        try:
            from biometric_keychain import is_biometric_protection_active
            if is_biometric_protection_active():
                return "keychain (Touch ID / Face ID protected)"
            return "keychain (macOS Keychain)"
        except Exception:
            return "keychain (macOS Keychain)"
    return "file"


# --- OAuth Client ---


class AtlassianMCPOAuth:
    """OAuth 2.0 client for Atlassian MCP server."""

    def __init__(self, callback_port: int = DEFAULT_CALLBACK_PORT):
        self.callback_port = callback_port
        self.redirect_uri = f"http://localhost:{callback_port}/callback"

    def register_client(self) -> dict:
        """
        Register a new OAuth client via Dynamic Client Registration (RFC7591).

        Returns:
            Client info dict with client_id
        """
        print("Registering OAuth client with Atlassian MCP...")

        client_metadata = {
            "redirect_uris": [self.redirect_uri],
            "token_endpoint_auth_method": "none",  # Public client
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "Atlassian MCP Python Client",
            "client_uri": "https://github.com/anthropics/claude-code",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                REGISTRATION_ENDPOINT,
                json=client_metadata,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code not in (200, 201):
                raise OAuthError(
                    f"Client registration failed: {response.status_code} - {response.text}"
                )

            client_info = response.json()

        print(f"Client registered: {client_info.get('client_id')}")
        return client_info

    def get_authorization_url(
        self, client_id: str, code_challenge: str, state: str, scopes: list[str] | None = None
    ) -> str:
        """Build authorization URL for browser."""
        params = {
            "client_id": client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
        if scopes:
            params["scope"] = " ".join(scopes)
        return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    def exchange_code(
        self, code: str, code_verifier: str, client_id: str
    ) -> dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier
            client_id: OAuth client ID

        Returns:
            Token dict with access_token, refresh_token, etc.
        """
        print("Exchanging authorization code for tokens...")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise OAuthError(
                    f"Token exchange failed: {response.status_code} - {response.text}"
                )

            tokens = response.json()

        return tokens

    def refresh_tokens(self, refresh_token: str, client_id: str) -> dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token
            client_id: OAuth client ID

        Returns:
            New token dict
        """
        print("Refreshing access token...")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise OAuthError(
                    f"Token refresh failed: {response.status_code} - {response.text}"
                )

            tokens = response.json()

        return tokens

    def login(self, scopes: list[str] | None = None) -> dict:
        """
        Perform full OAuth login flow.

        Args:
            scopes: OAuth scopes to request. Defaults to DEFAULT_SCOPES.

        Returns:
            Token dict
        """
        if scopes is None:
            scopes = DEFAULT_SCOPES

        # 1. Load or register client
        client_info = load_client_info()
        if not client_info:
            client_info = self.register_client()
            save_client_info(client_info)

        client_id = client_info["client_id"]

        # 2. Generate PKCE
        code_verifier, code_challenge = generate_pkce()

        # 3. Generate state
        state = secrets.token_urlsafe(32)

        # 4. Build authorization URL
        auth_url = self.get_authorization_url(client_id, code_challenge, state, scopes)

        # 5. Open browser
        print("\nOpening browser for Atlassian login...")
        print(f"If browser doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        # 6. Wait for callback
        auth_code, received_state = wait_for_callback(self.callback_port)

        # 7. Verify state
        if received_state != state:
            raise OAuthError("State mismatch - possible CSRF attack")

        # 8. Exchange code for tokens
        tokens = self.exchange_code(auth_code, code_verifier, client_id)

        # 9. Save tokens
        save_tokens(tokens)

        print("\nAuthentication successful!")
        return tokens


def get_valid_token() -> str:
    """
    Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token

    Raises:
        AuthenticationError: If no valid token available
    """
    tokens = load_tokens()
    if not tokens:
        raise AuthenticationError(
            "Not authenticated. Run 'auth.py login' first."
        )

    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)

    # Check if token is expired or expiring within 5 minutes
    if time.time() > expires_at - 300:
        # Try to refresh
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise AuthenticationError(
                "Token expired and no refresh token. Run 'auth.py login'."
            )

        client_info = load_client_info()
        if not client_info:
            raise AuthenticationError(
                "No client info. Run 'auth.py login'."
            )

        oauth = AtlassianMCPOAuth()
        try:
            new_tokens = oauth.refresh_tokens(refresh_token, client_info["client_id"])
            save_tokens(new_tokens)
            access_token = new_tokens["access_token"]
        except OAuthError as e:
            raise AuthenticationError(
                f"Token refresh failed: {e}. Run 'auth.py login'."
            )

    return access_token


# --- CLI Commands ---


def cmd_login(args):
    """Login via OAuth."""
    try:
        oauth = AtlassianMCPOAuth()
        tokens = oauth.login()
        yaml.dump(
            {
                "status": "success",
                "message": "Authentication complete!",
                "expires_in_minutes": tokens.get("expires_in", 0) // 60,
            },
            sys.stdout,
            default_flow_style=False,
        )
    except OAuthError as e:
        yaml.dump({"error": str(e)}, sys.stderr, default_flow_style=False)
        sys.exit(1)


def cmd_status(args):
    """Check authentication status."""
    storage_type = get_storage_type()
    tokens = load_tokens()
    client_info = load_client_info()

    if not tokens:
        yaml.dump(
            {
                "authenticated": False,
                "storage": storage_type,
                "message": "Not authenticated. Run 'oauth.py login'.",
            },
            sys.stdout,
            default_flow_style=False,
        )
        return

    expires_at = tokens.get("expires_at", 0)
    now = time.time()
    expires_in_seconds = int(expires_at - now)

    if expires_in_seconds <= 0:
        status = "expired"
    elif expires_in_seconds < 300:
        status = "expiring_soon"
    else:
        status = "valid"

    yaml.dump(
        {
            "authenticated": True,
            "storage": storage_type,
            "client_id": client_info.get("client_id") if client_info else None,
            "token_status": status,
            "expires_in_minutes": max(0, expires_in_seconds // 60),
        },
        sys.stdout,
        default_flow_style=False,
    )


def cmd_refresh(args):
    """Refresh access token."""
    try:
        token = get_valid_token()
        yaml.dump(
            {
                "status": "success",
                "message": "Token refreshed (or still valid).",
            },
            sys.stdout,
            default_flow_style=False,
        )
    except AuthenticationError as e:
        yaml.dump({"error": str(e)}, sys.stderr, default_flow_style=False)
        sys.exit(1)


def cmd_logout(args):
    """Clear stored tokens."""
    if args.all:
        clear_all()
        yaml.dump(
            {"status": "success", "message": "All credentials cleared."},
            sys.stdout,
            default_flow_style=False,
        )
    else:
        clear_tokens()
        yaml.dump(
            {"status": "success", "message": "Tokens cleared. Client info retained."},
            sys.stdout,
            default_flow_style=False,
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Atlassian MCP OAuth client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # login
    subparsers.add_parser("login", help="Login via OAuth (opens browser)")

    # status
    subparsers.add_parser("status", help="Check authentication status")

    # refresh
    subparsers.add_parser("refresh", help="Refresh access token")

    # logout
    logout_parser = subparsers.add_parser("logout", help="Clear stored tokens")
    logout_parser.add_argument(
        "--all", action="store_true", help="Also remove client registration"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "login": cmd_login,
        "status": cmd_status,
        "refresh": cmd_refresh,
        "logout": cmd_logout,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
