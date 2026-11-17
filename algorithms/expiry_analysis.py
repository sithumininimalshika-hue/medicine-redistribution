
import sqlite3
from datetime import date

DATABASE = "database/medicine.db"

WARNING_DAYS = 30


def analyze_expiry():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            hospitals.name,
            medicines.name,
            inventory.quantity,
            inventory.expiry_date

        FROM inventory

        JOIN hospitals
            ON inventory.hospital_id = hospitals.id

        JOIN medicines
            ON inventory.medicine_id = medicines.id

        WHERE inventory.expiry_date IS NOT NULL
    """)

    records = cursor.fetchall()
    connection.close()

    results = []

    today = date.today()

    for hospital, medicine, quantity, expiry_date in records:

        expiry = date.fromisoformat(expiry_date)

        days_remaining = (expiry - today).days

        if days_remaining < 0:
            status = "Expired"

        elif days_remaining <= WARNING_DAYS:
            status = "Expiring Soon"

        else:
            status = "Safe"

        results.append({

            "hospital": hospital,
            "medicine": medicine,
            "quantity": quantity,
            "expiry_date": expiry_date,
            "days_remaining": days_remaining,
            "status": status

        })

    return results


if __name__ == "__main__":

    results = analyze_expiry()

    print("\nMEDICINE EXPIRY ANALYSIS")
    print("=" * 45)

    for item in results:

        print("\nHospital:", item["hospital"])
        print("Medicine:", item["medicine"])
        print("Quantity:", item["quantity"])
        print("Expiry Date:", item["expiry_date"])
        print("Days Remaining:", item["days_remaining"])
        print("Expiry Status:", item["status"])
