

from flask import Flask, render_template, request, redirect, url_for
import sqlite3

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


def _get_catalog_counts():
    """Read live hospital and medicine counts from the database."""

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        total_hospitals = cursor.execute(
            "SELECT COUNT(*) FROM hospitals"
        ).fetchone()[0]

        total_medicines = cursor.execute(
            "SELECT COUNT(*) FROM medicines"
        ).fetchone()[0]

    finally:
        connection.close()

    return total_hospitals, total_medicines


def _add_catalog_record(
    table,
    detail_column,
    other_table,
    fk_column,
    name,
    detail,
    label
):
    """
    Insert a hospital or medicine, then seed zero-stock inventory rows so the
    new record appears in stock analysis right away.

    Table/column names come from the calling route's internal constants —
    never from user input — so they are safe to concatenate into SQL. All
    user-provided values still use parameterized queries.
    """

    connection = sqlite3.connect(MEDICINE_DB_PATH)

    try:
        cursor = connection.cursor()

        # The schema has no UNIQUE constraint, so reject duplicates here.
        duplicate = cursor.execute(
            "SELECT 1 FROM " + table + " WHERE LOWER(name) = LOWER(?)",
            (name,)
        ).fetchone()

        if duplicate:
            return False, f'{label} "{name}" already exists.'

        cursor.execute(
            "INSERT INTO " + table + " (name, " + detail_column + ") "
            "VALUES (?, ?)",
            (name, detail)
        )
        record_id = cursor.lastrowid

        other_ids = [
            row[0]
            for row in cursor.execute(
                "SELECT id FROM " + other_table + " ORDER BY id"
            )
        ]

        if fk_column == "hospital_id":
            inventory_rows = [
                (record_id, other_id) for other_id in other_ids
            ]
        else:
            inventory_rows = [
                (other_id, record_id) for other_id in other_ids
            ]

        cursor.executemany(
            """
            INSERT INTO inventory
                (hospital_id, medicine_id, quantity, daily_usage, expiry_date)
            VALUES (?, ?, 0, 0, NULL)
            """,
            inventory_rows
        )

        connection.commit()

    except sqlite3.Error as error:
        connection.rollback()
        return False, "Could not add " + label.lower() + ": " + str(error)

    finally:
        connection.close()

    return True, (
        f'{label} "{name}" added with '
        f'{len(other_ids)} inventory records.'
    )


@app.route("/")
def home():

    # Analyze stock
    stock_data = analyze_stock()

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
    total_hospitals, total_medicines = _get_catalog_counts()

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
        chart_data=chart_data
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

    if not name or not location:
        success = False
        message = "Hospital name and location are required."
    else:
        success, message = _add_catalog_record(
            "hospitals",
            "location",
            "medicines",
            "hospital_id",
            name,
            location,
            "Hospital"
        )

    return redirect(url_for(
        "home",
        add_message=message,
        add_success=int(success)
    ))


@app.route("/add-medicine", methods=["POST"])
def add_medicine_route():

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()

    if not name or not category:
        success = False
        message = "Medicine name and category are required."
    else:
        success, message = _add_catalog_record(
            "medicines",
            "category",
            "hospitals",
            "medicine_id",
            name,
            category,
            "Medicine"
        )

    return redirect(url_for(
        "home",
        add_message=message,
        add_success=int(success)
    ))


if __name__ == "__main__":
    app.run(debug=True)
