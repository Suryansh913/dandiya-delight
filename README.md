# Dandiya Delight (Django)

Find your garba / dandiya partner. Quick login with WhatsApp number, profile cards,
interest requests, matches and one-tap WhatsApp chat.

## Setup
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser     # this is the owner/admin account
    python manage.py runserver

Open http://127.0.0.1:8000

> Upgrading from an older copy? Delete the old `db.sqlite3` first (the database schema changed).

## Login
Users enter their name and WhatsApp number and are logged in directly (no OTP / verification step).
If they don't have a profile yet, they are sent to create one.

## WhatsApp chat button
Every profile card has a green **WhatsApp** button that opens a chat with a ready-made message.
The number is never printed in the page HTML (the button goes through `/chat/<id>/`).
Users can turn this off in their profile ("Allow people to chat with me on WhatsApp").

## Other features
Filters (gender, city, level, style, age), interest requests, matches, report & auto-hide after 3 reports,
admin panel at `/admin/`.

## Production notes
Set `DEBUG=0`, a real `SECRET_KEY` and `ALLOWED_HOSTS`, and serve `media/` with nginx or object storage.
