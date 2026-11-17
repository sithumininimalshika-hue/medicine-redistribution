
import sqlite3

DATABASE = "database/medicine.db"


def approve_transfer(medicine, from_hospital, to_hospital, quantity):

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    try:

        # Find the medicine ID
        cursor.execute("""
            SELECT id FROM medicines
            WHERE name = ?
        """, (medicine,))

        medicine_record = cursor.fetchone()

        if medicine_record is None:
            return False, "Medicine not found."

        medicine_id = medicine_record[0]

        # Find donor hospital inventory
        cursor.execute("""
            SELECT id, quantity
            FROM inventory
            WHERE hospital_id = (
                SELECT id FROM hospitals WHERE name = ?
            )
            AND medicine_id = ?
        """, (from_hospital, medicine_id))

        donor = cursor.fetchone()

        # Find recipient hospital inventory
        cursor.execute("""
            SELECT id
            FROM inventory
            WHERE hospital_id = (
                SELECT id FROM hospitals WHERE name = ?
            )
            AND medicine_id = ?
        """, (to_hospital, medicine_id))

        recipient = cursor.fetchone()

        if donor is None or recipient is None:
            return False, "Hospital inventory not found."

        donor_id, donor_quantity = donor
        recipient_id = recipient[0]

        # Validate transfer quantity
        if quantity <= 0:
            return False, "Transfer quantity must be positive."

        if quantity > donor_quantity:
            return False, "Insufficient donor stock."

        # Deduct from donor
        cursor.execute("""
            UPDATE inventory
            SET quantity = quantity - ?
            WHERE id = ?
        """, (quantity, donor_id))

        # Add to recipient
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
