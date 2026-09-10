import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# -----------------------------
# SECURITY CONFIG
# -----------------------------
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE", "true"
).lower() == "true"

# -----------------------------
# DATABASE CONFIG
# -----------------------------
# Render PostgreSQL provides DATABASE_URL. For local development only, the app
# falls back to a local SQLite file so it can still be tested easily.
database_url = os.environ.get("DATABASE_URL", "sqlite:///solution_guys.db")
# Some providers still return postgres://; SQLAlchemy expects postgresql://.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)

# -----------------------------
# ADMIN CONFIG
# -----------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@solutionguysnj.com")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    ADMIN_PASSWORD_HASH = generate_password_hash("change-this-admin-password")

# -----------------------------
# SERVICE CATALOG
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
# DATABASE MODEL
# -----------------------------
class ServiceRequest(db.Model):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(254), nullable=False, default="")
    address = db.Column(db.String(300), nullable=False, default="")
    property_type = db.Column(db.String(80), nullable=False, default="")
    services_json = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(40), nullable=False, default="New")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def services(self):
        try:
            value = json.loads(self.services_json)
            return value if isinstance(value, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    def to_dict(self):
        created = self.created_at
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "property_type": self.property_type,
            "services": self.services,
            "notes": self.notes,
            "status": self.status,
            "created_at": created.isoformat(timespec="seconds") if created else "",
        }


# Create tables automatically at app startup.
with app.app_context():
    db.create_all()


# -----------------------------
# HELPERS
# -----------------------------
def is_admin():
    return session.get("is_admin") is True


def request_to_view(item):
    """Return a plain dict so the existing Jinja template keeps working."""
    return item.to_dict()


# -----------------------------
# PUBLIC SITE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html", services=SERVICES)
SERVICE_PAGES = {
    "lawn-landscaping": {
        "page_title": "Lawn & Landscaping in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Lawn care, landscaping, edging, trimming and seasonal property maintenance in Burlington County and nearby South Jersey communities.",
        "heading": "Lawn & Landscaping Services in Burlington County, NJ",
        "intro": "Solution Guys NJ provides practical lawn care and landscaping for homeowners, property managers and commercial properties throughout Burlington County.",
        "service_name": "lawn and landscaping service",
        "service_area": "Burlington County, NJ",
        "service_items": [
            "Lawn mowing",
            "Edging",
            "Trimming",
            "Seasonal cleanup",
            "Property maintenance",
            "Landscape cleanup"
        ]
    },

    "gutter-cleaning": {
        "page_title": "Gutter Cleaning in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Professional gutter cleaning and downspout clearing in Burlington county, Willingboro Westhampton and nearby South jersey communities. Request a quote today.",
        "heading": "Gutter Cleaning in Burlington County, NJ",
        "intro": "Protect your home from clogged gutters, overflowing water and drainage problems with professional gutter cleaning from Solution Guys NJ. We remove leaves, debris and buildup, clear downspouts, and inspect your gutter system for proper water flow throughout Burlington County, NJ.",
        "service_name": "gutter cleaning",
        "service_area": "Burlington County, NJ",
        "service_items": [
    "Gutter cleaning and leaf debris removal",
    "Downspout cleaning and blockage clearing",
    "Gutter and roofline visual inspection",
    "Seasonal fall gutter cleaning",
    "Before-and-after gutter assessment",
    "Gutter guard consultation"
]
        ]
    },

    "junk-removal": {
        "page_title": "Junk Removal in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Junk removal for homes, garages, move-outs and property cleanouts in Burlington County and nearby South Jersey areas.",
        "heading": "Junk Removal in Burlington County, NJ",
        "intro": "Solution Guys NJ helps homeowners and property managers clear unwanted items from homes, garages and properties.",
        "service_name": "junk removal",
        "service_area": "Burlington County, NJ",
        "service_items": [
            "Garage cleanouts",
            "Household junk removal",
            "Move-out cleanouts",
            "Property cleanouts",
            "Furniture removal",
            "General debris removal"
        ]
    },

    "commercial-cleaning": {
        "page_title": "Commercial Cleaning in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Commercial and janitorial cleaning services for offices, businesses and managed properties in Burlington County, New Jersey.",
        "heading": "Commercial Cleaning Services in Burlington County, NJ",
        "intro": "Solution Guys NJ provides dependable commercial cleaning for businesses, offices, managed properties and recurring service accounts.",
        "service_name": "commercial cleaning",
        "service_area": "Burlington County, NJ",
        "service_items": [
            "Office cleaning",
            "Janitorial service",
            "Common-area cleaning",
            "Restroom cleaning",
            "Recurring service",
            "One-time commercial cleaning"
        ]
    },

    "post-construction-cleaning": {
        "page_title": "Post-Construction Cleaning in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Post-construction cleaning for contractors, property managers and newly renovated spaces throughout Burlington County and South Jersey.",
        "heading": "Post-Construction Cleaning in Burlington County, NJ",
        "intro": "Solution Guys NJ helps prepare newly built and renovated properties for move-in, turnover or final presentation.",
        "service_name": "post-construction cleaning",
        "service_area": "Burlington County, NJ",
        "service_items": [
            "Construction dust removal",
            "Floor cleaning",
            "Kitchen cleaning",
            "Bathroom cleaning",
            "Surface wipe-downs",
            "Final turnover cleaning"
        ]
    },

    "fall-cleanup": {
        "page_title": "Fall Cleanup in Burlington County NJ | Solution Guys NJ",
        "meta_description": "Fall yard cleanup, leaf removal and seasonal property cleanup in Burlington County, Willingboro, Westampton and nearby communities.",
        "heading": "Fall Cleanup Services in Burlington County, NJ",
        "intro": "Prepare your property for colder weather with seasonal cleanup from Solution Guys NJ.",
        "service_name": "fall cleanup",
        "service_area": "Burlington County, NJ",
        "service_items": [
            "Leaf removal",
            "Yard debris cleanup",
            "Final mowing",
            "Edging",
            "Garden-bed cleanup",
            "Seasonal property preparation"
        ]
    }
}


@app.route("/<service_slug>")
def service_page(service_slug):
    page = SERVICE_PAGES.get(service_slug)

    if page is None:
        return "Page not found", 404

    return render_template(
        "service.html",
        canonical_url=f"https://solutionguysnj.com/{service_slug}",
        **page
    )

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/service-request", methods=["POST"])
def service_request():
    """Receive a quote request and store it safely in the database."""
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

    item = ServiceRequest(
        name=name,
        phone=phone,
        email=email,
        address=address,
        property_type=property_type,
        services_json=json.dumps(valid_services),
        notes=notes,
        status="New",
    )
    db.session.add(item)
    db.session.commit()

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
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("admin_login"))

    rows = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    requests_list = [request_to_view(row) for row in rows]

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

    item = db.session.get(ServiceRequest, request_id)
    if not item:
        return jsonify({"error": "Request not found"}), 404

    item.status = new_status
    db.session.commit()
    return jsonify({"message": "Status updated"})


@app.route("/admin/requests/<int:request_id>", methods=["DELETE"])
def delete_request(request_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    item = db.session.get(ServiceRequest, request_id)
    if not item:
        return jsonify({"error": "Request not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Request deleted"})


# -----------------------------
# JSON API (ADMIN ONLY)
# -----------------------------
@app.route("/api/requests", methods=["GET"])
def get_requests():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403

    rows = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    return jsonify([row.to_dict() for row in rows])


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# -----------------------------
# RUN APP
# -----------------------------
@app.route("/sitemap.xml")
def sitemap():
    pages = [
        "https://solutionguysnj.com/",
        "https://solutionguysnj.com/lawn-landscaping",
    "https://solutionguysnj.com/gutter-cleaning",
    "https://solutionguysnj.com/junk-removal",
    "https://solutionguysnj.com/commercial-cleaning",
    "https://solutionguysnj.com/post-construction-cleaning",
    "https://solutionguysnj.com/fall-cleanup",
    ]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in pages:
        xml.append("<url>")
        xml.append(f"<loc>{page}</loc>")
        xml.append("</url>")

    xml.append("</urlset>")

    return "\n".join(xml), 200, {"Content-Type": "application/xml"}
@app.route("/robots.txt")
def robots():
    content = """User-agent: *
Allow: /

Sitemap: https://solutionguysnj.com/sitemap.xml
"""
    return content, 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, port=int(os.environ.get("PORT", 5001)))
