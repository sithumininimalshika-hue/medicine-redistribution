
import sqlite3
from datetime import date, timedelta

DATABASE = "database/medicine.db"


def add_expiry_dates():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Check whether the expiry_date column already exists
    cursor.execute("PRAGMA table_info(inventory)")

    columns = [column[1] for column in cursor.fetchall()]

    if "expiry_date" not in columns:

        cursor.execute("""
            ALTER TABLE inventory
            ADD COLUMN expiry_date TEXT
        """)

    # Simulated expiry dates for existing inventory records
    today = date.today()

    cursor.execute("""
        SELECT id FROM inventory
        WHERE expiry_date IS NULL
    """)

    records = cursor.fetchall()

    expiry_offsets = [
        15, 90, 180, 60, 120,
        -5, 20, 150, 45, 200,
        10, 100, 75, 30, 160
    ]

    for index, record in enumerate(records):

        expiry_date = (
            today + timedelta(days=expiry_offsets[index % 15])
        ).isoformat()

        cursor.execute("""
            UPDATE inventory
            SET expiry_date = ?
            WHERE id = ?
        """, (expiry_date, record[0]))

    connection.commit()
    connection.close()

    print("Expiry dates added successfully!")


if __name__ == "__main__":
    add_expiry_dates()
