import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as vp
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class CreateUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(validators=[])
    email = serializers.EmailField(validators=[])
    password = serializers.CharField(validators=[], write_only=True)

    class Meta:
        model = User
        exclude = (
            "is_staff",
            "is_superuser",
            "is_active",
            "groups",
            "slug",
            "user_permissions",
            "last_login",
        )

    def validate_password(self, data):
        password = data

        if password and len(password) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        elif password and not re.search("[A-Z]", password):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )
        elif password and not re.search("[a-z]", password):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter."
            )
        elif password and not re.search("[0-9]", password):
            raise serializers.ValidationError(
                "Password must contain at least one digit."
            )
        elif password and not re.search(
            "[!@#$%^&*()_+}{\":?><|\\\/,./;'[\]]", password
        ):
            raise serializers.ValidationError(
                "Password must contain at least one special character."
            )
        if password:
            vp(password)
        return password


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = RefreshToken