"""
update_product_images.py
-------------------------
Updates the products in cyber_store.db with proper cybersecurity product details,
categories, and associates them with high-quality generated cybersecurity images.
Preserves existing product IDs (1, 2, 3) and order foreign keys.
"""
import sqlite3
import os
from database import DATABASE_PATH

PRODUCTS_DATA = [
    {
        "id": 1,
        "name": "Network Scanner Pro",
        "category_id": 1,
        "description": "Enterprise-grade network scanner and topology mapper featuring deep packet inspection, automated port discovery, and zero-latency threat detection.",
        "features": "Active Network Topology Mapping\nAutomated Port & Service Discovery\nDeep Packet Flow Inspection\nReal-Time Vulnerability Alerts",
        "price": 149.50,
        "license": "Enterprise",
        "compatibility": "Linux, Windows, macOS",
        "image": "network_scanner_pro.jpg",
        "stock": 15
    },
    {
        "id": 2,
        "name": "Vulnerability Scanner",
        "category_id": 2,
        "description": "Comprehensive automated vulnerability assessment suite with deep code inspection, CVE exploit scanning, and compliance tracking.",
        "features": "Automated CVE Database Sync\nZero-Day Exploit Identification\nWeb Application Vulnerability Audit\nPrioritized Remediation Roadmaps",
        "price": 149.50,
        "license": "Enterprise",
        "compatibility": "Linux, Windows",
        "image": "vulnerability_scanner.jpg",
        "stock": 18
    },
    {
        "id": 3,
        "name": "Password Manager Pro",
        "category_id": 3,
        "description": "Secure enterprise password vault engineered with zero-knowledge cryptography, biometric access control, and credential breach alerts.",
        "features": "Zero-Knowledge Encryption Vault\nMulti-Factor & Biometric Auth\nCredential Stuffing Detection\nAutomated Enterprise Key Rotation",
        "price": 300.00,
        "license": "Enterprise",
        "compatibility": "Windows, macOS, Linux, iOS, Android",
        "image": "password_manager_pro.jpg",
        "stock": 38
    },
    {
        "id": 4,
        "name": "File Encryption Suite",
        "category_id": 4,
        "description": "Military-grade cryptographic file and volume security suite with AES-256 GCM algorithms, digital signatures, and automated key exchange.",
        "features": "AES-256 GCM File & Disk Encryption\nAutomated Key Lifecycle Management\nMulti-User Cryptographic Signatures\nTamper-Proof Integrity Audits",
        "price": 189.00,
        "license": "Enterprise",
        "compatibility": "Windows, Linux, macOS",
        "image": "file_encryption_suite.jpg",
        "stock": 25
    },
    {
        "id": 5,
        "name": "Security Monitor",
        "category_id": 5,
        "description": "Real-time SOC threat telemetry monitor, global attack vector tracking, SIEM log collector, and instant incident response platform.",
        "features": "Real-Time SOC Telemetry Stream\nGlobal Cyber Threat Attack Map\nSIEM Ingestion & Heuristic Analytics\nAutomated Incident Containment",
        "price": 249.00,
        "license": "Enterprise",
        "compatibility": "Linux, Windows, Cloud",
        "image": "security_monitor.jpg",
        "stock": 20
    },
    {
        "id": 6,
        "name": "Endpoint Protection",
        "category_id": 6,
        "description": "Next-generation endpoint defense platform with behavioral heuristics, zero-day device isolation, and real-time ransomware defense.",
        "features": "AI-Powered Behavioral Heuristics\nReal-Time Ransomware Interception\nInstant Host Device Isolation\nContinuous Compliance Monitoring",
        "price": 169.00,
        "license": "Enterprise",
        "compatibility": "Windows, macOS, Linux",
        "image": "endpoint_protection.jpg",
        "stock": 30
    }
]

def update_products():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    for item in PRODUCTS_DATA:
        existing = cursor.execute("SELECT id FROM products WHERE id = ?", (item["id"],)).fetchone()
        if existing:
            cursor.execute("""
                UPDATE products
                SET name = ?,
                    category_id = ?,
                    description = ?,
                    features = ?,
                    price = ?,
                    license = ?,
                    compatibility = ?,
                    image = ?,
                    stock = ?
                WHERE id = ?;
            """, (
                item["name"],
                item["category_id"],
                item["description"],
                item["features"],
                item["price"],
                item["license"],
                item["compatibility"],
                item["image"],
                item["stock"],
                item["id"]
            ))
            print(f"Updated product #{item['id']}: {item['name']}")
        else:
            cursor.execute("""
                INSERT INTO products (id, name, category_id, description, features, price, license, compatibility, image, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                item["id"],
                item["name"],
                item["category_id"],
                item["description"],
                item["features"],
                item["price"],
                item["license"],
                item["compatibility"],
                item["image"],
                item["stock"]
            ))
            print(f"Inserted product #{item['id']}: {item['name']}")

    conn.commit()

    # Verify
    rows = cursor.execute("""
        SELECT p.id, p.name, c.name, p.price, p.image, p.stock
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.id ASC;
    """).fetchall()

    print("\nVerified Products in Database:")
    for r in rows:
        print(f"  #{r[0]}: {r[1]} | Category: {r[2]} | Price: ₹{r[3]:.2f} | Image: {r[4]} | Stock: {r[5]}")

    conn.close()

if __name__ == "__main__":
    update_products()
