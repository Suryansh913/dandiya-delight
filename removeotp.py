#!/usr/bin/env python3
"""
remove_otp.py  --  Garba Partner project se OTP / WhatsApp-verify system hatata hai.

Kaise chalana hai:
    1. Is file ko apne project ke root mein rakho (jahan manage.py hai)
    2. python remove_otp.py
       (ya kahin aur se:  python remove_otp.py /path/to/garba_partner)
    3. python manage.py migrate

Default mein SIRF OTP hata hai. Name, phone number, profile, WhatsApp chat sab waisa hi rehta hai.
Home/login ke text (jaise "verified") nahi badalte.

Optional flags:
    --texts          login/home/README ke "verification" wale text bhi badal do
    --revert-texts   agar pehle wale version se text badal chuke ho, to wapas original kar do

Ye script:
  - Har badli hui file ka backup  .otp_backup/  folder mein rakhti hai
  - Do baar chalane par bhi safe hai (jo ho chuka, use skip kar deti hai)
  - Django template tags ko touch nahi karti
"""
import sys
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------------ setup
POS = [a for a in sys.argv[1:] if not a.startswith("--")]
DO_TEXTS = "--texts" in sys.argv
REVERT_TEXTS = "--revert-texts" in sys.argv
arg = Path(POS[0]).resolve() if POS else Path.cwd()
candidates = [arg, arg / "garba_partner"]
ROOT = next((c for c in candidates if (c / "manage.py").exists()), None)
if ROOT is None:
    sys.exit("ERROR: manage.py nahi mila. Script ko project root mein rakho ya path do:\n"
             "       python remove_otp.py /path/to/garba_partner")

CORE = ROOT / "core"
TPL = CORE / "templates" / "core"
BACKUP = ROOT / ".otp_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")

changed, skipped, warnings = [], [], []


def backup(path: Path):
    dest = BACKUP / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def edit(path: Path, steps):
    """steps = list of (label, old, new). Har step sirf tab chalta hai jab old text mile."""
    if not path.exists():
        warnings.append(f"{rel(path)} nahi mili - skip")
        return
    text = path.read_text(encoding="utf-8")
    original = text
    for label, old, new in steps:
        if old in text:
            text = text.replace(old, new, 1)
        else:
            skipped.append(f"{rel(path)}: {label} (pehle se ho chuka ya mila nahi)")
    if text != original:
        backup(path)
        path.write_text(text, encoding="utf-8")
        changed.append(rel(path))


def cut(text, start_marker, end_marker, replacement=""):
    """start_marker se end_marker tak ka hissa replacement se badal do."""
    a = text.find(start_marker)
    if a == -1:
        return text, False
    b = text.find(end_marker, a) if end_marker else len(text)
    if b == -1:
        return text, False
    return text[:a] + replacement + text[b:], True


# ------------------------------------------------------------------ views.py
NEW_LOGIN = '''def login_view(request):
    """Name + phone => logged in directly (no OTP / verification step)."""
    if request.user.is_authenticated:
        return redirect("browse")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:50]
        phone = normalize_phone(request.POST.get("phone"))
        if not name or not phone:
            messages.error(request, "Enter a valid name and phone number (10 digits, or with +country code).")
        else:
            user, created = User.objects.get_or_create(username=phone, defaults={"first_name": name})
            if created:
                user.set_unusable_password()
                user.save()
            login(request, user)
            if not Profile.objects.filter(user=user).exists():
                return redirect("profile_edit")
            return redirect("browse")
    return render(request, "core/login.html")


'''

p = CORE / "views.py"
if p.exists():
    t = p.read_text(encoding="utf-8")
    o = t
    # login_view + verify_view + manage + send_code  ->  naya login_view
    if "def verify_view" in t or "PhoneCheck" in t:
        t, ok = cut(t, "def login_view(request):", "@require_POST\ndef logout_view", NEW_LOGIN)
        if not ok:
            warnings.append("views.py: login_view..logout_view block nahi mila, manually dekho")
    for old, new in [
        ("import hmac\nfrom datetime import timedelta\nfrom functools import wraps",
         "from functools import wraps"),
        ("from django.contrib.auth.decorators import login_required, user_passes_test",
         "from django.contrib.auth.decorators import login_required"),
        ("from django.utils import timezone\n", ""),
        ("from .models import Interest, PhoneCheck, Profile, Report",
         "from .models import Interest, Profile, Report"),
        ("from .utils import make_code, normalize_phone",
         "from .utils import normalize_phone"),
        ('staff_only = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="/admin/login/")\n\n\n',
         "\n"),
    ]:
        t = t.replace(old, new, 1)
    if t != o:
        backup(p)
        p.write_text(t, encoding="utf-8")
        changed.append(rel(p))
    else:
        skipped.append("views.py: pehle se clean hai")
else:
    warnings.append("core/views.py nahi mili")

# ------------------------------------------------------------------ urls.py
edit(CORE / "urls.py", [
    ("verify route", '    path("verify/", views.verify_view, name="verify"),\n', ""),
    ("manage route", '    path("manage/", views.manage, name="manage"),\n', ""),
    ("send_code route", '    path("manage/send/<int:pk>/", views.send_code, name="send_code"),\n', ""),
])

# ------------------------------------------------------------------ models.py
p = CORE / "models.py"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "class PhoneCheck" in t:
        t, ok = cut(t, "class PhoneCheck", "class Profile")
        if ok:
            backup(p)
            p.write_text(t, encoding="utf-8")
            changed.append(rel(p))
        else:
            warnings.append("models.py: PhoneCheck class hatane mein dikkat, manually dekho")
    else:
        skipped.append("models.py: PhoneCheck pehle se nahi hai")

# ------------------------------------------------------------------ admin.py
edit(CORE / "admin.py", [
    ("import", "from .models import Interest, PhoneCheck, Profile, Report",
     "from .models import Interest, Profile, Report"),
    ("register", "admin.site.register(PhoneCheck)\n", ""),
])

# ------------------------------------------------------------------ utils.py
p = CORE / "utils.py"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "def make_code" in t:
        t = t.replace("import re\nimport secrets\n", "import re\n", 1)
        t = t[:t.index("def make_code")].rstrip() + "\n"
        backup(p)
        p.write_text(t, encoding="utf-8")
        changed.append(rel(p))
    else:
        skipped.append("utils.py: make_code pehle se nahi hai")

# ------------------------------------------------------------------ migration
mig_dir = CORE / "migrations"
mig_dir.mkdir(exist_ok=True)
existing = sorted(f for f in mig_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
already = any("DeleteModel" in f.read_text(encoding="utf-8") and "PhoneCheck" in f.read_text(encoding="utf-8")
              for f in existing)
if already:
    skipped.append("migration: PhoneCheck delete migration pehle se hai")
elif not existing:
    warnings.append("core/migrations mein koi migration nahi mila - pehle `python manage.py makemigrations core` chalao")
else:
    last = existing[-1]
    num = int(last.name[:4]) + 1
    new_mig = mig_dir / f"{num:04d}_delete_phonecheck.py"
    new_mig.write_text(
        "from django.db import migrations\n\n\n"
        "class Migration(migrations.Migration):\n\n"
        "    dependencies = [\n"
        f'        ("core", "{last.stem}"),\n'
        "    ]\n\n"
        "    operations = [\n"
        '        migrations.DeleteModel(name="PhoneCheck"),\n'
        "    ]\n",
        encoding="utf-8",
    )
    changed.append(rel(new_mig) + "  (new)")

# ------------------------------------------------------------------ templates
for name in ("verify.html", "manage.html"):
    f = TPL / name
    if f.exists():
        backup(f)
        f.unlink()
        changed.append(rel(f) + "  (deleted)")
    else:
        skipped.append(f"{name} pehle se nahi hai")

# Ye jaruri hai: "Verify Panel" link 'manage' URL use karta tha, URL hata to ye error deta
edit(TPL / "base.html", [
    ("Verify Panel link",
     '''    {% if user.is_staff %}<a href="{% url 'manage' %}"><svg class="ic"><use href="#i-shield"/></svg><span class="lbl">Verify Panel</span></a>{% endif %}\n''',
     ""),
])

# ------------------------------------------------------------------ optional text changes
TEXT_EDITS = {
    TPL / "login.html": [
        ("tagline", "<p>Verify your number and meet your garba partner.</p>",
         "<p>Join in seconds and meet your garba partner.</p>"),
        ("side point", '<li><svg class="ic"><use href="#i-shield"/></svg>Verified with WhatsApp</li>',
         '<li><svg class="ic"><use href="#i-shield"/></svg>Quick &amp; simple sign up</li>'),
        ("button", "Request verification code <svg", "Continue <svg"),
    ],
    TPL / "home.html": [
        ("lead", "Verified profiles, filters by city", "Real profiles, filters by city"),
        ("badge", "WhatsApp<br>verified", "WhatsApp<br>chat"),
        ("feature",
         "<h3>WhatsApp verification</h3><p>Every number is verified, so you meet real people instead of fake profiles.</p>",
         "<h3>Simple sign up</h3><p>Just your name and WhatsApp number &mdash; no codes, no waiting.</p>"),
        ("step",
         "<h3>Verify your number</h3><p>Enter your name and WhatsApp number, then confirm with a code.</p>",
         "<h3>Join with your number</h3><p>Enter your name and WhatsApp number and you're in.</p>"),
    ],
    ROOT / "README.md": [
        ("tagline", "Phone verification through WhatsApp, profile cards", "Quick login with WhatsApp number, profile cards"),
    ],
}

if DO_TEXTS or REVERT_TEXTS:
    for path, steps in TEXT_EDITS.items():
        if REVERT_TEXTS:
            steps = [(l, new, old) for (l, old, new) in steps]
        edit(path, steps)
    if DO_TEXTS:
        p = ROOT / "README.md"
        if p.exists():
            t = p.read_text(encoding="utf-8")
            t2, ok = cut(t, "## How phone verification works", "## WhatsApp chat button",
                         "## Login\nUsers enter their name and WhatsApp number and are logged in directly "
                         "(no OTP / verification step).\nIf they don't have a profile yet, they are sent to create one.\n\n")
            if ok and t2 != t:
                backup(p); p.write_text(t2, encoding="utf-8")
                if rel(p) not in changed:
                    changed.append(rel(p))

# ------------------------------------------------------------------ report
print(f"\nProject: {ROOT}\n")
print("BADLA GAYA:")
for c in changed:
    print("  +", c)
if not changed:
    print("  (kuch nahi - shayad pehle hi ho chuka hai)")
if skipped:
    print("\nSKIP (koi dikkat nahi):")
    for s in skipped:
        print("  -", s)
if warnings:
    print("\nWARNING:")
    for w in warnings:
        print("  !", w)
if changed:
    print(f"\nBackup yahan hai: {BACKUP}")
print("\nAb ye chalao:\n  python manage.py migrate\n  python manage.py runserver\n")