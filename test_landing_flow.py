"""
test_landing_flow.py
--------------------
Automated verification of role-based landing, navigation, and simple home experience.
Tests Guest, Customer, and Admin flows.
"""
import sys
import os
from app import app
from database import get_db_connection, init_db
from werkzeug.security import generate_password_hash

def run_tests():
    app.config['WTF_CSRF_ENABLED'] = False
    init_db()
    client = app.test_client()

    # Ensure test customer exists
    TEST_EMAIL = "cust_test@example.com"
    TEST_PW = "CustomerPass123"
    TEST_NAME = "Alice Defender"

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE email = ?", (TEST_EMAIL,))
    conn.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (TEST_NAME, TEST_EMAIL, generate_password_hash(TEST_PW), "customer")
    )
    conn.commit()

    # Get admin credentials
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cyberstore.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@CyberStore2026!")
    admin_row = conn.execute("SELECT * FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if admin_row:
        ADMIN_EMAIL = admin_row['email']
    conn.close()

    print("=== STARTING LANDING & ROLE EXPERIENCE TESTS ===\n")
    passed = 0
    failed = 0

    def assert_test(cond, title):
        nonlocal passed, failed
        if cond:
            print(f" [PASS] {title}")
            passed += 1
        else:
            print(f" [FAIL] {title}")
            failed += 1

    # 1. GUEST: Public Home
    r = client.get('/', follow_redirects=False)
    assert_test(r.status_code == 200, "Guest GET / returns 200 OK")
    html = r.get_data(as_text=True)
    assert_test("CYBERSEC <span class=\"brand-accent\">STORE</span>" in html or "CYBERSEC" in html, "Guest sees CYBERSEC STORE brand")
    assert_test("Secure Tools." in html and "Smarter Protection." in html, "Guest sees Hero heading")
    assert_test("Browse Products" in html and "Login" in html, "Guest sees Hero action buttons")
    assert_test("Security Tools" in html, "Guest sees Security Tools section")
    assert_test("Admin Dashboard" not in html and "Customer Home" not in html, "Guest does not see role-specific navigation")
    assert_test("TOTAL REVENUE" not in html and "Customers" not in html, "Guest does not see admin telemetry")

    # 2. GUEST: Unauthenticated /dashboard
    r = client.get('/dashboard', follow_redirects=False)
    assert_test(r.status_code == 302 and "/login" in r.location, "Guest accessing /dashboard redirects to login")

    # 3. CUSTOMER: Login redirection
    with client.session_transaction() as sess:
        sess.clear()

    # Post login form
    r = client.post('/login', data={"email": TEST_EMAIL, "password": TEST_PW}, follow_redirects=False)
    assert_test(r.status_code == 302 and r.location.endswith('/dashboard'), "Customer login redirects to /dashboard")

    # Follow redirect to customer dashboard
    r_cust_dash = client.get('/dashboard', follow_redirects=True)
    cust_html = r_cust_dash.get_data(as_text=True)
    assert_test(r_cust_dash.status_code == 200, "Customer dashboard returns 200 OK")
    assert_test(f"Welcome back" in cust_html and TEST_NAME in cust_html, "Customer dashboard greets customer by name")
    assert_test("Browse Products" in cust_html, "Customer dashboard contains Browse Products card")
    assert_test("My Orders" in cust_html, "Customer dashboard contains My Orders card")
    assert_test("Shopping Cart" in cust_html, "Customer dashboard contains Shopping Cart card")
    assert_test("Customer Home" in cust_html, "Customer navbar contains Customer Home link")
    assert_test("Admin Dashboard" not in cust_html, "Customer navbar does NOT contain Admin Dashboard")

    # 4. CUSTOMER visiting / redirects to /dashboard
    r_root = client.get('/', follow_redirects=False)
    assert_test(r_root.status_code == 302 and r_root.location.endswith('/dashboard'), "Logged-in Customer visiting / redirects to /dashboard")

    # 5. CUSTOMER visiting /admin/ gets 403
    r_admin_forbidden = client.get('/admin/', follow_redirects=False)
    assert_test(r_admin_forbidden.status_code == 403, "Logged-in Customer accessing /admin/ gets 403 Forbidden")

    # 6. ADMIN: Login redirection
    client.get('/logout') # clear session
    r_admin_login = client.post('/login', data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, follow_redirects=False)
    assert_test(r_admin_login.status_code == 302 and "/admin" in r_admin_login.location, "Admin login redirects to /admin/")

    # Admin dashboard
    r_admin_dash = client.get('/admin/', follow_redirects=True)
    admin_html = r_admin_dash.get_data(as_text=True)
    assert_test(r_admin_dash.status_code == 200, "Admin dashboard returns 200 OK")
    assert_test("Admin Dashboard" in admin_html, "Admin dashboard header present")
    assert_test("CUSTOMERS" in admin_html and "PRODUCTS" in admin_html and "CATEGORIES" in admin_html and "ORDERS" in admin_html and "TOTAL REVENUE" in admin_html, "All 5 core telemetry metrics present in Admin Dashboard")
    assert_test("Admin Dashboard" in admin_html and "Categories" in admin_html and "Customers" in admin_html, "Admin navigation visible")
    assert_test("Customer Home" not in admin_html, "Admin navbar does NOT contain Customer Home")

    # 7. ADMIN visiting / redirects to /admin/
    r_admin_root = client.get('/', follow_redirects=False)
    assert_test(r_admin_root.status_code == 302 and "/admin" in r_admin_root.location, "Logged-in Admin visiting / redirects to /admin/")

    # 8. LOGOUT
    r_logout = client.get('/logout', follow_redirects=False)
    assert_test(r_logout.status_code == 302 and "/login" in r_logout.location, "Logout clears session and redirects to login")

    print(f"\n==========================================")
    print(f"Total Tests: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print(f"==========================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
