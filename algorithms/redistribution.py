
import sqlite3

DATABASE = "database/medicine.db"

TARGET_DAYS = 7


def generate_recommendations():

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

    # Group inventory records by medicine
    medicine_data = {}

    for hospital, medicine, quantity, daily_usage in records:

        medicine_data.setdefault(medicine, [])

        if daily_usage > 0:
            days_remaining = quantity / daily_usage
        else:
            days_remaining = None

        medicine_data[medicine].append({
            "hospital": hospital,
            "quantity": quantity,
            "daily_usage": daily_usage,
            "days_remaining": days_remaining
        })

    recommendations = []

    # Analyze each medicine separately
    for medicine, hospitals in medicine_data.items():

        recipients = []
        donors = []

        for hospital in hospitals:

            days = hospital["days_remaining"]

            if days is None:
                continue

            # Hospitals needing medicine
            if days <= TARGET_DAYS:

                required_stock = (
                    hospital["daily_usage"] * TARGET_DAYS
                )

                shortage = max(
                    0,
                    required_stock - hospital["quantity"]
                )

                if shortage > 0:
                    recipients.append({
                        **hospital,
                        "shortage": shortage
                    })

            # Hospitals with transferable excess stock
            else:

                safe_stock = (
                    hospital["daily_usage"] * TARGET_DAYS
                )

                excess = max(
                    0,
                    hospital["quantity"] - safe_stock
                )

                if excess > 0:
                    donors.append({
                        **hospital,
                        "excess": excess
                    })

        # Give priority to hospitals with fewer days remaining
        recipients.sort(
            key=lambda item: item["days_remaining"]
        )

        # Prefer donors with the largest transferable excess
        donors.sort(
            key=lambda item: item["excess"],
            reverse=True
        )

        # Match donors with recipients
        for recipient in recipients:

            remaining_need = recipient["shortage"]

            for donor in donors:

                if remaining_need <= 0:
                    break

                if donor["excess"] <= 0:
                    continue

                transfer_quantity = min(
                    remaining_need,
                    donor["excess"]
                )

                recommendations.append({
                    "medicine": medicine,
                    "from_hospital": donor["hospital"],
                    "to_hospital": recipient["hospital"],
                    "quantity": int(transfer_quantity),
                    "reason": (
                        f'{recipient["hospital"]} has only '
                        f'{recipient["days_remaining"]:.1f} days '
                        f'of stock remaining. '
                        f'{donor["hospital"]} has transferable '
                        f'excess stock while retaining at least '
                        f'{TARGET_DAYS} days of its own supply.'
                    )
                })

                donor["excess"] -= transfer_quantity
                remaining_need -= transfer_quantity

    return recommendations


if __name__ == "__main__":

    results = generate_recommendations()

    print("\nMEDICINE REDISTRIBUTION RECOMMENDATIONS")
    print("=" * 45)

    if not results:
        print("No redistribution recommendations available.")

    for item in results:

        print("\nMedicine:", item["medicine"])
        print("From:", item["from_hospital"])
        print("To:", item["to_hospital"])
        print("Transfer Quantity:", item["quantity"])
        print("Reason:", item["reason"])
