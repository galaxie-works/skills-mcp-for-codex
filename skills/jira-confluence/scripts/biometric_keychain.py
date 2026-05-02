# /// script
# dependencies = [
#   "pyobjc-framework-Security>=10.0",
#   "pyobjc-framework-LocalAuthentication>=10.0",
# ]
# requires-python = ">=3.12"
# ///
"""
Biometric-protected Keychain storage using macOS Security framework.

Stores secrets in the system Keychain with Touch ID / Face ID protection.
Secrets cannot be accessed without biometric authentication or device passcode.

Falls back to regular keyring storage on non-macOS systems or when running
in environments without biometric support (SSH, CI/CD).
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING

# Check if we're on macOS and not in a headless environment
IS_MACOS = sys.platform == "darwin"
IS_HEADLESS = bool(os.environ.get("SSH_TTY") or os.environ.get("CI"))
BIOMETRIC_AVAILABLE = IS_MACOS and not IS_HEADLESS

if TYPE_CHECKING:
    pass


class BiometricKeychainError(Exception):
    """Keychain operation failed."""

    pass


class BiometricAuthCanceled(BiometricKeychainError):
    """User canceled biometric authentication."""

    pass


class BiometricNotAvailable(BiometricKeychainError):
    """Biometric authentication not available in this environment."""

    pass


def _get_pyobjc_modules():
    """
    Lazily import PyObjC modules.

    Returns tuple of (Security, Foundation) modules.
    Raises BiometricNotAvailable if imports fail.
    """
    try:
        import Security
        from Foundation import NSData

        return Security, NSData
    except ImportError as e:
        raise BiometricNotAvailable(
            f"PyObjC Security framework not available: {e}. "
            "Install with: pip install pyobjc-framework-Security"
        ) from e


class BiometricKeychain:
    """
    macOS Keychain storage with Touch ID / Face ID protection.

    Secrets stored with this class require biometric authentication
    (or device passcode as fallback) to read.

    Note: Biometric protection requires code-signed applications with proper
    entitlements. For unsigned CLI tools, falls back to regular Keychain
    storage (still encrypted, but no biometric prompt).

    Usage:
        keychain = BiometricKeychain("my-service")
        keychain.set("api_token", "secret123")
        token = keychain.get("api_token")  # Triggers Touch ID prompt if available
    """

    # Error codes from Security framework
    ERR_SEC_SUCCESS = 0
    ERR_SEC_ITEM_NOT_FOUND = -25300
    ERR_SEC_USER_CANCELED = -128
    ERR_SEC_AUTH_FAILED = -25293
    ERR_SEC_DUPLICATE_ITEM = -25299
    ERR_SEC_INTERACTION_NOT_ALLOWED = -25308
    ERR_SEC_MISSING_ENTITLEMENT = -34018

    def __init__(
        self,
        service: str,
        require_biometry: bool = False,
        auth_reason: str = "Access stored credentials",
    ):
        """
        Initialize biometric keychain.

        Args:
            service: Keychain service name (groups related secrets)
            require_biometry: If True, use kSecAccessControlBiometryAny
                              (strictly requires biometric, no passcode fallback).
                              If False (default), use kSecAccessControlUserPresence
                              (allows passcode fallback).
            auth_reason: Reason shown in Touch ID prompt
        """
        if not BIOMETRIC_AVAILABLE:
            raise BiometricNotAvailable(
                "Biometric keychain not available. "
                f"macOS={IS_MACOS}, headless={IS_HEADLESS}"
            )

        self.service = service
        self.require_biometry = require_biometry
        self.auth_reason = auth_reason
        self._security, self._nsdata = _get_pyobjc_modules()
        self._use_biometric_access_control = True  # Will be disabled if entitlements missing

    def _create_access_control(self):
        """
        Create access control object for biometric protection.

        Returns None if biometric access control is disabled (e.g., due to
        missing entitlements), which signals to use regular Keychain storage.
        """
        if not self._use_biometric_access_control:
            return None

        Security = self._security

        # Choose access control flag based on configuration
        if self.require_biometry:
            # Strictly require biometric - no passcode fallback
            flag = Security.kSecAccessControlBiometryAny
        else:
            # Allow biometric OR passcode (more user-friendly)
            flag = Security.kSecAccessControlUserPresence

        access_control, error = Security.SecAccessControlCreateWithFlags(
            None,  # Default allocator
            Security.kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            flag,
            None,  # Error output
        )

        if error or not access_control:
            # Fall back to regular Keychain if we can't create access control
            self._use_biometric_access_control = False
            return None

        return access_control

    def _to_nsdata(self, value: str) -> "NSData":
        """Convert string to NSData."""
        data = value.encode("utf-8")
        return self._nsdata.dataWithBytes_length_(data, len(data))

    def set(self, key: str, value: str) -> None:
        """
        Store a secret with biometric protection (if available).

        Falls back to regular Keychain storage if biometric protection
        is not available (e.g., missing entitlements for unsigned apps).

        Args:
            key: The key name
            value: The secret value to store
        """
        Security = self._security
        value_data = self._to_nsdata(value)

        # First delete any existing item (ignore errors)
        self._delete_raw(key)

        # Try with biometric access control first
        access_control = self._create_access_control()

        # Build query - include access control only if available
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: self.service,
            Security.kSecAttrAccount: key,
            Security.kSecValueData: value_data,
        }

        if access_control:
            query[Security.kSecAttrAccessControl] = access_control
            query[Security.kSecUseAuthenticationUI] = Security.kSecUseAuthenticationUIAllow
        else:
            # Use basic accessibility without biometric
            query[Security.kSecAttrAccessible] = Security.kSecAttrAccessibleWhenUnlockedThisDeviceOnly

        status, _ = Security.SecItemAdd(query, None)

        # Handle missing entitlement by retrying without biometric protection
        if status == self.ERR_SEC_MISSING_ENTITLEMENT and access_control:
            self._use_biometric_access_control = False
            # Retry without biometric access control
            query = {
                Security.kSecClass: Security.kSecClassGenericPassword,
                Security.kSecAttrService: self.service,
                Security.kSecAttrAccount: key,
                Security.kSecValueData: value_data,
                Security.kSecAttrAccessible: Security.kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            }
            status, _ = Security.SecItemAdd(query, None)

        if status == self.ERR_SEC_DUPLICATE_ITEM:
            # Item exists, update it
            update_query = {
                Security.kSecClass: Security.kSecClassGenericPassword,
                Security.kSecAttrService: self.service,
                Security.kSecAttrAccount: key,
            }
            update_attrs = {
                Security.kSecValueData: value_data,
            }
            if access_control and self._use_biometric_access_control:
                update_attrs[Security.kSecAttrAccessControl] = access_control
            status = Security.SecItemUpdate(update_query, update_attrs)

        if status != self.ERR_SEC_SUCCESS:
            raise BiometricKeychainError(f"Failed to store secret: OSStatus {status}")

    def get(self, key: str) -> str | None:
        """
        Retrieve a secret (triggers Touch ID prompt if biometric protection is enabled).

        Args:
            key: The key name

        Returns:
            The secret value, or None if not found

        Raises:
            BiometricAuthCanceled: User canceled authentication
            BiometricKeychainError: Other keychain errors
        """
        Security = self._security

        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: self.service,
            Security.kSecAttrAccount: key,
            Security.kSecReturnData: True,
            Security.kSecMatchLimit: Security.kSecMatchLimitOne,
        }

        # Only allow authentication UI if biometric is enabled
        if self._use_biometric_access_control:
            query[Security.kSecUseAuthenticationUI] = Security.kSecUseAuthenticationUIAllow

        status, result = Security.SecItemCopyMatching(query, None)

        if status == self.ERR_SEC_ITEM_NOT_FOUND:
            return None
        if status == self.ERR_SEC_USER_CANCELED:
            raise BiometricAuthCanceled("User canceled biometric authentication")
        if status == self.ERR_SEC_AUTH_FAILED:
            raise BiometricAuthCanceled("Biometric authentication failed")
        if status == self.ERR_SEC_INTERACTION_NOT_ALLOWED:
            raise BiometricNotAvailable(
                "User interaction not allowed (headless environment?)"
            )
        if status != self.ERR_SEC_SUCCESS:
            raise BiometricKeychainError(f"Failed to retrieve secret: OSStatus {status}")

        if result:
            return bytes(result).decode("utf-8")
        return None

    def _delete_raw(self, key: str) -> int:
        """Delete item without raising errors. Returns status code."""
        Security = self._security
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: self.service,
            Security.kSecAttrAccount: key,
        }
        return Security.SecItemDelete(query)

    def delete(self, key: str) -> None:
        """
        Delete a secret.

        Args:
            key: The key name to delete
        """
        status = self._delete_raw(key)
        if status not in (self.ERR_SEC_SUCCESS, self.ERR_SEC_ITEM_NOT_FOUND):
            raise BiometricKeychainError(f"Failed to delete secret: OSStatus {status}")

    def exists(self, key: str) -> bool:
        """
        Check if a key exists (without triggering biometric prompt).

        Args:
            key: The key name

        Returns:
            True if the key exists
        """
        Security = self._security
        query = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: self.service,
            Security.kSecAttrAccount: key,
            # Don't request data - just check existence
            Security.kSecUseAuthenticationUI: Security.kSecUseAuthenticationUIFail,
        }
        status, _ = Security.SecItemCopyMatching(query, None)
        # Will return auth failed if item exists but needs auth, or not found if missing
        return status not in (self.ERR_SEC_ITEM_NOT_FOUND,)


# --- High-level token storage API ---
# These functions provide a simple interface for oauth.py


_SERVICE_NAME = "atlassian-claude-skill"
_TOKENS_KEY = "oauth_tokens"
_CLIENT_KEY = "client_info"

# Singleton keychain instance (to preserve biometric_access_control state)
_keychain_instance: BiometricKeychain | None = None


def _get_keychain() -> BiometricKeychain:
    """Get or create the singleton keychain instance."""
    global _keychain_instance
    if _keychain_instance is None:
        _keychain_instance = BiometricKeychain(_SERVICE_NAME)
    return _keychain_instance


def is_biometric_available() -> bool:
    """Check if biometric keychain is available in this environment."""
    if not BIOMETRIC_AVAILABLE:
        return False
    try:
        _get_pyobjc_modules()
        return True
    except BiometricNotAvailable:
        return False


def is_biometric_protection_active() -> bool:
    """
    Check if biometric protection is actually active.

    Performs a probe write to detect missing entitlements.

    Returns False if:
    - Not on macOS
    - PyObjC not available
    - Running in headless mode
    - Missing entitlements (unsigned app)
    """
    if not is_biometric_available():
        return False
    try:
        keychain = _get_keychain()
        # If we haven't probed yet, do a test write to check entitlements
        if keychain._use_biometric_access_control:
            # Try to write a test value - this will trigger entitlement check
            # and set _use_biometric_access_control to False if it fails
            keychain.set("__biometric_probe__", "test")
            keychain.delete("__biometric_probe__")
        return keychain._use_biometric_access_control
    except Exception:
        return False


def save_tokens_biometric(tokens: dict) -> None:
    """
    Store OAuth tokens with biometric protection (if available).

    Args:
        tokens: Token dictionary to store
    """
    keychain = _get_keychain()
    keychain.set(_TOKENS_KEY, json.dumps(tokens))


def load_tokens_biometric() -> dict | None:
    """
    Load OAuth tokens (triggers Touch ID prompt if biometric is active).

    Returns:
        Token dictionary or None if not found

    Raises:
        BiometricAuthCanceled: User canceled authentication
    """
    keychain = _get_keychain()
    data = keychain.get(_TOKENS_KEY)
    if data:
        return json.loads(data)
    return None


def clear_tokens_biometric() -> None:
    """Remove stored OAuth tokens."""
    keychain = _get_keychain()
    keychain.delete(_TOKENS_KEY)


def save_client_info_biometric(client_info: dict) -> None:
    """
    Store OAuth client info with biometric protection (if available).

    Args:
        client_info: Client registration dictionary
    """
    keychain = _get_keychain()
    keychain.set(_CLIENT_KEY, json.dumps(client_info))


def load_client_info_biometric() -> dict | None:
    """
    Load OAuth client info (triggers Touch ID prompt if biometric is active).

    Returns:
        Client info dictionary or None if not found
    """
    keychain = _get_keychain()
    data = keychain.get(_CLIENT_KEY)
    if data:
        return json.loads(data)
    return None


def clear_all_biometric() -> None:
    """Remove all stored biometric data."""
    keychain = _get_keychain()
    keychain.delete(_TOKENS_KEY)
    keychain.delete(_CLIENT_KEY)
