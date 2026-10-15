from django.contrib.auth.models import User
from django.db import models


class PhoneCheck(models.Model):
    """The admin sets a code for a phone number; the user types the same code to verify."""
    phone = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=8, blank=True)
    code_set_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.code and not self.code_set_at:
            self.code_set_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} {self.phone}"


class Profile(models.Model):
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    LEVEL = [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("pro", "Pro")]
    STYLE = [("garba", "Garba"), ("dandiya", "Dandiya Raas"), ("dodhiyu", "Dodhiyu"),
             ("hudo", "Hudo"), ("any", "Any")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=50)
    age = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=1, choices=GENDER)
    looking_for = models.CharField("Looking for", max_length=1, choices=GENDER + [("A", "Anyone")], default="A")
    city = models.CharField(max_length=60)
    level = models.CharField(max_length=15, choices=LEVEL, default="beginner")
    style = models.CharField(max_length=10, choices=STYLE, default="any")
    bio = models.TextField(max_length=300, blank=True)
    photo = models.ImageField(upload_to="photos/", blank=True)
    allow_whatsapp = models.BooleanField("Allow people to chat with me on WhatsApp", default=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Interest(models.Model):
    STATUS = [("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received")
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("sender", "receiver")


class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports_made")
    reported = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports_got")
    reason = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reporter", "reported")
