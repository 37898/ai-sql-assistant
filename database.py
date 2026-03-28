import sqlite3

def create_db():
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        country TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        revenue REAL,
        order_date TEXT
    )
    """)

    # Insert sample data
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM orders")

    customers = [
        (1, "Alice", "USA"),
        (2, "Bob", "Canada"),
        (3, "Charlie", "USA")
    ]

    orders = [
        (1, 1, 100.0, "2024-01-01"),
        (2, 1, 200.0, "2024-01-02"),
        (3, 2, 150.0, "2024-01-03"),
        (4, 3, 300.0, "2024-01-04")
    ]

    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?)", customers)
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()

create_db()