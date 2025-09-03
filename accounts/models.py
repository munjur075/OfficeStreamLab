from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import shortuuid
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from django.core.exceptions import ValidationError

# ============================
# Custom User Manager
# ============================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        
        full_name = extra_fields.get("full_name")

        if not full_name:
            raise ValueError(_("The Full Name field must be set"))
        
        terms_agreed = extra_fields.get("terms_agreed")
        if not terms_agreed:
            raise ValueError(_("You must agree to the Terms of Service."))
        
        # Handle referral code
        distro_code = extra_fields.pop("distro_code", None)
        distro_by = None
        if distro_code:
            try:
                distro_by = self.model.objects.get(distro_code=distro_code)
            except self.model.DoesNotExist:
               raise ValueError("Invalid referral code")

        user = self.model(email=email, **extra_fields)
        if distro_by:
            user.distro_by = distro_by

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("terms_agreed", True)

        if extra_fields.get("role") != UserRole.ADMIN:
            raise ValueError("Superuser must have role='admin'.")
        return self.create_user(email, password, **extra_fields)

# ============================
# User Roles
# ============================
class UserRole(models.TextChoices):
    ADMIN = 'admin', _('Admin')
    USER = 'user', _('User')

def generate_short_uuid():
    return shortuuid.uuid()[:12]

# ============================
# Custom User Model
# ============================
class User(AbstractBaseUser, PermissionsMixin):
    id = models.CharField(primary_key=True, max_length=12, default=generate_short_uuid, editable=False, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to="profile/", blank=True, null=True)
   
    # Phone number fields
    phone_country_code = models.CharField(max_length=5, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    otp = models.CharField(max_length=6, blank=True)
    otp_expired = models.DateTimeField(null=True, blank=True)
    reset_secret_key = models.UUIDField(blank=True, null=True)
    is_subscribe= models.BooleanField(default=False)
    is_platform = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    terms_agreed = models.BooleanField(default=False)

    distro_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals',
        help_text='User who referred this user',
    )

    distro_code = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        blank=True,
        null=True,
        help_text="Unique referral code for the user"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email

    def clean(self):
        if self.phone_country_code and self.phone_number:
            cc = self.phone_country_code.lstrip("+").strip()
            pn = self.phone_number.strip()
            try:
                parsed = phonenumbers.parse(f"+{cc}{pn}", None)
            except NumberParseException:
                raise ValidationError({"phone_number": "Invalid phone number format."})

            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError({"phone_number": "Invalid phone number for the given country code."})

    def save(self, *args, **kwargs):
        if not self.distro_code:
            self.distro_code = self.generate_unique_distro_code()
        super().save(*args, **kwargs)

    def generate_unique_distro_code(self):
        while True:
            code = shortuuid.ShortUUID().random(length=8).upper()
            if not User.objects.filter(distro_code=code).exists():
                return code
