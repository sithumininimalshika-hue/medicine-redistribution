

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

from algorithms.stock_analysis import analyze_stock
from algorithms.redistribution import generate_recommendations
from algorithms.consumption_analysis import analyze_consumption
from algorithms.inventory_transfer import approve_transfer
from algorithms.expiry_analysis import analyze_expiry

import os
from pathlib import Path

_DEFAULT_MED_DB = Path(__file__).resolve().parent / "database" / "medicine.db"
MEDICINE_DB_PATH = os.environ.get("MEDICINE_DB_PATH", str(_DEFAULT_MED_DB))
app = Flask(__name__)


def _get_catalog_info():
    """Read live counts and medicine names from the database."""

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        total_hospitals = cursor.execute(
            "SELECT COUNT(*) FROM hospitals"
        ).fetchone()[0]

        total_medicines = cursor.execute(
            "SELECT COUNT(*) FROM medicines"
        ).fetchone()[0]

        medicine_names = [
            row[0]
            for row in cursor.execute(
                "SELECT name FROM medicines ORDER BY name"
            )
        ]

    finally:
        connection.close()

    return total_hospitals, total_medicines, medicine_names


def _get_hospitals():
    """Return hospitals with their inventory row counts for management UI."""

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        hospitals = [
            {
                "id": row[0],
                "name": row[1],
                "location": row[2],
                "stock_records": row[3],
            }
            for row in cursor.execute(
                """
                SELECT
                    h.id,
                    h.name,
                    h.location,
                    (SELECT COUNT(*) FROM inventory i WHERE i.hospital_id = h.id)
                FROM hospitals h
                ORDER BY h.name
                """
            )
        ]

    finally:
        connection.close()

    return hospitals


def _update_hospital(hospital_id, name, location):
    """Rename/relocate a hospital after checking for duplicate names."""

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        if not cursor.execute(
            "SELECT 1 FROM hospitals WHERE id = ?", (hospital_id,)
        ).fetchone():
            return False, "Hospital not found."

        duplicate = cursor.execute(
            "SELECT 1 FROM hospitals "
            "WHERE LOWER(name) = LOWER(?) AND id <> ?",
            (name, hospital_id)
        ).fetchone()

        if duplicate:
            return False, f'Hospital "{name}" already exists.'

        cursor.execute(
            "UPDATE hospitals SET name = ?, location = ? WHERE id = ?",
            (name, location, hospital_id)
        )
        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        return False, "Could not update hospital: " + str(error)

    finally:
        connection.close()

    return True, f'Hospital "{name}" updated.'


def _delete_hospital(hospital_id):
    """Delete a hospital and all inventory/history rows belonging to it."""

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        record = cursor.execute(
            "SELECT name FROM hospitals WHERE id = ?", (hospital_id,)
        ).fetchone()

        if not record:
            return False, "Hospital not found."

        name = record[0]

        cursor.execute(
            "DELETE FROM inventory WHERE hospital_id = ?", (hospital_id,)
        )
        cursor.execute(
            "DELETE FROM consumption_history WHERE hospital_id = ?",
            (hospital_id,)
        )
        cursor.execute(
            "DELETE FROM hospitals WHERE id = ?", (hospital_id,)
        )
        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        return False, "Could not delete hospital: " + str(error)

    finally:
        connection.close()

    return True, (
        f'Hospital "{name}" and its stock/history records were deleted.'
    )


def _add_hospital_with_stock(
    name,
    location,
    medicine_name,
    quantity,
    expiry_date
):
    """
    Insert a hospital together with its first medicine stock record.

    The medicine is reused when it already exists (case-insensitive) and
    created on the fly otherwise, so the separate "Add Medicine" action is
    no longer needed. All user values use parameterized queries.
    """

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        # The schema has no UNIQUE constraint, so reject duplicates here.
        duplicate = cursor.execute(
            "SELECT 1 FROM hospitals WHERE LOWER(name) = LOWER(?)",
            (name,)
        ).fetchone()

        if duplicate:
            return False, f'Hospital "{name}" already exists.'

        cursor.execute(
            "INSERT INTO hospitals (name, location) VALUES (?, ?)",
            (name, location)
        )
        hospital_id = cursor.lastrowid

        existing_medicine = cursor.execute(
            "SELECT id FROM medicines WHERE LOWER(name) = LOWER(?)",
            (medicine_name,)
        ).fetchone()

        medicine_created = False

        if existing_medicine:
            medicine_id = existing_medicine[0]
        else:
            cursor.execute(
                "INSERT INTO medicines (name, category) VALUES (?, ?)",
                (medicine_name, "General")
            )
            medicine_id = cursor.lastrowid
            medicine_created = True

        # The stock record the user entered
        cursor.execute(
            """
            INSERT INTO inventory
                (hospital_id, medicine_id, quantity, daily_usage, expiry_date)
            VALUES (?, ?, ?, 0, ?)
            """,
            (hospital_id, medicine_id, quantity, expiry_date)
        )

        # Register the new hospital for every other medicine with zero stock
        cursor.execute(
            """
            INSERT INTO inventory
                (hospital_id, medicine_id, quantity, daily_usage, expiry_date)
            SELECT ?, id, 0, 0, NULL
            FROM medicines
            WHERE id <> ?
            """,
            (hospital_id, medicine_id)
        )

        # If this is a brand new medicine, register it in existing hospitals
        if medicine_created:
            cursor.execute(
                """
                INSERT INTO inventory
                    (hospital_id, medicine_id, quantity, daily_usage, expiry_date)
                SELECT id, ?, 0, 0, NULL
                FROM hospitals
                WHERE id <> ?
                """,
                (medicine_id, hospital_id)
            )

        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        return False, "Could not add hospital: " + str(error)

    finally:
        connection.close()

    return True, (
        f'Hospital "{name}" added with {quantity} units of '
        f'"{medicine_name}" (expiry {expiry_date}).'
    )


@app.route("/")
def home():

    # Analyze stock (grouped by hospital so row actions stay together)
    stock_data = sorted(
        analyze_stock(),
        key=lambda item: (item["hospital"], item["medicine"])
    )

    # Prepare chart data
    chart_data = {}

    for item in stock_data:
        medicine = item["medicine"]

        if medicine not in chart_data:
            chart_data[medicine] = []

        chart_data[medicine].append({
            "hospital": item["hospital"],
            "quantity": item["quantity"]
        })

    # Generate recommendations
    recommendations = generate_recommendations()

    # Analyze consumption and expiry
    consumption_data = analyze_consumption()
    expiry_data = analyze_expiry()

    # Dashboard statistics (live counts, so additions show up immediately)
    total_hospitals, total_medicines, medicine_names = _get_catalog_info()
    hospitals = _get_hospitals()

    # Used by the stock table to attach row actions to the right hospital
    hospital_lookup = {
        hospital["name"]: {
            "id": hospital["id"],
            "location": hospital["location"],
        }
        for hospital in hospitals
    }

    critical_count = sum(
        1 for item in stock_data
        if item["status"] == "Critical"
    )

    low_count = sum(
        1 for item in stock_data
        if item["status"] == "Low"
    )

    return render_template(
        "index.html",
        stock_data=stock_data,
        recommendations=recommendations,
        consumption_data=consumption_data,
        expiry_data=expiry_data,
        total_hospitals=total_hospitals,
        total_medicines=total_medicines,
        critical_count=critical_count,
        low_count=low_count,
        chart_data=chart_data,
        medicine_names=medicine_names,
        hospitals=hospitals,
        hospital_lookup=hospital_lookup
    )


@app.route("/approve-transfer", methods=["POST"])
def approve_transfer_route():

    medicine = request.form.get("medicine")
    from_hospital = request.form.get("from_hospital")
    to_hospital = request.form.get("to_hospital")

    try:
        quantity = int(request.form.get("quantity", 0))

        if quantity <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return redirect(url_for(
            "home",
            transfer_message="Invalid transfer quantity.",
            transfer_success=0
        ))

    success, message = approve_transfer(
        medicine,
        from_hospital,
        to_hospital,
        quantity
    )

    return redirect(url_for(
        "home",
        transfer_message=message,
        transfer_success=int(success)
    ))


@app.route("/search", methods=["GET"])
def search_medicine():

    medicine_name = request.args.get("medicine", "").strip()

    search_results = []

    if medicine_name:

        connection = sqlite3.connect(MEDICINE_DB_PATH)

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    hospitals.name,
                    medicines.name,
                    inventory.quantity,
                    inventory.daily_usage,
                    inventory.expiry_date
                FROM inventory
                JOIN hospitals
                    ON inventory.hospital_id = hospitals.id
                JOIN medicines
                    ON inventory.medicine_id = medicines.id
                WHERE medicines.name LIKE ?
                ORDER BY hospitals.name
            """, ("%" + medicine_name + "%",))

            records = cursor.fetchall()

            for hospital, medicine, quantity, usage, expiry in records:

                if usage > 0:
                    days_remaining = round(quantity / usage, 1)
                else:
                    days_remaining = None

                search_results.append({
                    "hospital": hospital,
                    "medicine": medicine,
                    "quantity": quantity,
                    "daily_usage": usage,
                    "days_remaining": days_remaining,
                    "expiry_date": expiry
                })

        finally:
            connection.close()

    return render_template(
        "search.html",
        medicine_name=medicine_name,
        search_results=search_results
    )


@app.route("/add-hospital", methods=["POST"])
def add_hospital_route():

    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    medicine_name = request.form.get("medicine", "").strip()
    expiry_date = request.form.get("expiry_date", "").strip()

    try:
        quantity = int(request.form.get("quantity", 0))

        if quantity < 0:
            raise ValueError

    except (ValueError, TypeError):
        quantity = None

    try:
        date.fromisoformat(expiry_date)
    except ValueError:
        expiry_date = ""

    if (
        not name
        or not location
        or not medicine_name
        or quantity is None
        or not expiry_date
    ):
        success = False
        message = (
            "Hospital, medicine, current stock and a valid expiry date "
            "are required."
        )
    else:
        success, message = _add_hospital_with_stock(
            name,
            location,
            medicine_name,
            quantity,
            expiry_date
        )

    redirect_args = {
        "add_message": message,
        "add_success": int(success)
    }

    if not success:
        redirect_args["open_add"] = 1

    return redirect(url_for("home", **redirect_args))


@app.route("/edit-hospital", methods=["POST"])
def edit_hospital_route():

    try:
        hospital_id = int(request.form.get("hospital_id", 0))
    except (ValueError, TypeError):
        hospital_id = 0

    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()

    if not hospital_id or not name or not location:
        success = False
        message = "Hospital ID, name and location are required."
    else:
        success, message = _update_hospital(hospital_id, name, location)

    return redirect(url_for(
        "home",
        add_message=message,
        add_success=int(success)
    ))


@app.route("/delete-hospital", methods=["POST"])
def delete_hospital_route():

    try:
        hospital_id = int(request.form.get("hospital_id", 0))
    except (ValueError, TypeError):
        hospital_id = 0

    if not hospital_id:
        success = False
        message = "A valid hospital ID is required."
    else:
        success, message = _delete_hospital(hospital_id)

    return redirect(url_for(
        "home",
        add_message=message,
        add_success=int(success)
    ))


if __name__ == "__main__":
    app.run(debug=True)
