# Dandiya Delight (Django)

Find your garba / dandiya partner. Phone verification through WhatsApp, profile cards,
interest requests, matches and one-tap WhatsApp chat.

## Setup
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py createsuperuser     # this is the owner/admin account
    python manage.py runserver

Open http://127.0.0.1:8000

> Upgrading from an older copy? Delete the old `db.sqlite3` first (the database schema changed).

## How phone verification works (no API needed)
1. A user enters their name and WhatsApp number, then waits on the verify page.
2. You log in at `/admin/login/` and open `/manage/` (Verify Panel). The pending number appears there.
3. Click **Send code via WhatsApp**. WhatsApp opens with the message ready; press Send.
4. The user types the same code, is verified, and creates their profile.

Codes are valid for 15 minutes with a maximum of 5 wrong attempts. `/manage/` is staff-only.

## WhatsApp chat button
Every profile card has a green **WhatsApp** button that opens a chat with a ready-made message.
The number is never printed in the page HTML (the button goes through `/chat/<id>/`).
Users can turn this off in their profile ("Allow people to chat with me on WhatsApp").

## Other features
Filters (gender, city, level, style, age), interest requests, matches, report & auto-hide after 3 reports,
admin panel at `/admin/`.

## Production notes
Set `DEBUG=0`, a real `SECRET_KEY` and `ALLOWED_HOSTS`, and serve `media/` with nginx or object storage.
