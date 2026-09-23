"""
app.py
------
Main Flask application entry point for the Cyber Security Tools Store.
Initializes the database on startup, registers all blueprints, and seeds
the admin account (if one does not already exist).
Configured with security hardening: session security, CSRF protection,
security headers, and clean error handling.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment configuration from .env if present
load_dotenv()

from flask import Flask, render_template, request, session, redirect, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from database import init_db, get_db_connection
from auth import auth_bp, get_current_user, login_required
from admin import admin_bp
from products import store_bp
from cart import cart_bp

# ---------------------------------------------------------------------------
# Application Factory & Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Strong SECRET_KEY loaded from environment
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'cyber-store-dev-fallback-key-should-be-in-env-file'
)

# Session Security Configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Secure cookie flag can be toggled via environment in production HTTPS
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1')

# Max upload size: 8 MB
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize CSRF Protection globally
csrf = CSRFProtect(app)

# ---------------------------------------------------------------------------
# Register Blueprints
# ---------------------------------------------------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(store_bp)
app.register_blueprint(cart_bp)

# ---------------------------------------------------------------------------
# Context Processor — injects `current_user` into every template
# ---------------------------------------------------------------------------
@app.context_processor
def inject_current_user():
    """Make the current logged-in user available as `current_user` in templates."""
    return {"current_user": get_current_user()}

# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    """Add standard HTTP security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors safely."""
    return render_template("400.html"), 400

@app.errorhandler(400)
def bad_request(e):
    """Custom 400 Bad Request page."""
    return render_template("400.html"), 400

@app.errorhandler(403)
def forbidden(e):
    """Custom 403 Forbidden page."""
    return render_template("403.html"), 403

@app.errorhandler(404)
def not_found(e):
    """Custom 404 Not Found page."""
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Custom 500 Internal Server Error page without leaking stack traces."""
    app.logger.error("Internal Server Error: %s", e)
    return render_template("500.html"), 500

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """
    Public Home page — renders the simple, clean landing page for guests.
    If already authenticated, redirects directly to role-specific dashboard.
    """
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    # Fetch a small selection of security tools for the public showcase
    conn = get_db_connection()
    featured_products = conn.execute("""
        SELECT p.id, p.name, p.description, p.price, p.image, p.stock,
               c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.id ASC
        LIMIT 6
    """).fetchall()
    categories = conn.execute("SELECT id, name, description FROM categories ORDER BY name ASC LIMIT 4").fetchall()
    conn.close()

    return render_template(
        'index.html',
        featured_products=featured_products,
        categories=categories
    )


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Customer Home / Dashboard — dedicated landing page for authenticated customers.
    """
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    user_id = session["user_id"]
    conn = get_db_connection()

    # Query recent orders for this customer (up to 5)
    recent_orders = conn.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_id = ?
        ORDER BY order_date DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    total_orders_count = conn.execute(
        "SELECT COUNT(*) AS c FROM orders WHERE user_id = ?",
        (user_id,)
    ).fetchone()["c"]

    conn.close()

    return render_template(
        'customer_dashboard.html',
        recent_orders=recent_orders,
        total_orders_count=total_orders_count
    )

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Initialize the database (creates tables if they don't exist)
    init_db()

    # Seed the admin account if no admin exists yet
    from init_admin import create_admin_if_missing
    create_admin_if_missing()

    # Run server with debug controlled via environment variable
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode)
