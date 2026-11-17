
import sqlite3

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "database" / "medicine.db"
DATABASE = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_DB))


def create_history_table():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumption_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            hospital_id INTEGER NOT NULL,

            medicine_id INTEGER NOT NULL,

            consumption_date TEXT NOT NULL,

            quantity_used INTEGER NOT NULL,

            FOREIGN KEY (hospital_id) REFERENCES hospitals(id),

            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    """)

    connection.commit()
    connection.close()

    print("Consumption history table created successfully!")


if __name__ == "__main__":
    create_history_table()
