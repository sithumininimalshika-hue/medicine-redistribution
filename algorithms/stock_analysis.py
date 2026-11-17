
import sqlite3

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "database" / "medicine.db"
DATABASE = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_DB))


def analyze_stock():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            hospitals.name,
            medicines.name,
            inventory.quantity,
            inventory.daily_usage
        FROM inventory
        JOIN hospitals
            ON inventory.hospital_id = hospitals.id
        JOIN medicines
            ON inventory.medicine_id = medicines.id
    """)

    records = cursor.fetchall()
    connection.close()

    results = []

    for hospital, medicine, quantity, daily_usage in records:

        if daily_usage <= 0:
            days_remaining = None
            status = "No recorded usage"

        else:
            days_remaining = quantity / daily_usage

            if days_remaining <= 3:
                status = "Critical"

            elif days_remaining <= 7:
                status = "Low"

            else:
                status = "Adequate"

        results.append({
            "hospital": hospital,
            "medicine": medicine,
            "quantity": quantity,
            "daily_usage": daily_usage,
            "days_remaining": days_remaining,
            "status": status
        })

    return results


if __name__ == "__main__":

    stock_data = analyze_stock()

    for item in stock_data:

        print("------------------------------")
        print("Hospital:", item["hospital"])
        print("Medicine:", item["medicine"])
        print("Current Stock:", item["quantity"])
        print("Daily Usage:", item["daily_usage"])

        if item["days_remaining"] is not None:
            print("Days Remaining:", round(item["days_remaining"], 2))
        else:
            print("Days Remaining: Not available")

        print("Stock Status:", item["status"])
