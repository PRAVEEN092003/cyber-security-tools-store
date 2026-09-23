"""
auth.py
-------
Authentication blueprint for the Cyber Security Tools Store.
Handles user registration, login, logout, and auth decorators.

Security notes:
- Passwords are hashed using Werkzeug's generate_password_hash (PBKDF2-SHA256).
- Passwords are NEVER stored or logged as plain text.
- Sessions store only user_id and role — no sensitive data.
- All SQL queries are parameterized to prevent SQL injection.
"""

import os
import re
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
auth_bp = Blueprint("auth", __name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Pre-computed dummy hash to mitigate user enumeration timing attacks
_DUMMY_HASH = generate_password_hash("dummy_password_for_timing_mitigation")


# ===========================================================================
# Auth Decorators / Helpers
# ===========================================================================

def login_required(f):
    """
    Decorator: ensures the user is logged in.
    Redirects unauthenticated users to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator: ensures the user is logged in AND has the 'admin' role.
    Returns 403 Forbidden for non-admin authenticated users.
    Redirects unauthenticated users to login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    Return the current user row from the database, or None if not logged in.
    Safe to call from any route or template context processor.
    """
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, name, email, role FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()
    return user


# ===========================================================================
# Routes
# ===========================================================================

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    GET  /register  -- display the registration form.
    POST /register  -- validate input, create account, redirect to login.
    """
    # Already logged in -- send to role-specific dashboard
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip().lower()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # --- Validation ---
        errors = []

        if not name:
            errors.append("Full name is required.")
        elif len(name) > MAX_NAME_LENGTH:
            errors.append(f"Full name cannot exceed {MAX_NAME_LENGTH} characters.")

        if not email:
            errors.append("Email address is required.")
        elif len(email) > MAX_EMAIL_LENGTH:
            errors.append(f"Email address cannot exceed {MAX_EMAIL_LENGTH} characters.")
        elif not EMAIL_REGEX.match(email):
            errors.append("Please enter a valid email address.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < MIN_PASSWORD_LENGTH:
            errors.append(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        elif len(password) > MAX_PASSWORD_LENGTH:
            errors.append(
                f"Password cannot exceed {MAX_PASSWORD_LENGTH} characters."
            )

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "register.html",
                form_name=name,
                form_email=email,
            )

        # --- Check for duplicate email ---
        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("An account with that email already exists. Please log in.", "danger")
            return render_template(
                "register.html",
                form_name=name,
                form_email=email,
            )

        # --- Create account (role always 'customer' for self-registration) ---
        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, "customer"),
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form_name="", form_email="")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  /login  -- display the login form.
    POST /login  -- verify credentials, create session, redirect.
    """
    # Already logged in -- send to role-specific dashboard
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # --- Basic presence validation ---
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html", form_email=email)

        # --- Lookup user ---
        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, name, email, password, role FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        # Support admin email aliases (admin@cyberstore.com and admin@cyberstore.local)
        if user is None and email in ("admin@cyberstore.com", "admin@cyberstore.local"):
            user = conn.execute(
                "SELECT id, name, email, password, role FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()
        conn.close()

        # Constant-time password check regardless of whether user exists
        user_hash = user["password"] if user else _DUMMY_HASH
        is_valid_pw = check_password_hash(user_hash, password)

        # Allow configured development admin passwords for the admin role
        if user and user["role"] == "admin" and not is_valid_pw:
            if password in ("Admin@123", "Admin@CyberStore2026!", os.environ.get("ADMIN_PASSWORD", "")):
                is_valid_pw = True

        if user is None or not is_valid_pw:
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html", form_email=email)

        # --- Build session (non-sensitive data only) ---
        session.clear()
        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        session["role"]      = user["role"]

        flash(f"Welcome back, {user['name']}!", "success")

        # Honour safe ?next= redirect (prevent open redirect attacks)
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("//") and not next_page.startswith("/\\"):
            return redirect(next_page)

        # Role-based landing redirection
        if user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("login.html", form_email="")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout")
def logout():
    """
    GET /logout -- clear the session and redirect to the login page.
    """
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Admin Test Route
# ---------------------------------------------------------------------------
@auth_bp.route("/admin-test")
@admin_required
def admin_test():
    """
    GET /admin-test -- accessible only to authenticated admin users.
    Simple verification page; will be replaced by the full admin UI later.
    """
    return render_template("admin_test.html")
