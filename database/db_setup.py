
import sqlite3

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "database" / "medicine.db"
DATABASE = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_DB))


def setup_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Create healthcare facilities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    # Create medicines table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    # Create inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER,
            medicine_id INTEGER,
            quantity INTEGER NOT NULL,
            daily_usage REAL NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    """)

    # Insert sample hospitals
    cursor.executemany("""
        INSERT INTO hospitals (name, location)
        VALUES (?, ?)
    """, [
        ("Central Hospital", "Colombo"),
        ("City Hospital", "Kandy"),
        ("Rural Hospital", "Galle")
    ])

    # Insert sample medicines
    cursor.executemany("""
        INSERT INTO medicines (name, category)
        VALUES (?, ?)
    """, [
        ("Paracetamol", "Pain Relief"),
        ("Amoxicillin", "Antibiotic"),
        ("Cetirizine", "Antihistamine"),
        ("Omeprazole", "Gastric"),
        ("Salbutamol", "Respiratory")
    ])

    # Insert sample inventory
    cursor.executemany("""
        INSERT INTO inventory
        (hospital_id, medicine_id, quantity, daily_usage)
        VALUES (?, ?, ?, ?)
    """, [
        (1, 1, 500, 50),
        (1, 2, 100, 20),
        (1, 3, 300, 15),
        (1, 4, 250, 10),
        (1, 5, 80, 10),

        (2, 1, 100, 40),
        (2, 2, 400, 10),
        (2, 3, 200, 10),
        (2, 4, 150, 10),
        (2, 5, 200, 10),

        (3, 1, 600, 20),
        (3, 2, 80, 15),
        (3, 3, 100, 10),
        (3, 4, 300, 10),
        (3, 5, 50, 10)
    ])

    connection.commit()
    connection.close()

    print("Database created successfully!")


if __name__ == "__main__":
    setup_database()
