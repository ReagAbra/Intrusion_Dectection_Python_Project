import os
from flask import render_template, request, Blueprint, redirect, url_for
import hashlib


login_blueprint = Blueprint("login", __name__)


@login_blueprint.route("/login", methods=["GET", "POST"])
def login_form():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Get admin credentials
        valid_username = os.getenv("APP_USERNAME", "admin")
        valid_password_hash = os.getenv("APP_PASSWORD_HASH", 
            hashlib.sha256("123".encode()).hexdigest())  # Default hash of "123"
        

        # Hash the entered password
        entered_password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Replace with your real authentication
        if username == valid_username and entered_password_hash == valid_password_hash:
            # Create a flag to indicate login success
            os.makedirs("temp_flags", exist_ok=True)
            with open("temp_flags/.logged_in", "w") as f:
                f.write("true")

            # Open consent form
            return redirect(url_for("consent.consent_form"))
            
        return render_template("login_form.html", error="Invalid credentials")
        
    return render_template("login_form.html")
