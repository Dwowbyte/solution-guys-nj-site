# Solution Guys NJ — Website + PostgreSQL Request Backend

## What's included
- `app.py` — Flask backend for the public site, quote form, admin login, and admin dashboard.
- PostgreSQL-backed lead storage using SQLAlchemy. Customer requests no longer depend on a local `requests.json` file.
- `templates/index.html` — public site.
- `templates/thank_you.html` — confirmation page.
- `templates/admin_login.html` / `templates/admin_dashboard.html` — private admin area.
- `static/logo.jpg` — website logo.

## Production database
Set the `DATABASE_URL` environment variable to your PostgreSQL connection string. On Render, create a PostgreSQL database and use its internal database URL for the web service.

The application creates its `service_requests` table automatically when it starts.

## Required production environment variables
- `DATABASE_URL`
- `FLASK_SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD_HASH`
- `FLASK_DEBUG=false`
- `SESSION_COOKIE_SECURE=true`

Generate an admin password hash locally with:

```bash
python -c "from werkzeug.security import generate_password_hash as g; print(g('YOUR-ADMIN-PASSWORD'))"
```

Generate a Flask secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Local testing
If `DATABASE_URL` is not set, the app falls back to a local SQLite database named `solution_guys.db`. This is only for convenient local testing.

```bash
pip install -r requirements.txt
python app.py
```

Then visit:
- Site: `http://127.0.0.1:5001/`
- Admin: `http://127.0.0.1:5001/admin-login`
- Health check: `http://127.0.0.1:5001/health`

## Render deployment
Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Connect the Render web service to a Render PostgreSQL database and set `DATABASE_URL` before accepting real customer submissions.
