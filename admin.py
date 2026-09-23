"""
admin.py
--------
Admin blueprint for the Cyber Security Tools Store.
Provides admin-only CRUD for Categories and Products.

All routes are protected by @admin_required.
All SQL queries are parameterized.
File uploads are validated and stored with secure filenames.
"""

import os
import uuid
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
)
from werkzeug.utils import secure_filename

from database import get_db_connection
from auth import admin_required

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# ---------------------------------------------------------------------------
# File upload helpers
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_MIMETYPES = {"image/png", "image/jpeg", "image/webp"}


def allowed_file(filename):
    """Return True only if filename has an allowed image extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_product_image(file_obj):
    """
    Validate and save an uploaded product image.
    Validates both file extension and MIME content type.
    Stores files only inside static/images/products/ using a random UUID filename.
    Guards against path traversal and malicious filenames.
    Returns the stored filename on success, or None if no file provided.
    Raises ValueError with a user-friendly message on bad input.
    """
    if not file_obj or file_obj.filename == "":
        return None

    # 1. Validate file extension
    if not allowed_file(file_obj.filename):
        raise ValueError(
            "Invalid file type. Allowed extensions: PNG, JPG, JPEG, WEBP."
        )

    # 2. Validate MIME content type
    if file_obj.mimetype and file_obj.mimetype.lower() not in ALLOWED_MIMETYPES:
        raise ValueError(
            "Invalid image content type. Allowed formats: PNG, JPG, JPEG, WEBP."
        )

    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    # Use a clean UUID to prevent filename collisions and directory traversal
    safe_name = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = os.path.abspath(os.path.join(
        current_app.root_path, "static", "images", "products"
    ))
    os.makedirs(upload_folder, exist_ok=True)

    dest_path = os.path.abspath(os.path.join(upload_folder, safe_name))
    # Directory traversal sequence defense
    if not dest_path.startswith(upload_folder):
        raise ValueError("Invalid upload destination path.")

    file_obj.save(dest_path)
    return safe_name


def delete_product_image(filename):
    """Safely remove a stored product image file if it exists."""
    if not filename:
        return
    upload_folder = os.path.abspath(os.path.join(
        current_app.root_path, "static", "images", "products"
    ))
    # secure_filename guards against any traversal attempts
    safe = secure_filename(filename)
    if not safe:
        return
    path = os.path.abspath(os.path.join(upload_folder, safe))
    if path.startswith(upload_folder) and os.path.isfile(path):
        os.remove(path)


# ===========================================================================
# CATEGORY MANAGEMENT
# ===========================================================================

@admin_bp.route("/categories")
@admin_required
def categories():
    """
    GET /admin/categories — list all categories with their product count.
    """
    conn = get_db_connection()
    cats = conn.execute("""
        SELECT c.id, c.name, c.description,
               COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
        ORDER BY c.name ASC
    """).fetchall()
    conn.close()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/add", methods=["GET", "POST"])
@admin_required
def category_add():
    """
    GET  /admin/categories/add — display add-category form.
    POST /admin/categories/add — validate and create category.
    """
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Category name is required.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Add",
                form_name=name,
                form_description=description,
            )

        if len(name) > 100:
            flash("Category name cannot exceed 100 characters.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Add",
                form_name=name,
                form_description=description,
            )

        if len(description) > 1000:
            flash("Category description cannot exceed 1000 characters.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Add",
                form_name=name,
                form_description=description,
            )

        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()

        if existing:
            conn.close()
            flash("A category with that name already exists.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Add",
                form_name=name,
                form_description=description,
            )

        conn.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (name, description or None),
        )
        conn.commit()
        conn.close()
        flash(f"Category '{name}' created successfully.", "success")
        return redirect(url_for("admin.categories"))

    return render_template(
        "admin/category_form.html",
        action="Add",
        form_name="",
        form_description="",
    )


@admin_bp.route("/categories/edit/<int:cat_id>", methods=["GET", "POST"])
@admin_required
def category_edit(cat_id):
    """
    GET  /admin/categories/edit/<id> — display edit form pre-filled.
    POST /admin/categories/edit/<id> — validate and update category.
    """
    conn = get_db_connection()
    cat = conn.execute(
        "SELECT * FROM categories WHERE id = ?", (cat_id,)
    ).fetchone()
    conn.close()

    if cat is None:
        abort(404)

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Category name is required.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Edit",
                cat=cat,
                form_name=name,
                form_description=description,
            )

        if len(name) > 100:
            flash("Category name cannot exceed 100 characters.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Edit",
                cat=cat,
                form_name=name,
                form_description=description,
            )

        if len(description) > 1000:
            flash("Category description cannot exceed 1000 characters.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Edit",
                cat=cat,
                form_name=name,
                form_description=description,
            )

        conn = get_db_connection()
        duplicate = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?) AND id != ?",
            (name, cat_id),
        ).fetchone()

        if duplicate:
            conn.close()
            flash("Another category with that name already exists.", "danger")
            return render_template(
                "admin/category_form.html",
                action="Edit",
                cat=cat,
                form_name=name,
                form_description=description,
            )

        conn.execute(
            "UPDATE categories SET name = ?, description = ? WHERE id = ?",
            (name, description or None, cat_id),
        )
        conn.commit()
        conn.close()
        flash(f"Category '{name}' updated successfully.", "success")
        return redirect(url_for("admin.categories"))

    return render_template(
        "admin/category_form.html",
        action="Edit",
        cat=cat,
        form_name=cat["name"],
        form_description=cat["description"] or "",
    )


@admin_bp.route("/categories/delete/<int:cat_id>", methods=["POST"])
@admin_required
def category_delete(cat_id):
    """
    POST /admin/categories/delete/<id> — delete a category.
    Blocked if any products still reference this category.
    """
    conn = get_db_connection()
    cat = conn.execute(
        "SELECT * FROM categories WHERE id = ?", (cat_id,)
    ).fetchone()

    if cat is None:
        conn.close()
        abort(404)

    product_count = conn.execute(
        "SELECT COUNT(*) AS c FROM products WHERE category_id = ?", (cat_id,)
    ).fetchone()["c"]

    if product_count > 0:
        conn.close()
        flash(
            f"Cannot delete '{cat['name']}': {product_count} product(s) are assigned to it. "
            "Reassign or delete those products first.",
            "danger",
        )
        return redirect(url_for("admin.categories"))

    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    flash(f"Category '{cat['name']}' deleted.", "success")
    return redirect(url_for("admin.categories"))


# ===========================================================================
# PRODUCT MANAGEMENT
# ===========================================================================

@admin_bp.route("/products")
@admin_required
def products():
    """
    GET /admin/products — list all products with category name.
    """
    conn = get_db_connection()
    prods = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.name ASC
    """).fetchall()
    conn.close()
    return render_template("admin/products.html", products=prods)


@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def product_add():
    """
    GET  /admin/products/add — display add-product form.
    POST /admin/products/add — validate, handle image upload, create product.
    """
    conn = get_db_connection()
    categories = conn.execute(
        "SELECT id, name FROM categories ORDER BY name ASC"
    ).fetchall()
    conn.close()

    if request.method == "POST":
        name          = request.form.get("name", "").strip()
        category_id   = request.form.get("category_id", "").strip()
        description   = request.form.get("description", "").strip()
        features      = request.form.get("features", "").strip()
        price_raw     = request.form.get("price", "").strip()
        license_      = request.form.get("license", "").strip()
        compatibility = request.form.get("compatibility", "").strip()
        stock_raw     = request.form.get("stock", "0").strip()

        errors = _validate_product(
            name, category_id, price_raw, stock_raw,
            description, features, license_, compatibility
        )

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "admin/product_form.html",
                action="Add",
                categories=categories,
                form=request.form,
            )

        # Handle image upload
        image_filename = None
        try:
            image_filename = save_product_image(request.files.get("image"))
        except ValueError as e:
            flash(str(e), "danger")
            return render_template(
                "admin/product_form.html",
                action="Add",
                categories=categories,
                form=request.form,
            )

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO products
                (name, category_id, description, features, price,
                 license, compatibility, image, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            int(category_id),
            description or None,
            features or None,
            float(price_raw),
            license_ or None,
            compatibility or None,
            image_filename,
            int(stock_raw),
        ))
        conn.commit()
        conn.close()
        flash(f"Product '{name}' created successfully.", "success")
        return redirect(url_for("admin.products"))

    return render_template(
        "admin/product_form.html",
        action="Add",
        categories=categories,
        form={},
        product=None,
    )


@admin_bp.route("/products/edit/<int:prod_id>", methods=["GET", "POST"])
@admin_required
def product_edit(prod_id):
    """
    GET  /admin/products/edit/<id> — display edit form pre-filled.
    POST /admin/products/edit/<id> — validate, optionally update image, save.
    """
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (prod_id,)
    ).fetchone()
    conn.close()

    if product is None:
        abort(404)

    conn = get_db_connection()
    categories = conn.execute(
        "SELECT id, name FROM categories ORDER BY name ASC"
    ).fetchall()
    conn.close()

    if request.method == "POST":
        name          = request.form.get("name", "").strip()
        category_id   = request.form.get("category_id", "").strip()
        description   = request.form.get("description", "").strip()
        features      = request.form.get("features", "").strip()
        price_raw     = request.form.get("price", "").strip()
        license_      = request.form.get("license", "").strip()
        compatibility = request.form.get("compatibility", "").strip()
        stock_raw     = request.form.get("stock", "0").strip()

        errors = _validate_product(
            name, category_id, price_raw, stock_raw,
            description, features, license_, compatibility
        )

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "admin/product_form.html",
                action="Edit",
                categories=categories,
                form=request.form,
                product=product,
            )

        # Handle optional image replacement
        new_image_filename = product["image"]  # keep existing by default
        uploaded = request.files.get("image")
        if uploaded and uploaded.filename != "":
            try:
                saved = save_product_image(uploaded)
                if saved:
                    # Remove old image file safely
                    delete_product_image(product["image"])
                    new_image_filename = saved
            except ValueError as e:
                flash(str(e), "danger")
                return render_template(
                    "admin/product_form.html",
                    action="Edit",
                    categories=categories,
                    form=request.form,
                    product=product,
                )

        conn = get_db_connection()
        conn.execute("""
            UPDATE products
            SET name=?, category_id=?, description=?, features=?,
                price=?, license=?, compatibility=?, image=?, stock=?
            WHERE id=?
        """, (
            name,
            int(category_id),
            description or None,
            features or None,
            float(price_raw),
            license_ or None,
            compatibility or None,
            new_image_filename,
            int(stock_raw),
            prod_id,
        ))
        conn.commit()
        conn.close()
        flash(f"Product '{name}' updated successfully.", "success")
        return redirect(url_for("admin.products"))

    return render_template(
        "admin/product_form.html",
        action="Edit",
        categories=categories,
        form=product,
        product=product,
    )


@admin_bp.route("/products/delete/<int:prod_id>", methods=["POST"])
@admin_required
def product_delete(prod_id):
    """
    POST /admin/products/delete/<id> — delete a product and its image file.
    """
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (prod_id,)
    ).fetchone()

    if product is None:
        conn.close()
        abort(404)

    delete_product_image(product["image"])
    conn.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    flash(f"Product '{product['name']}' deleted.", "success")
    return redirect(url_for("admin.products"))


# ---------------------------------------------------------------------------
# Internal validation helper
# ---------------------------------------------------------------------------

def _validate_product(name, category_id, price_raw, stock_raw,
                      description="", features="", license_="", compatibility=""):
    """Validate common product fields. Returns a list of error strings."""
    errors = []
    if not name:
        errors.append("Product name is required.")
    elif len(name) > 200:
        errors.append("Product name cannot exceed 200 characters.")

    if len(description) > 3000:
        errors.append("Description cannot exceed 3000 characters.")
    if len(features) > 3000:
        errors.append("Features cannot exceed 3000 characters.")
    if len(license_) > 100:
        errors.append("License field cannot exceed 100 characters.")
    if len(compatibility) > 100:
        errors.append("Compatibility field cannot exceed 100 characters.")

    if not category_id:
        errors.append("Category is required.")
    else:
        try:
            cat_id_int = int(category_id)
            if cat_id_int <= 0:
                raise ValueError
            # Verify category actually exists
            conn = get_db_connection()
            cat = conn.execute(
                "SELECT id FROM categories WHERE id = ?", (cat_id_int,)
            ).fetchone()
            conn.close()
            if cat is None:
                errors.append("Selected category does not exist.")
        except (ValueError, TypeError):
            errors.append("Invalid category selected.")

    if not price_raw:
        errors.append("Price is required.")
    else:
        try:
            price = float(price_raw)
            if price < 0:
                errors.append("Price must be zero or greater.")
            elif price > 1000000.0:
                errors.append("Price cannot exceed ₹1,000,000.00.")
        except ValueError:
            errors.append("Price must be a valid number.")

    try:
        stock = int(stock_raw)
        if stock < 0:
            errors.append("Stock must be zero or greater.")
        elif stock > 1000000:
            errors.append("Stock cannot exceed 1,000,000 units.")
    except (ValueError, TypeError):
        errors.append("Stock must be a valid whole number.")

    return errors


# ===========================================================================
# ADMIN DASHBOARD
# ===========================================================================

# Allowed order statuses — single source of truth used by all order routes
ORDER_STATUSES = ["Pending", "Confirmed", "Processing", "Completed", "Cancelled"]


@admin_bp.route("/")
@admin_required
def dashboard():
    """
    GET /admin — admin dashboard with store-wide statistics and recent orders.
    """
    conn = get_db_connection()

    # --- Statistics ---
    total_customers = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'customer'"
    ).fetchone()["c"]

    total_products = conn.execute(
        "SELECT COUNT(*) AS c FROM products"
    ).fetchone()["c"]

    total_categories = conn.execute(
        "SELECT COUNT(*) AS c FROM categories"
    ).fetchone()["c"]

    total_orders = conn.execute(
        "SELECT COUNT(*) AS c FROM orders"
    ).fetchone()["c"]

    # Revenue = sum of all order totals (all statuses except Cancelled)
    revenue_row = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS rev FROM orders WHERE status != 'Cancelled'"
    ).fetchone()
    total_revenue = revenue_row["rev"]

    # --- Recent orders (last 10) ---
    recent_orders = conn.execute("""
        SELECT o.id, o.total_amount, o.status, o.order_date,
               u.name AS customer_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.order_date DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_customers=total_customers,
        total_products=total_products,
        total_categories=total_categories,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
    )


# ===========================================================================
# ADMIN ORDER MANAGEMENT
# ===========================================================================

@admin_bp.route("/orders")
@admin_required
def orders():
    """
    GET /admin/orders — list all customer orders, newest first.
    """
    conn = get_db_connection()
    all_orders = conn.execute("""
        SELECT o.id, o.total_amount, o.status, o.order_date,
               u.name AS customer_name, u.email AS customer_email
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.order_date DESC
    """).fetchall()
    conn.close()
    return render_template(
        "admin/orders.html",
        orders=all_orders,
        statuses=ORDER_STATUSES,
    )


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    """
    GET /admin/orders/<order_id> — full detail of any order, including
    customer info, line items, quantities, purchase prices and total.
    """
    conn = get_db_connection()

    order = conn.execute("""
        SELECT o.id, o.total_amount, o.status, o.order_date,
               u.id   AS customer_id,
               u.name AS customer_name,
               u.email AS customer_email
        FROM orders o
        JOIN users u ON u.id = o.user_id
        WHERE o.id = ?
    """, (order_id,)).fetchone()

    if order is None:
        conn.close()
        abort(404)

    items = conn.execute("""
        SELECT oi.quantity, oi.price,
               p.name  AS product_name,
               p.image AS product_image,
               p.id    AS product_id,
               (oi.quantity * oi.price) AS subtotal
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    conn.close()

    return render_template(
        "admin/order_detail.html",
        order=order,
        items=items,
        statuses=ORDER_STATUSES,
    )


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_update_status(order_id):
    """
    POST /admin/orders/<order_id>/status — update an order's status.
    Only values in ORDER_STATUSES are accepted; any other value is rejected.
    """
    new_status = request.form.get("status", "").strip()

    if new_status not in ORDER_STATUSES:
        flash(
            f"Invalid status '{new_status}'. "
            f"Allowed values: {', '.join(ORDER_STATUSES)}.",
            "danger",
        )
        return redirect(url_for("admin.order_detail", order_id=order_id))

    conn = get_db_connection()
    order = conn.execute(
        "SELECT id FROM orders WHERE id = ?", (order_id,)
    ).fetchone()

    if order is None:
        conn.close()
        abort(404)

    conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id),
    )
    conn.commit()
    conn.close()

    flash(f"Order #{order_id} status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


# ===========================================================================
# ADMIN CUSTOMER MANAGEMENT
# ===========================================================================

@admin_bp.route("/customers")
@admin_required
def customers():
    """
    GET /admin/customers — list all registered customers with order counts.
    Passwords are never selected or exposed.
    """
    conn = get_db_connection()
    customer_list = conn.execute("""
        SELECT u.id, u.name, u.email, u.created_at,
               COUNT(o.id) AS order_count
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        WHERE u.role = 'customer'
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("admin/customers.html", customers=customer_list)


@admin_bp.route("/customers/<int:user_id>")
@admin_required
def customer_detail(user_id):
    """
    GET /admin/customers/<user_id> — view a specific customer's profile
    and full order history.
    Passwords are never selected or exposed.
    """
    conn = get_db_connection()

    customer = conn.execute(
        "SELECT id, name, email, created_at, role FROM users WHERE id = ? AND role = 'customer'",
        (user_id,)
    ).fetchone()

    if customer is None:
        conn.close()
        abort(404)

    orders = conn.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_id = ?
        ORDER BY order_date DESC
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
        orders=orders,
        statuses=ORDER_STATUSES,
    )
