
import sqlite3

import os
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "database" / "medicine.db"
DATABASE = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_DB))


def analyze_consumption():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            hospitals.name,
            medicines.name,
            consumption_history.consumption_date,
            consumption_history.quantity_used

        FROM consumption_history

        JOIN hospitals
            ON consumption_history.hospital_id = hospitals.id

        JOIN medicines
            ON consumption_history.medicine_id = medicines.id

        ORDER BY
            hospitals.name,
            medicines.name,
            consumption_history.consumption_date
    """)

    records = cursor.fetchall()
    connection.close()

    grouped_data = {}

    # Group records by hospital and medicine
    for hospital, medicine, date, quantity in records:

        key = (hospital, medicine)

        grouped_data.setdefault(key, [])

        grouped_data[key].append(quantity)

    results = []

    # Analyse consumption for each hospital and medicine
    for (hospital, medicine), quantities in grouped_data.items():

        average_usage = sum(quantities) / len(quantities)

        first_half = quantities[:len(quantities) // 2]
        second_half = quantities[len(quantities) // 2:]

        if not first_half or not second_half:
            # Too few records to compare two halves of the period
            trend = "Stable"

        else:
            first_average = sum(first_half) / len(first_half)
            second_average = sum(second_half) / len(second_half)

            if second_average > first_average * 1.05:
                trend = "Increasing"

            elif second_average < first_average * 0.95:
                trend = "Decreasing"

            else:
                trend = "Stable"

        results.append({

            "hospital": hospital,
            "medicine": medicine,
            "average_usage": round(average_usage, 2),
            "trend": trend

        })

    return results


if __name__ == "__main__":

    results = analyze_consumption()

    print("\nMEDICINE CONSUMPTION ANALYSIS")
    print("=" * 45)

    for item in results:

        print("\nHospital:", item["hospital"])
        print("Medicine:", item["medicine"])
        print("Average Daily Consumption:", item["average_usage"])
        print("Consumption Trend:", item["trend"])
