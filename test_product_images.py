import os
import sys
from app import app
from database import get_db_connection

client = app.test_client()
conn = get_db_connection()
products = conn.execute("SELECT * FROM products ORDER BY id;").fetchall()
conn.close()

print(f"Total products in DB: {len(products)}")
assert len(products) == 6, f"Expected 6 products, got {len(products)}"

for p in products:
    img_name = p["image"]
    img_path = os.path.join("static", "images", "products", img_name)
    assert os.path.exists(img_path), f"Image file missing: {img_path}"
    img_size = os.path.getsize(img_path)
    assert img_size > 10000, f"Image file too small ({img_size}b): {img_path}"
    
    # Test static file serving via client
    res = client.get(f"/static/images/products/{img_name}")
    assert res.status_code == 200, f"Static image GET failed: {img_name}"
    
    # Test product detail page
    res_detail = client.get(f"/product/{p['id']}")
    assert res_detail.status_code == 200, f"Product detail failed for {p['name']}"
    assert img_name in res_detail.get_data(as_text=True), f"Image {img_name} missing from product detail"
    
    print(f"  [OK] Product #{p['id']} {p['name']}: Image {img_name} ({img_size:,} bytes)")

# Test product list
res_list = client.get("/products")
assert res_list.status_code == 200
html_list = res_list.get_data(as_text=True)
for p in products:
    assert p["image"] in html_list, f"{p['image']} missing in product list"

# Test public home
res_home = client.get("/")
assert res_home.status_code == 200
html_home = res_home.get_data(as_text=True)
for p in products:
    assert p["image"] in html_home, f"{p['image']} missing in home page"

print("ALL PRODUCT IMAGE VALIDATIONS PASSED!")
