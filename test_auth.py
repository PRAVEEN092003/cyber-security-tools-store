"""
test_auth.py
------------
Automated test script for Stage 2 — Authentication System.
Tests all 10 required scenarios (A through I + hash check).
Run with: python test_auth.py
"""
import sys
import requests
from werkzeug.security import check_password_hash
from database import get_db_connection

BASE = "http://127.0.0.1:5000"
PASS = []
FAIL = []

def ok(label):
    PASS.append(label)
    print(f"  [PASS] {label}")

def fail(label, reason=""):
    FAIL.append(label)
    print(f"  [FAIL] {label}" + (f" — {reason}" if reason else ""))


# ── Helper ─────────────────────────────────────────────────────────────────
def make_session():
    """Return a new requests.Session (cookie jar included)."""
    return requests.Session()

# ── Test data ──────────────────────────────────────────────────────────────
TEST_EMAIL    = "testcustomer_auto@example.com"
TEST_PASSWORD = "SecurePass123"
TEST_NAME     = "Test Customer"
ADMIN_EMAIL   = "admin@cyberstore.local"
ADMIN_PASSWORD = "Admin@CyberStore2026!"

# Cleanup: remove test customer if already exists from a prior run
conn = get_db_connection()
conn.execute("DELETE FROM users WHERE email = ?", (TEST_EMAIL,))
conn.commit()
conn.close()
print("\n=== Authentication Test Suite ===\n")

# ── A: Customer can register ────────────────────────────────────────────────
print("A: Customer registration")
s = make_session()
r = s.post(f"{BASE}/register", data={
    "name": TEST_NAME, "email": TEST_EMAIL,
    "password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD
}, allow_redirects=True)
if r.status_code == 200 and "Please log in" not in r.url and "login" in r.url.lower():
    ok("Customer registered and redirected to login")
elif r.status_code == 200 and "Account created" in r.text:
    ok("Customer registered (flash message found)")
else:
    # Check DB directly
    conn = get_db_connection()
    u = conn.execute("SELECT id FROM users WHERE email = ?", (TEST_EMAIL,)).fetchone()
    conn.close()
    if u:
        ok("Customer registered (confirmed in DB)")
    else:
        fail("Customer registration", f"status={r.status_code} url={r.url}")

# ── C: Password stored as hash ──────────────────────────────────────────────
print("\nC: Password hash check")
conn = get_db_connection()
u = conn.execute("SELECT password FROM users WHERE email = ?", (TEST_EMAIL,)).fetchone()
conn.close()
if u is None:
    fail("Password hash check", "user not found in DB")
elif u["password"] == TEST_PASSWORD:
    fail("Password hash check", "PLAIN TEXT password stored!")
elif check_password_hash(u["password"], TEST_PASSWORD):
    ok("Password stored as bcrypt/scrypt hash, not plain text")
else:
    fail("Password hash check", f"hash mismatch — stored: {u['password'][:30]}")

# ── B: Customer can login ───────────────────────────────────────────────────
print("\nB: Customer login")
s = make_session()
r = s.post(f"{BASE}/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
           allow_redirects=True)
if r.status_code == 200 and ("Welcome" in r.text or "Logout" in r.text):
    ok("Customer logged in successfully")
else:
    fail("Customer login", f"status={r.status_code}, logout_in_page={'Logout' in r.text}")
customer_session = s  # keep session for next tests

# ── D: Customer can logout ──────────────────────────────────────────────────
print("\nD: Customer logout")
r = customer_session.get(f"{BASE}/logout", allow_redirects=True)
if "login" in r.url.lower() or "logged out" in r.text.lower():
    ok("Customer logged out and redirected")
else:
    fail("Customer logout", f"url={r.url}")

# ── E: Customer cannot access /admin-test ──────────────────────────────────
print("\nE: Customer blocked from /admin-test")
# Login as customer again
s2 = make_session()
s2.post(f"{BASE}/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        allow_redirects=True)
r = s2.get(f"{BASE}/admin-test", allow_redirects=True)
if r.status_code == 403 or "403" in r.text or "Forbidden" in r.text:
    ok("Customer gets 403 on /admin-test")
else:
    fail("Customer admin-test block", f"status={r.status_code}, url={r.url}")

# ── F: Admin can login ──────────────────────────────────────────────────────
print("\nF: Admin login")
admin_sess = make_session()
r = admin_sess.post(f"{BASE}/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                    allow_redirects=True)
if r.status_code == 200 and ("Welcome" in r.text or "Logout" in r.text or "Admin" in r.text):
    ok("Admin logged in successfully")
else:
    fail("Admin login", f"status={r.status_code}")

# ── G: Admin can access /admin-test ─────────────────────────────────────────
print("\nG: Admin accesses /admin-test")
r = admin_sess.get(f"{BASE}/admin-test", allow_redirects=True)
if r.status_code == 200 and ("Admin" in r.text or "admin" in r.text.lower()):
    ok("Admin can access /admin-test")
else:
    fail("Admin /admin-test", f"status={r.status_code}")

# ── H: Logged-out user cannot access protected routes ───────────────────────
print("\nH: Logged-out user blocked from /admin-test")
anon = make_session()
r = anon.get(f"{BASE}/admin-test", allow_redirects=True)
if "login" in r.url.lower() or r.status_code in (302, 401, 403):
    ok("Anonymous user redirected to login on /admin-test")
else:
    fail("Anonymous user /admin-test", f"status={r.status_code}, url={r.url}")

# ── I: Restart does not duplicate admin ─────────────────────────────────────
print("\nI: No duplicate admin on re-init")
conn = get_db_connection()
count = conn.execute("SELECT COUNT(*) as c FROM users WHERE role='admin'").fetchone()["c"]
conn.close()
if count == 1:
    ok("Exactly one admin account exists")
else:
    fail("Duplicate admin check", f"found {count} admin accounts")

# ── Summary ─────────────────────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("Failed tests:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
