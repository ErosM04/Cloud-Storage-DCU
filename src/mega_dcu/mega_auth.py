"""
MEGA Cloud Storage Authentication & Session Caching.

Handles terminal login, session persistence in .mega_session.json,
and intercepts rate-limiting/Proof-of-Work API challenges with actionable diagnostics.
"""

import getpass
import json
import os
import sys
import time
import requests
import asyncio
import types

# Compatibility shim for Python 3.11+ with tenacity < 6.0 (required by mega.py)
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = types.coroutine

from mega import Mega
from mega.errors import RequestError

SESSION_FILE = ".mega_session.json"


def _robust_api_request(self, data):
    """
    Enhanced _api_request for mega.py that checks HTTP status codes and headers
    before attempting json.loads(), preventing cryptic JSONDecodeError crashes.
    """
    params = {'id': self.sequence_num}
    self.sequence_num += 1

    if self.sid:
        params.update({'sid': self.sid})

    if not isinstance(data, list):
        data = [data]

    url = f'{self.schema}://g.api.{self.domain}/cs'
    response = requests.post(
        url,
        params=params,
        data=json.dumps(data),
        timeout=self.timeout,
    )

    # Check for anti-bot / proof-of-work challenges or rate limits
    if response.status_code == 402 or 'X-Hashcash' in response.headers:
        raise PermissionError(
            "MEGA anti-bot rate-limit triggered (HTTP 402 / X-Hashcash Proof-of-Work challenge).\n"
            "   MEGA has temporarily restricted automated logins from your IP address due to multiple rapid login attempts.\n"
            "   To resolve this:\n"
            "     1. Wait 15–30 minutes for the cooldown to reset, OR\n"
            "     2. Disconnect/reconnect your network or switch to a different network/IP (e.g. mobile hotspot)."
        )

    if response.status_code == 429:
        raise PermissionError(
            "MEGA API rate limit reached (HTTP 429: Too Many Requests).\n"
            "   Please wait a few minutes before trying again."
        )

    if not response.text or not response.text.strip():
        raise ConnectionError(
            f"MEGA API returned an empty response body (HTTP {response.status_code})."
        )

    try:
        json_resp = json.loads(response.text)
    except json.JSONDecodeError:
        raise ConnectionError(
            f"Failed to parse MEGA response as JSON (HTTP {response.status_code}): {response.text[:200]}"
        )

    try:
        if isinstance(json_resp, list):
            int_resp = json_resp[0] if isinstance(json_resp[0], int) else None
        elif isinstance(json_resp, int):
            int_resp = json_resp
    except IndexError:
        int_resp = None

    if int_resp is not None:
        if int_resp == 0:
            return int_resp
        if int_resp == -3:
            raise RuntimeError('Request failed, retrying')
        raise RequestError(int_resp)

    return json_resp[0]


# Apply robust API request handler to Mega
Mega._api_request = _robust_api_request


def load_cached_session(requested_email=None):
    """Attempts to restore an active MEGA session from .mega_session.json."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cached_email = data.get('email', '')
        if requested_email and cached_email and requested_email.strip().lower() != cached_email.strip().lower():
            return None

        mega = Mega()
        mega.sid = data['sid']
        mega.master_key = tuple(data['master_key'])
        if data.get('root_id'):
            mega.root_id = data['root_id']
        if data.get('trashbin_id'):
            mega._trash_folder_node_id = data['trashbin_id']
            mega.trashbin_id = data['trashbin_id']

        # Validate session with a lightweight check
        user_info = mega.get_user()
        if isinstance(user_info, dict) and 'email' in user_info:
            return mega, data.get('email', '')
    except Exception:
        # Invalid or expired session - clear cache
        try:
            os.remove(SESSION_FILE)
        except OSError:
            pass
    return None


def save_cached_session(mega_instance, email):
    """Caches active MEGA session credentials to avoid repeated login handshakes."""
    try:
        root_id = getattr(mega_instance, 'root_id', None)
        trash_id = getattr(mega_instance, '_trash_folder_node_id', None)
        session_data = {
            'email': email,
            'sid': str(mega_instance.sid),
            'master_key': list(mega_instance.master_key),
            'root_id': str(root_id) if isinstance(root_id, str) else None,
            'trashbin_id': str(trash_id) if isinstance(trash_id, str) else None,
            'saved_at': time.time()
        }
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Warning: Could not cache MEGA session: {e}")


def authenticate_mega():
    """
    Authenticates to MEGA.
    First checks for an active cached session in .mega_session.json.
    If none exists or expired, prompts for credentials (or reads MEGA_EMAIL / MEGA_PASSWORD).
    """
    print("\n🔐 --- MEGA Authentication ---")

    # Check for existing cached session first
    env_email = os.environ.get("MEGA_EMAIL")
    cached = load_cached_session(requested_email=env_email)
    if cached is not None:
        mega_client, session_email = cached
        display_account = session_email or "active session"
        print(f"🔄 Reusing active MEGA session for: {display_account}")
        print("👤 MEGA Login restored successfully!\n")
        return mega_client

    # Allow reading from environment variables if set
    email = env_email
    password = os.environ.get("MEGA_PASSWORD")

    if not email:
        email = input("Enter MEGA email: ").strip()
    else:
        print(f"Using MEGA email from environment variable: {email}")

    if not password:
        password = getpass.getpass("Enter MEGA password: ").strip()
    else:
        print("Using MEGA password from environment variable.")

    if not email or not password:
        print("❌ Error: MEGA email and password cannot be empty.")
        sys.exit(1)

    print("\n⏳ Logging in to MEGA...")
    mega = Mega()
    try:
        m = mega.login(email, password)
        print("👤 MEGA Login performed successfully!\n")
        # Cache session for subsequent runs
        save_cached_session(m, email)
        return m
    except Exception as e:
        print(f"\n❌ Failed to login to MEGA: {e}")
        if not isinstance(e, PermissionError):
            print("Please check your email and password and try again.")
        sys.exit(1)
