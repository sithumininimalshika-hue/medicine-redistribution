
import sqlite3
from datetime import date, timedelta

DATABASE = "database/medicine.db"

TARGET_DAYS = 7
EXPIRY_WARNING_DAYS = 30


def approve_transfer(medicine, from_hospital, to_hospital, quantity):

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # Validate transfer quantity
        if quantity <= 0:
            return False, "Invalid transfer quantity."

        # Find medicine ID
        cursor.execute("""
            SELECT id FROM medicines
            WHERE name = ?
        """, (medicine,))

        medicine_record = cursor.fetchone()

        if medicine_record is None:
            return False, "Medicine not found."

        medicine_id = medicine_record[0]

        # Find donor inventory
        cursor.execute("""
            SELECT
                inventory.id,
                inventory.quantity,
                inventory.daily_usage,
                inventory.expiry_date
            FROM inventory
            JOIN hospitals
                ON inventory.hospital_id = hospitals.id
            WHERE hospitals.name = ?
            AND inventory.medicine_id = ?
        """, (from_hospital, medicine_id))

        donor = cursor.fetchone()

        if donor is None:
            return False, "Donor inventory not found."

        donor_id, donor_quantity, donor_usage, expiry_date = donor

        # Find recipient inventory
        cursor.execute("""
            SELECT inventory.id
            FROM inventory
            JOIN hospitals
                ON inventory.hospital_id = hospitals.id
            WHERE hospitals.name = ?
            AND inventory.medicine_id = ?
        """, (to_hospital, medicine_id))

        recipient = cursor.fetchone()

        if recipient is None:
            return False, "Recipient inventory not found."

        recipient_id = recipient[0]

        # Check expiry date
        if expiry_date is None:
            return False, "Donor stock has no expiry date."

        expiry = date.fromisoformat(expiry_date)

        if expiry <= date.today() + timedelta(
            days=EXPIRY_WARNING_DAYS
        ):
            return False, "Donor stock is expired or expiring soon."

        # Calculate safe transferable stock
        minimum_stock = donor_usage * TARGET_DAYS

        available_stock = max(
            0,
            donor_quantity - minimum_stock
        )

        if quantity > available_stock:
            return False, "Insufficient transferable stock."

        # Update inventory
        cursor.execute("""
            UPDATE inventory
            SET quantity = quantity - ?
            WHERE id = ?
        """, (quantity, donor_id))

        cursor.execute("""
            UPDATE inventory
            SET quantity = quantity + ?
            WHERE id = ?
        """, (quantity, recipient_id))

        connection.commit()

        return True, "Transfer approved successfully!"

    except Exception as error:

        connection.rollback()
        return False, str(error)

    finally:

        connection.close()
