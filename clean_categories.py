"""
clean_categories.py
-------------------
Clean incorrect/duplicate category data and ensure ONLY the 6 specified
categories exist in the Cyber Security Tools Store database.
Also ensures products are associated with the correct categories.
"""
import sqlite3
from database import DATABASE_PATH

PROPER_CATEGORIES = [
    (1, "Network Security", "Perimeter defense, intrusion prevention, deep packet inspection, and firewall management software."),
    (2, "Vulnerability Assessment", "Automated vulnerability scanners, penetration testing frameworks, and exploit discovery tools."),
    (3, "Password Security", "Enterprise password management, credential stuffing detection, and authentication enforcement."),
    (4, "Encryption", "Cryptographic libraries, file and disk encryption utilities, and secret management suites."),
    (5, "Security Monitoring", "Threat telemetry visualizers, SIEM log collectors, and real-time security operations center tools."),
    (6, "System Protection", "Endpoint defense, zero-day threat mitigation, anti-malware agents, and host integrity checkers.")
]

def clean_categories():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")
    cursor = conn.cursor()

    # 1. Clear out old category data
    cursor.execute("DELETE FROM categories;")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'categories';")

    # 2. Insert ONLY the 6 proper categories
    for cat_id, name, desc in PROPER_CATEGORIES:
        cursor.execute(
            "INSERT INTO categories (id, name, description) VALUES (?, ?, ?);",
            (cat_id, name, desc)
        )

    # 3. Associate products with the correct category (Network Security = id 1)
    # Also clean random numbers from product names and features
    cursor.execute("""
        UPDATE products
        SET name = 'PacketSentinel Pro',
            category_id = 1,
            description = 'High performance deep packet inspection and network security monitoring suite.',
            features = 'Real-time Packet Inspection\nPerimeter Threat Blocking\nZero-Latency Protocol Parsing\nAutomated Security Alerts'
        WHERE id = 1;
    """)

    cursor.execute("""
        UPDATE products
        SET name = 'PacketSentinel Enterprise',
            category_id = 1,
            description = 'Enterprise-grade packet inspection engine with multi-gigabit throughput support.',
            features = 'Multi-Gigabit Network Analysis\nDistributed Sensor Support\nCustom IDS/IPS Rule Sets\nCompliance Audit Logs'
        WHERE id = 2;
    """)

    cursor.execute("""
        UPDATE products
        SET name = 'PacketSentinel Cloud Defense',
            category_id = 1,
            description = 'Cloud and container network traffic inspection tool for hybrid cloud environments.',
            features = 'VPC Traffic Mirroring\nKubernetes Network Policy Auditing\nTLS 1.3 Flow Visibility\nCloud Security Telemetry'
        WHERE id = 3;
    """)

    # Update any other products if present to category 1
    cursor.execute("UPDATE products SET category_id = 1 WHERE category_id NOT IN (1, 2, 3, 4, 5, 6);")

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")

    # Verify results
    cats = cursor.execute("SELECT id, name, description FROM categories ORDER BY id ASC;").fetchall()
    print(f"Categories successfully updated ({len(cats)} categories):")
    for c in cats:
        print(f"  [{c[0]}] {c[1]}: {c[2]}")

    prods = cursor.execute("""
        SELECT p.id, p.name, p.category_id, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.id ASC;
    """).fetchall()
    print("\nProducts successfully updated:")
    for p in prods:
        print(f"  Product #{p[0]}: '{p[1]}' -> Category [{p[2]}] {p[3]}")

    conn.close()

if __name__ == "__main__":
    clean_categories()
