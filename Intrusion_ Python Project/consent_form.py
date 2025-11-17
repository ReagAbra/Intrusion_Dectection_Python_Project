from flask import render_template, request, Blueprint, redirect, url_for, jsonify
import base64
import os
import time
import csv
from utils.auth import is_logged_in

consent_blueprint = Blueprint("consent", __name__)

os.makedirs("signatures", exist_ok=True)

CSV_FILE = "consents.csv"
DESIRED_HEADERS = ["first_name", "last_name", "id_number", "consent", "signature_file"]

# Overwrite CSV completely with only the header row
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(DESIRED_HEADERS)




@consent_blueprint.route("/consent", methods=["GET", "POST"])
def consent_form():
    if request.method == "POST":

        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        id_number = request.form["id_number"].strip()
        consent = request.form.get("consent", "No")
        signature_data = request.form.get("signature")

        # Check for duplicate IDs
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("id_number", "").strip() == id_number:
                    return render_template("consent_form.html", error = "This ID already exists. Duplicate entries are not allowed.")
                
                if row.get("first_name","").strip().lower() == first_name.lower() and row.get("last_name", "").strip().lower() == last_name.lower():
                    return render_template("consent_form.html", error = "Name already exists. Duplicate entries are not allowed.")

        # Save signature as PNG
        timestamp = int(time.time())
        signature_filename = f"signatures/{first_name}_{last_name}_{timestamp}.png"
        if signature_data:
            header, encoded = signature_data.split(",", 1)
            signature_bytes = base64.b64decode(encoded)
            with open(signature_filename, "wb") as sig_file:
                sig_file.write(signature_bytes)

        # Append new entry to CSV
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([first_name, last_name, id_number, consent, signature_filename])


        return redirect(url_for("index"))

    if not is_logged_in():
            return redirect(url_for("login.login_form"))

    return render_template("consent_form.html")


# Get list of the names from the consent.csv file
@consent_blueprint.route('/get_consent_names')
def get_consent_names():
    try:
        names = []
        with open(CSV_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = f"{row['first_name']} {row['last_name']}"
                names.append(full_name)
        return jsonify(names)
    except Exception as e:
        return jsonify([])
