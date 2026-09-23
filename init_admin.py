"""
init_admin.py
-------------
Development initialization script — creates the default admin account
if one does not already exist.

USAGE (one-time setup):
    python init_admin.py

The admin password is read from the ADMIN_PASSWORD environment variable.
If the variable is not set, a secure development default is used and printed.

This script is SAFE to run multiple times: it will NOT create duplicate
admin accounts.

NEVER commit a plain-text password to source control.
"""

import os
import sys

# Ensure the project root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cyberstore.com")
ADMIN_NAME  = os.environ.get("ADMIN_NAME", "Admin")

# Development fallback password — used ONLY when ADMIN_PASSWORD env var is absent.
# Change via environment variable before deploying.
_DEV_FALLBACK_PASSWORD = "Admin@123"


def create_admin_if_missing():
    """
    Insert the admin account into the users table if no admin exists.
    Returns True if an account was created, False if it already existed.
    """
    # Ensure tables exist
    init_db()

    conn = get_db_connection()

    # Check whether ANY admin account exists
    existing_admin = conn.execute(
        "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
    ).fetchone()

    if existing_admin:
        conn.close()
        print("[ADMIN] Admin account already exists — no changes made.")
        return False

    # Resolve admin password from environment (preferred) or dev fallback
    raw_password = os.environ.get("ADMIN_PASSWORD", "")
    if not raw_password:
        raw_password = _DEV_FALLBACK_PASSWORD
        print(
            "[ADMIN] WARNING: ADMIN_PASSWORD environment variable not set.\n"
            f"[ADMIN] Using development fallback password.\n"
            f"[ADMIN] Set the ADMIN_PASSWORD environment variable before going to production."
        )

    password_hash = generate_password_hash(raw_password)

    conn.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (ADMIN_NAME, ADMIN_EMAIL, password_hash, "admin"),
    )
    conn.commit()
    conn.close()

    print(f"[ADMIN] Admin account created: {ADMIN_EMAIL}")
    return True


if __name__ == "__main__":
    created = create_admin_if_missing()
    if created:
        print("[ADMIN] Setup complete. You can now log in at /login")
    else:
        print("[ADMIN] No changes were made.")
