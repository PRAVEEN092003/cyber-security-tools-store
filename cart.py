"""
cart.py
-------
Shopping cart, checkout, order placement and order history blueprint
for the Cyber Security Tools Store.

Cart storage:
    Session-based.  The cart is stored in Flask's signed cookie session
    as a dict:  session['cart'] = { '<product_id>': <quantity>, ... }
    Prices are NEVER stored in the session — they are always fetched from
    the database at display / checkout time.

Order creation:
    A SQLite transaction guarantees that stock reductions, the orders row,
    and all order_items rows are written atomically.  If anything fails,
    the whole transaction is rolled back.

Security notes:
    - All prices and stock levels come from the database, never from the client.
    - Customers can only view their own orders (user_id enforced in every query).
    - All SQL queries are parameterized.
    - @login_required guards every route.
"""

import sqlite3
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
from database import get_db_connection, DATABASE_PATH
from auth import login_required

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------
cart_bp = Blueprint("cart", __name__)

# ---------------------------------------------------------------------------
# Cart session helpers
# ---------------------------------------------------------------------------

def _get_cart():
    """Return the cart dict from the session, creating it if absent."""
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def _save_cart(cart):
    """Persist the cart dict back into the session and mark it modified."""
    session["cart"] = cart
    session.modified = True


def _cart_item_count():
    """Return total number of individual items in the cart (sum of quantities)."""
    return sum(_get_cart().values())


def _build_cart_details():
    """
    Enrich the session cart with live product data from the database.

    Returns a tuple (items, total) where:
        items  — list of dicts with keys:
                    product_id, name, price, image, stock,
                    quantity, subtotal, stock_ok
        total  — float, sum of all subtotals
    Entries for products that no longer exist in the DB are silently dropped.
    """
    cart = _get_cart()
    if not cart:
        return [], 0.0

    # Fetch all referenced products in one query
    product_ids = list(cart.keys())          # strings from session
    placeholders = ",".join("?" * len(product_ids))
    conn = get_db_connection()
    rows = conn.execute(
        f"SELECT id, name, price, image, stock FROM products WHERE id IN ({placeholders})",
        [int(pid) for pid in product_ids],
    ).fetchall()
    conn.close()

    db_products = {str(row["id"]): row for row in rows}

    items = []
    total = 0.0
    for pid_str, qty in list(cart.items()):
        if pid_str not in db_products:
            continue                         # product deleted since cart was built
        prod = db_products[pid_str]
        subtotal = prod["price"] * qty
        total += subtotal
        items.append({
            "product_id": int(pid_str),
            "name":       prod["name"],
            "price":      prod["price"],
            "image":      prod["image"],
            "stock":      prod["stock"],
            "quantity":   qty,
            "subtotal":   subtotal,
            "stock_ok":   qty <= prod["stock"],
        })

    return items, round(total, 2)


# ===========================================================================
# CART ROUTES
# ===========================================================================

@cart_bp.route("/cart")
@login_required
def cart_view():
    """
    GET /cart — display the shopping cart.
    """
    items, total = _build_cart_details()
    return render_template("cart/cart.html", items=items, total=total)


@cart_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    """
    POST /cart/add/<product_id> — add a product to the cart.

    If the product is already in the cart, increment quantity.
    Quantity defaults to 1; can be overridden by a form field 'quantity'.
    Blocks adding out-of-stock products.
    """
    # Validate and parse requested quantity
    try:
        qty = int(request.form.get("quantity", 1))
        if qty < 1:
            qty = 1
        elif qty > 1000:
            qty = 1000
    except (ValueError, TypeError):
        qty = 1

    # Fetch product from DB — never trust client-supplied data
    conn = get_db_connection()
    product = conn.execute(
        "SELECT id, name, price, stock FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()
    conn.close()

    if product is None:
        flash("Product not found.", "danger")
        return redirect(url_for("store.product_list"))

    if product["stock"] < 1:
        flash(f"'{product['name']}' is out of stock.", "warning")
        return redirect(request.referrer or url_for("store.product_list"))

    cart = _get_cart()
    pid_str = str(product_id)
    current_qty = cart.get(pid_str, 0)
    new_qty = current_qty + qty

    # Cap at available stock
    if new_qty > product["stock"]:
        new_qty = product["stock"]
        flash(
            f"Only {product['stock']} unit(s) of '{product['name']}' available. "
            "Quantity adjusted.",
            "warning",
        )
    else:
        flash(f"'{product['name']}' added to your cart.", "success")

    cart[pid_str] = new_qty
    _save_cart(cart)

    return redirect(request.referrer or url_for("store.product_list"))


@cart_bp.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    """
    POST /cart/update — update quantities for all cart items at once.

    Expects form fields named  quantity_<product_id>  for each item.
    Items set to 0 or less are removed from the cart.
    Quantities are capped at available stock.
    """
    cart = _get_cart()
    if not cart:
        return redirect(url_for("cart.cart_view"))

    # Fetch current stock for all items
    product_ids = [int(pid) for pid in cart.keys()]
    placeholders = ",".join("?" * len(product_ids))
    conn = get_db_connection()
    rows = conn.execute(
        f"SELECT id, name, stock FROM products WHERE id IN ({placeholders})",
        product_ids,
    ).fetchall()
    conn.close()
    stock_map = {str(row["id"]): (row["stock"], row["name"]) for row in rows}

    updated_cart = {}
    for pid_str in cart:
        field_name = f"quantity_{pid_str}"
        raw = request.form.get(field_name, "").strip()

        try:
            qty = int(raw)
        except ValueError:
            qty = cart[pid_str]           # keep old if invalid input

        if qty <= 0:
            continue                      # remove item

        if pid_str in stock_map:
            max_stock, prod_name = stock_map[pid_str]
            if qty > max_stock:
                qty = max_stock
                flash(
                    f"Quantity for '{prod_name}' adjusted to available stock ({max_stock}).",
                    "warning",
                )

        updated_cart[pid_str] = qty

    _save_cart(updated_cart)
    flash("Cart updated.", "success")
    return redirect(url_for("cart.cart_view"))


@cart_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def cart_remove(product_id):
    """
    POST /cart/remove/<product_id> — remove a single product from the cart.
    """
    cart = _get_cart()
    pid_str = str(product_id)
    if pid_str in cart:
        del cart[pid_str]
        _save_cart(cart)
        flash("Item removed from your cart.", "info")
    return redirect(url_for("cart.cart_view"))


@cart_bp.route("/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    """
    POST /cart/clear — empty the entire cart.
    """
    _save_cart({})
    flash("Your cart has been cleared.", "info")
    return redirect(url_for("cart.cart_view"))


# ===========================================================================
# CHECKOUT
# ===========================================================================

@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """
    GET  /checkout — display the checkout page.
    POST /checkout — place the order.
    """
    items, total = _build_cart_details()

    if not items:
        flash("Your cart is empty. Add some products before checking out.", "warning")
        return redirect(url_for("store.product_list"))

    # Fetch current user info for display
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    if request.method == "GET":
        return render_template(
            "cart/checkout.html",
            items=items,
            total=total,
            user=user,
        )

    # ------------------------------------------------------------------
    # POST — place the order
    # ------------------------------------------------------------------
    payment_method = request.form.get("payment_method", "").strip()
    if not payment_method:
        flash("Please select a payment method.", "danger")
        return render_template(
            "cart/checkout.html",
            items=items,
            total=total,
            user=user,
        )

    cart = _get_cart()
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("store.product_list"))

    user_id = session["user_id"]

    # Use a raw connection for the explicit transaction
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN")                # explicit transaction start

        # 1. Re-fetch all products inside the transaction for consistency
        product_ids = [int(pid) for pid in cart.keys()]
        placeholders = ",".join("?" * len(product_ids))
        products_in_db = conn.execute(
            f"SELECT id, name, price, stock FROM products WHERE id IN ({placeholders})",
            product_ids,
        ).fetchall()
        db_map = {str(row["id"]): row for row in products_in_db}

        # 2. Validate stock and compute server-side total
        server_total = 0.0
        line_items = []          # (product_id, quantity, unit_price)

        for pid_str, qty in cart.items():
            if pid_str not in db_map:
                conn.rollback()
                conn.close()
                flash(
                    "One or more products in your cart no longer exist. "
                    "Your cart has been updated.",
                    "danger",
                )
                # Remove stale item
                cart_now = _get_cart()
                cart_now.pop(pid_str, None)
                _save_cart(cart_now)
                return redirect(url_for("cart.cart_view"))

            prod = db_map[pid_str]

            if qty > prod["stock"]:
                conn.rollback()
                conn.close()
                flash(
                    f"Only {prod['stock']} unit(s) of '{prod['name']}' are available. "
                    "Please update your cart.",
                    "danger",
                )
                return redirect(url_for("cart.cart_view"))

            unit_price = prod["price"]      # always from DB
            server_total += unit_price * qty
            line_items.append((int(pid_str), qty, unit_price))

        server_total = round(server_total, 2)

        # 3. Insert order record
        cursor = conn.execute(
            "INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, ?)",
            (user_id, server_total, "Pending"),
        )
        order_id = cursor.lastrowid

        # 4. Insert order_items and reduce stock with negative-stock guard
        for prod_id, qty, unit_price in line_items:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) "
                "VALUES (?, ?, ?, ?)",
                (order_id, prod_id, qty, unit_price),
            )
            # Enforce stock >= qty in the UPDATE query directly to prevent negative stock
            stock_update = conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (qty, prod_id, qty),
            )
            if stock_update.rowcount != 1:
                conn.rollback()
                conn.close()
                flash(
                    "Stock changed or is insufficient for one or more items. Please update your cart.",
                    "danger",
                )
                return redirect(url_for("cart.cart_view"))

        conn.commit()
        conn.close()

    except Exception as exc:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        flash(
            "An error occurred while placing your order. Please try again.",
            "danger",
        )
        # Log to stderr for dev visibility without exposing to user
        import traceback
        traceback.print_exc()
        return redirect(url_for("cart.checkout"))

    # 5. Clear cart on success
    _save_cart({})
    flash(
        f"Order #{order_id} placed successfully! Thank you for your purchase.",
        "success",
    )
    return redirect(url_for("cart.order_detail", order_id=order_id))


# ===========================================================================
# MY ORDERS
# ===========================================================================

@cart_bp.route("/orders")
@login_required
def my_orders():
    """
    GET /orders — list all orders belonging to the logged-in customer.
    """
    user_id = session["user_id"]
    conn = get_db_connection()
    orders = conn.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_id = ?
        ORDER BY order_date DESC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template("cart/orders.html", orders=orders)


@cart_bp.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    """
    GET /order/<order_id> — view a specific order's details.

    Security: the user_id is always enforced in the query — customers
    cannot access another customer's order by manipulating the URL.
    """
    user_id = session["user_id"]
    conn = get_db_connection()

    order = conn.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE id = ? AND user_id = ?
    """, (order_id, user_id)).fetchone()

    if order is None:
        conn.close()
        abort(404)           # not found OR belongs to another user — same response

    items = conn.execute("""
        SELECT oi.quantity, oi.price,
               p.name AS product_name,
               p.image AS product_image,
               p.id   AS product_id,
               (oi.quantity * oi.price) AS subtotal
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()

    return render_template(
        "cart/order_detail.html",
        order=order,
        items=items,
    )


# ---------------------------------------------------------------------------
# Context processor — exposes cart item count to all templates
# ---------------------------------------------------------------------------
@cart_bp.app_context_processor
def inject_cart_count():
    """Make `cart_item_count` available in every template."""
    try:
        count = _cart_item_count()
    except Exception:
        count = 0
    return {"cart_item_count": count}
