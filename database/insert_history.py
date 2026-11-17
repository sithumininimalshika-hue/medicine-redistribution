
import sqlite3
from datetime import date, timedelta

DATABASE = "database/medicine.db"

# Daily usage values for each hospital and medicine
usage_data = {
    (1, 1): 50,
    (1, 2): 20,
    (1, 3): 15,
    (1, 4): 10,
    (1, 5): 10,

    (2, 1): 40,
    (2, 2): 10,
    (2, 3): 10,
    (2, 4): 10,
    (2, 5): 10,

    (3, 1): 20,
    (3, 2): 15,
    (3, 3): 10,
    (3, 4): 10,
    (3, 5): 10
}


def insert_history():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    today = date.today()

    for (hospital_id, medicine_id), daily_usage in usage_data.items():

        for day in range(7):

            consumption_date = (
                today - timedelta(days=6 - day)
            ).isoformat()

            # Simulated small changes in daily consumption
            quantity_used = daily_usage + (day % 3) * 2

            cursor.execute("""
                INSERT INTO consumption_history
                (hospital_id, medicine_id, consumption_date, quantity_used)
                VALUES (?, ?, ?, ?)
            """, (
                hospital_id,
                medicine_id,
                consumption_date,
                quantity_used
            ))

    connection.commit()
    connection.close()

    print("Historical consumption records inserted successfully!")


if __name__ == "__main__":
    insert_history()
