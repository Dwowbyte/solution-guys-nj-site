import os
import json
import secrets
from datetime import timedelta

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# -----------------------------
# SECURITY CONFIG
# -----------------------------
# Never hardcode a secret key. Pull it from the environment; generate a
# throwaway one for local dev so the app still runs, but this MUST be
# set as a real env var before deploying (see README notes at bottom).
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Defaults to True (secure cookies) since this is meant to run on HTTPS.
# Only set SESSION_COOKIE_SECURE=false if you're testing locally over plain http.
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"

# -----------------------------
# ADMIN CONFIG (this is the only login the app has now — for you, not customers)
# -----------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@solutionguysnj.com")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    # Dev-only fallback so the app boots locally without extra setup.
    # Set a real ADMIN_PASSWORD_HASH before this ever goes live.
    ADMIN_PASSWORD_HASH = generate_password_hash("change-this-admin-password")

REQUESTS_FILE = "requests.json"

# -----------------------------
# SERVICE CATALOG — matches the Solution Guys NJ site, no pricing
# -----------------------------
SERVICES = {
    "lawn_landscaping": {"label": "Lawn Care & Landscaping", "code": "LN-01"},
    "junk_removal": {"label": "Junk Removal", "code": "JR-02"},
    "commercial_cleaning": {"label": "Commercial Cleaning", "code": "JS-03A"},
    "residential_cleaning": {"label": "Residential Cleaning", "code": "JS-03B"},
    "post_construction_cleaning": {"label": "Post-Construction Clean-Up", "code": "JS-03C"},
}

PROPERTY_TYPES = ["Residential", "Commercial", "New construction"]

STATUS_OPTIONS = ["New", "Contacted", "Scheduled", "Completed", "Not interested"]


# -----------------------------
# HELPERS
# -----------------------------
def load_requests():
    if not os.path.exists(REQUESTS_FILE):
        return []
    with open(REQUESTS_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []


def save_requests(items):
    with open(REQUESTS_FILE, "w") as file:
        json.dump(items, file, indent=4)


def generate_id(items):
    if not items:
        return 1
    return max(item.get("id", 0) for item in items) + 1


def is_admin():
    return session.get("is_admin") is True


# -----------------------------
# PUBLIC SITE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html", services=SERVICES)


@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/service-request", methods=["POST"])
def service_request():
    """Handles the 'Get a Quote' form. No pricing, no payment —
    this just logs the request so the team can call the customer."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing request data"}), 400

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    address = data.get("address", "").strip()
    property_type = data.get("property_type", "").strip()
    service_keys = data.get("services", [])
    notes = data.get("notes", "").strip()

    if not name or not phone:
        return jsonify({"error": "Name and phone are required"}), 400

    if not isinstance(service_keys, list) or not service_keys:
        return jsonify({"error": "Select at least one service"}), 400

    valid_services = [key for key in service_keys if key in SERVICES]
    if not valid_services:
        return jsonify({"error": "No valid services selected"}), 400

    requests_list = load_requests()
    requests_list.append({
        "id": generate_id(requests_list),
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "property_type": property_type,
        "services": valid_services,
        "notes": notes,
        "status": "New",
        "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    })
    save_requests(requests_list)

    return jsonify({"message": "Request received", "redirect": "/thank-you"})


# -----------------------------
# ADMIN AUTH
# -----------------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing login data"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session.clear()
        session.permanent = True
        session["is_admin"] = True
        return jsonify({"message": "Login successful", "redirect": "/admin-dashboard"})

    return jsonify({"error": "Invalid email or password"}), 401


@app.route("/admin-logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# -----------------------------
# ADMIN DASHBOARD — where you see and manage incoming requests
# -----------------------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))

    requests_list = load_requests()
    requests_list.sort(key=lambda r: r.get("id", 0), reverse=True)

    return render_template(
        "admin_dashboard.html",
        requests=requests_list,
        services=SERVICES,
        status_options=STATUS_OPTIONS,
    )


@app.route("/admin/requests/<int:request_id>/status", methods=["POST"])
def update_request_status(request_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return jsonify({"error": "Missing status"}), 400

    new_status = data["status"]
    if new_status not in STATUS_OPTIONS:
        return jsonify({"error": "Invalid status"}), 400

    requests_list = load_requests()
    for item in requests_list:
        if item.get("id") == request_id:
            item["status"] = new_status
            save_requests(requests_list)
            return jsonify({"message": "Status updated"})

    return jsonify({"error": "Request not found"}), 404


@app.route("/admin/requests/<int:request_id>", methods=["DELETE"])
def delete_request(request_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    requests_list = load_requests()
    filtered = [r for r in requests_list if r.get("id") != request_id]

    if len(filtered) == len(requests_list):
        return jsonify({"error": "Request not found"}), 404

    save_requests(filtered)
    return jsonify({"message": "Request deleted"})


# -----------------------------
# JSON API (admin-only — customer data lives here)
# -----------------------------
@app.route("/api/requests", methods=["GET"])
def get_requests():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(load_requests())


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, port=int(os.environ.get("PORT", 5001)))
