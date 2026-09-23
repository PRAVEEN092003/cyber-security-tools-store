"""
products.py
-----------
Customer-facing product browsing blueprint for the Cyber Security Tools Store.
All routes are publicly accessible (no login required).
Provides product listing with search/filter and individual product detail.
"""

from flask import Blueprint, render_template, request, abort
from database import get_db_connection

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
store_bp = Blueprint("store", __name__)


@store_bp.route("/products")
def product_list():
    """
    GET /products — browse all products with optional search and filter.

    Query parameters:
        q          (str)  — search term matched against product name
        category   (int)  — filter by category ID
        min_price  (float) — minimum price filter
        max_price  (float) — maximum price filter
    """
    search      = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()
    min_price   = request.args.get("min_price", "").strip()
    max_price   = request.args.get("max_price", "").strip()

    # Build query dynamically with parameterized placeholders
    query  = """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE 1=1
    """
    params = []

    if search:
        query  += " AND p.name LIKE ?"
        params.append(f"%{search}%")

    if category_id:
        try:
            cid = int(category_id)
            query  += " AND p.category_id = ?"
            params.append(cid)
        except ValueError:
            pass  # ignore invalid category param

    if min_price:
        try:
            query  += " AND p.price >= ?"
            params.append(float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            query  += " AND p.price <= ?"
            params.append(float(max_price))
        except ValueError:
            pass

    query += " ORDER BY p.name ASC"

    conn = get_db_connection()
    products   = conn.execute(query, params).fetchall()
    categories = conn.execute(
        "SELECT id, name FROM categories ORDER BY name ASC"
    ).fetchall()
    conn.close()

    return render_template(
        "store/product_list.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
        min_price=min_price,
        max_price=max_price,
    )


@store_bp.route("/product/<int:prod_id>")
def product_detail(prod_id):
    """
    GET /product/<id> — detailed view of a single product.
    Returns 404 if the product does not exist.
    """
    conn = get_db_connection()
    product = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.id = ?
    """, (prod_id,)).fetchone()
    conn.close()

    if product is None:
        abort(404)

    return render_template("store/product_detail.html", product=product)
