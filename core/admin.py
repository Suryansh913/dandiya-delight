from django.contrib import admin
from .models import Interest, PhoneCheck, Profile, Report

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "city", "gender", "age", "is_active")
    list_filter = ("is_active", "gender", "level")
    search_fields = ("name", "user__username", "city")

admin.site.register(Interest)
admin.site.register(Report)
admin.site.register(PhoneCheck)
