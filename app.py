
from flask import Flask, render_template, request, redirect, url_for

from algorithms.stock_analysis import analyze_stock
from algorithms.redistribution import generate_recommendations
from algorithms.consumption_analysis import analyze_consumption
from algorithms.inventory_transfer import approve_transfer

app = Flask(__name__)


@app.route("/")
def home():

    stock_data = analyze_stock()

    recommendations = generate_recommendations()

    consumption_data = analyze_consumption()

    total_hospitals = 3
    total_medicines = 5

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
        total_hospitals=total_hospitals,
        total_medicines=total_medicines,
        critical_count=critical_count,
        low_count=low_count
    )


@app.route("/approve-transfer", methods=["POST"])
def approve_transfer_route():

    medicine = request.form.get("medicine")
    from_hospital = request.form.get("from_hospital")
    to_hospital = request.form.get("to_hospital")

    try:
        quantity = int(request.form.get("quantity", 0))
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

if __name__ == "__main__":
    app.run(debug=True)
