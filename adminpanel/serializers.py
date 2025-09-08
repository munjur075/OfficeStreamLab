from rest_framework import serializers
from accounts.models import User

class ManageUserSerializer(serializers.ModelSerializer):
    date_joined = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "date_joined",
        ]

    def get_date_joined(self, obj):
        return obj.date_joined.date().isoformat()  # gives YYYY-MM-DD
