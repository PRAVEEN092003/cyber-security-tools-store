"""
database.py
-----------
Database initialization and helper functions for the Cyber Security Tools Store.
Uses Python's built-in sqlite3 module with parameterized queries.
"""

import sqlite3
import os

# Path to the SQLite database file
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'cyber_store.db')


def get_db_connection():
    """
    Create and return a new SQLite database connection.
    - Enables foreign key support.
    - Sets row_factory to sqlite3.Row for dict-like row access.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row          # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
    return conn


def init_db():
    """
    Initialize the database and create all required tables if they do not exist.
    This function is safe to call on every application start-up.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # Table: users
    # Stores customer and admin accounts.
    # Passwords must be stored as hashed values — never plain text.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            role       TEXT    NOT NULL DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ------------------------------------------------------------------
    # Table: categories
    # Groups products into logical security categories.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ------------------------------------------------------------------
    # Table: products
    # Stores all cyber security tool listings.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            category_id   INTEGER,
            description   TEXT,
            features      TEXT,
            price         REAL    NOT NULL,
            license       TEXT,
            compatibility TEXT,
            image         TEXT,
            stock         INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # ------------------------------------------------------------------
    # Table: orders
    # Represents a customer's purchase order.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            total_amount REAL    NOT NULL,
            status       TEXT    DEFAULT 'Pending',
            order_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ------------------------------------------------------------------
    # Table: order_items
    # Line items within an order — one row per product purchased.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity   INTEGER NOT NULL,
            price      REAL    NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully. All tables are ready.")
