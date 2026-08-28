# Solution Guys NJ — Website + Request Backend

## What's included
- `app.py` — Flask backend. Handles the public site, the "Get a Quote" form, and
  an admin dashboard to view/manage incoming requests. No pricing, no payment —
  every submission is just a lead for your team to call back.
- `templates/index.html` — the public site (hero, services, quote form).
- `templates/thank_you.html` — confirmation page after a request is submitted.
- `templates/admin_login.html` / `templates/admin_dashboard.html` — private
  dashboard where you see requests, update their status, or delete them.
- `static/logo.jpg` — your logo, served at `/static/logo.jpg`.

## Running it locally
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Set your admin credentials (don't skip this — without it the app falls
   back to an insecure dev password):
   ```
   export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   export ADMIN_EMAIL=you@yourdomain.com
   export ADMIN_PASSWORD_HASH=$(python3 -c "from werkzeug.security import generate_password_hash as g; print(g('yourrealpassword'))")
   ```
3. Run it:
   ```
   python3 app.py
   ```
4. Visit `http://127.0.0.1:5001/` for the site, and
   `http://127.0.0.1:5001/admin-login` to view submitted requests.

## How requests work
- A visitor fills out the "Get a Quote" form and picks one or more services —
  no price is shown or collected.
- The submission is saved to `requests.json` (created automatically) and shows
  up in the admin dashboard as status "New."
- From the dashboard you can mark a request Contacted / Scheduled / Completed /
  Not interested, or delete it once it's handled.

## Before this goes live
- Set real values for `FLASK_SECRET_KEY`, `ADMIN_EMAIL`, and
  `ADMIN_PASSWORD_HASH` as environment variables on your host — never commit
  them to code.
- `requests.json` holds customer contact info in plain text on disk. That's
  fine for a low-volume local setup, but for a real production deployment
  consider moving to a proper database and enabling HTTPS
  (`SESSION_COOKIE_SECURE = True` in `app.py`).
- The built-in server (`app.run(...)`) is for development only — deploy with
  a production WSGI server like gunicorn behind Nginx, or a host like
  Render/Railway/Fly.io.
