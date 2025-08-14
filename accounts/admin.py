from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id","email", "full_name", "role", "distro_code", "distro_by", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "terms_agreed", "is_affiliate")
    search_fields = ("email", "full_name", "phone_number", "distro_code")
    ordering = ("-date_joined",)
    readonly_fields = ["id", "email", "date_joined", "distro_code"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "avatar", "phone_country_code", "phone_number")}),
        ("Role & Permissions", {"fields": ("role", "is_affiliate", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Referral Info", {"fields": ("distro_code", "distro_by")}),
        ("Security & OTP", {"fields": ("otp", "otp_expired", "reset_secret_key")}),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
        ("Terms", {"fields": ("terms_agreed",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role", "terms_agreed"),
        }),
    )
