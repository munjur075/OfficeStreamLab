import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from phonenumbers.data import _COUNTRY_CODE_TO_REGION_CODE
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    distro_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "avatar",
            "phone_country_code", "phone_number",
            "role", "is_affiliate", "date_joined",
            "distro_by",
        ]
        read_only_fields = ["id", "email", "role", "date_joined", "distro_by"]

    def validate(self, data):
        country_code = data.get("phone_country_code") or getattr(self.instance, "phone_country_code", None)
        phone_number = data.get("phone_number") or getattr(self.instance, "phone_number", None)

        if country_code and phone_number:
            # Normalize country code (strip + and spaces)
            cc = country_code.lstrip("+").strip()

            if not cc.isdigit():
                raise serializers.ValidationError({"phone_country_code": "Country code must be numeric."})

            # Check if country code exists in official list
            valid_country_codes = set(_COUNTRY_CODE_TO_REGION_CODE.keys())
            cc_int = int(cc)
            if cc_int not in valid_country_codes:
                raise serializers.ValidationError({"phone_country_code": "Invalid country calling code."})

            # Validate full phone number
            pn = phone_number.strip()
            e164_number = f"+{cc}{pn}"

            try:
                parsed = phonenumbers.parse(e164_number, None)
            except NumberParseException:
                raise serializers.ValidationError({"phone_number": "Invalid phone number format."})

            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError({"phone_number": "Invalid phone number for the given country code."})

            # Normalize phone number fields for storage:
            data["phone_country_code"] = str(parsed.country_code)  # normalized country code as string (no plus)
            # Format national number removing spaces and dashes for consistent storage
            normalized_national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            normalized_national = normalized_national.replace(" ", "").replace("-", "")
            data["phone_number"] = normalized_national

        return data
