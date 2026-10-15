#!/usr/bin/env python3
"""
add_password.py  --  Login par password lagata hai (phone + password se login).

PEHLE remove_otp.py chala chuke ho, tabhi ye chalao.

Kaise chalana hai:
    1. Is file ko project root mein rakho (jahan manage.py hai)
    2. python add_password.py
       (ya:  python add_password.py /path/to/garba_partner)
    3. python manage.py runserver      (migration ki zaroorat nahi)

Login kaise kaam karega:
  - Naya number     -> name + password daalo, account ban jaata hai (password hashed save hota hai)
  - Purana user     -> phone + password daalo, login ho jaata hai
  - Purane account jinka password kabhi set nahi hua tha -> pehli baar jo password daaloge wahi set ho jayega
  - Password bhool gaye -> /admin/ se password reset kar sakte ho

Backup  .pw_backup/  mein jaata hai. Do baar chalane par bhi safe hai.
"""
import sys
from datetime import datetime
from pathlib import Path

POS = [a for a in sys.argv[1:] if not a.startswith("--")]
arg = Path(POS[0]).resolve() if POS else Path.cwd()
ROOT = next((c for c in (arg, arg / "garba_partner") if (c / "manage.py").exists()), None)
if ROOT is None:
    sys.exit("ERROR: manage.py nahi mila. Script ko project root mein rakho ya path do:\n"
             "       python add_password.py /path/to/garba_partner")

CORE = ROOT / "core"
TPL = CORE / "templates" / "core"
BACKUP = ROOT / ".pw_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
changed, skipped, warnings = [], [], []


def backup(path):
    dest = BACKUP / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(path.read_bytes())


def rel(path):
    return str(path.relative_to(ROOT))


NEW_LOGIN = '''def login_view(request):
    """Phone + password. A new number creates the account with the chosen password."""
    if request.user.is_authenticated:
        return redirect("browse")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:50]
        phone = normalize_phone(request.POST.get("phone"))
        password = request.POST.get("password", "")
        user = User.objects.filter(username=phone).first() if phone else None
        if not phone:
            messages.error(request, "Enter a valid phone number (10 digits, or with +country code).")
        elif user is not None and user.has_usable_password():
            # existing account -> check the password
            auth_user = authenticate(request, username=phone, password=password)
            if auth_user is None:
                messages.error(request, "Incorrect phone number or password.")
            else:
                login(request, auth_user)
                if not Profile.objects.filter(user=auth_user).exists():
                    return redirect("profile_edit")
                return redirect("browse")
        elif len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif user is None and not name:
            messages.error(request, "New number? Please enter your name too.")
        else:
            if user is None:
                user = User.objects.create_user(username=phone, password=password, first_name=name)
            else:
                # old account that never had a password: the first password entered is set
                user.set_password(password)
                user.save()
            login(request, user)
            if not Profile.objects.filter(user=user).exists():
                return redirect("profile_edit")
            return redirect("browse")
    return render(request, "core/login.html")


'''

# ------------------------------------------------------------------ views.py
p = CORE / "views.py"
if not p.exists():
    sys.exit("ERROR: core/views.py nahi mili")
t = p.read_text(encoding="utf-8")
if "def verify_view" in t or "PhoneCheck" in t:
    sys.exit("ERROR: OTP abhi hata nahi hai. Pehle `python remove_otp.py` chalao, phir ye script.")
if 'request.POST.get("password"' in t:
    skipped.append("views.py: password login pehle se laga hai")
else:
    a = t.find("def login_view(request):")
    b = t.find("@require_POST\ndef logout_view")
    if a == -1 or b == -1:
        warnings.append("views.py: login_view / logout_view nahi mila, manually dekho")
    else:
        t = t[:a] + NEW_LOGIN + t[b:]
        old_imp = "from django.contrib.auth import login, logout"
        if old_imp in t:
            t = t.replace(old_imp, "from django.contrib.auth import authenticate, login, logout", 1)
        elif "authenticate" not in t.split("def ")[0]:
            warnings.append("views.py: `authenticate` import manually add karo: "
                            "from django.contrib.auth import authenticate")
        backup(p)
        p.write_text(t, encoding="utf-8")
        changed.append(rel(p))

# ------------------------------------------------------------------ login.html
p = TPL / "login.html"
if not p.exists():
    warnings.append("core/templates/core/login.html nahi mili")
else:
    t = p.read_text(encoding="utf-8")
    o = t
    if 'name="password"' in t:
        skipped.append("login.html: password field pehle se hai")
    else:
        old_name = '<label>Your name</label><input name="name" required maxlength="50" placeholder="e.g. Riya">'
        new_name = ('<label>Your name <span class="muted">(only for new users)</span></label>'
                    '<input name="name" maxlength="50" placeholder="e.g. Riya">')
        phone_line = ('<label>WhatsApp number</label><input name="phone" required inputmode="tel" '
                      'placeholder="9876543210 or +919876543210">')
        pw_line = ('\n      <label>Password</label><input name="password" type="password" required minlength="6" '
                   'autocomplete="current-password" placeholder="At least 6 characters">'
                   '\n      <p class="muted" style="font-size:.82rem;margin:0 0 12px">New here? Enter your name and choose a '
                   'password. Already joined? Just number + password.</p>')
        if old_name in t:
            t = t.replace(old_name, new_name, 1)
        else:
            warnings.append("login.html: name field ka original line nahi mila (name ko optional manually karo)")
        if phone_line in t:
            t = t.replace(phone_line, phone_line + pw_line, 1)
        else:
            warnings.append("login.html: phone field nahi mila, password field manually add karo")
        for old_btn in ("Request verification code <svg", "Continue <svg"):
            if old_btn in t:
                t = t.replace(old_btn, "Login / Sign up <svg", 1)
                break
        if t != o:
            backup(p)
            p.write_text(t, encoding="utf-8")
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
print("\nAb chalao:\n  python manage.py runserver\n")