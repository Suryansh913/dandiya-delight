from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm
from .models import Interest, Profile, Report
from .utils import normalize_phone


def needs_profile(view):
    @wraps(view)
    @login_required
    def wrapper(request, *a, **kw):
        if not Profile.objects.filter(user=request.user).exists():
            messages.info(request, "Please create your profile first.")
            return redirect("profile_edit")
        return view(request, *a, **kw)
    return wrapper


def home(request):
    if request.user.is_authenticated:
        return redirect("browse")
    return render(request, "core/home.html")


def login_view(request):
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


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def profile_edit(request):
    profile = Profile.objects.filter(user=request.user).first()
    initial = {"name": request.user.first_name} if not profile else None
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile, initial=initial)
    if request.method == "POST" and form.is_valid():
        p = form.save(commit=False)
        p.user = request.user
        p.save()
        messages.success(request, "Profile saved!")
        return redirect("browse")
    return render(request, "core/profile_form.html", {"form": form})


@needs_profile
def browse(request):
    me = request.user.profile
    qs = Profile.objects.filter(is_active=True).exclude(user=request.user)
    g = request.GET.get("gender", me.looking_for if "gender" not in request.GET else "")
    if g in ("M", "F", "O"):
        qs = qs.filter(gender=g)
    city = request.GET.get("city", "").strip()
    if city:
        qs = qs.filter(city__icontains=city)
    for key in ("level", "style"):
        v = request.GET.get(key)
        if v:
            qs = qs.filter(**{key: v})
    if request.GET.get("age_min", "").isdigit():
        qs = qs.filter(age__gte=int(request.GET["age_min"]))
    if request.GET.get("age_max", "").isdigit():
        qs = qs.filter(age__lte=int(request.GET["age_max"]))
    profiles = list(qs.order_by("-created")[:60])
    status = {i.receiver_id: i.status for i in Interest.objects.filter(sender=request.user)}
    for p in profiles:
        p.istatus = status.get(p.user_id)
    return render(request, "core/browse.html", {
        "profiles": profiles, "g": g, "city": city, "GENDER": Profile.GENDER,
        "LEVEL": Profile.LEVEL, "STYLE": Profile.STYLE, "q": request.GET})


@needs_profile
def profile_detail(request, user_id):
    p = get_object_or_404(Profile, user_id=user_id, is_active=True)
    istatus = Interest.objects.filter(sender=request.user, receiver_id=user_id).values_list("status", flat=True).first()
    return render(request, "core/profile_detail.html", {"p": p, "istatus": istatus})


@needs_profile
@require_POST
def send_interest(request, user_id):
    other = get_object_or_404(User, pk=user_id, profile__is_active=True)
    if other == request.user:
        return redirect("browse")
    reverse = Interest.objects.filter(sender=other, receiver=request.user, status="pending").first()
    if reverse:
        reverse.status = "accepted"
        reverse.save()
        messages.success(request, "It's a match! Check your Matches page.")
    else:
        _, created = Interest.objects.get_or_create(sender=request.user, receiver=other)
        messages.success(request, "Interest sent!" if created else "You've already sent interest.")
    return redirect(request.POST.get("next") or "browse")


@needs_profile
@require_POST
def respond(request, pk, action):
    i = get_object_or_404(Interest, pk=pk, receiver=request.user, status="pending")
    if action in ("accept", "decline"):
        i.status = "accepted" if action == "accept" else "declined"
        i.save()
        messages.success(request, "It's a match!" if action == "accept" else "Declined.")
    return redirect("inbox")


@needs_profile
def inbox(request):
    me = request.user
    received = Interest.objects.filter(receiver=me, status="pending").select_related("sender__profile")
    sent = Interest.objects.filter(sender=me, status="pending").select_related("receiver__profile")
    matches = []
    for i in Interest.objects.filter(Q(sender=me) | Q(receiver=me), status="accepted").select_related(
            "sender__profile", "receiver__profile"):
        other = i.receiver if i.sender == me else i.sender
        matches.append({"profile": other.profile, "phone": other.username,
                        "wa": "https://wa.me/" + other.username.lstrip("+")})
    return render(request, "core/inbox.html", {"received": received, "sent": sent, "matches": matches})


@needs_profile
def chat(request, user_id):
    """Open a WhatsApp chat with the user (their number is never shown in the page HTML)."""
    p = get_object_or_404(Profile, user_id=user_id, is_active=True, allow_whatsapp=True)
    if p.user_id == request.user.id:
        return redirect("browse")
    text = (f"Hi {p.name}! I'm {request.user.profile.name}. I saw your profile on Dandiya Delight "
            "- would you like to be garba/dandiya partners? 🪔")
    return redirect(f"https://wa.me/{p.user.username.lstrip('+')}?text={quote(text)}")


@needs_profile
@require_POST
def report(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    if other != request.user:
        Report.objects.get_or_create(reporter=request.user, reported=other,
                                     defaults={"reason": request.POST.get("reason", "")[:200]})
        if Report.objects.filter(reported=other).count() >= 3:
            Profile.objects.filter(user=other).update(is_active=False)
        messages.success(request, "Report submitted. We'll review it.")
    return redirect("browse")
