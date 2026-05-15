from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Follow, Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    follower_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "display_name", "avatar_url", "bio", "country",
            "favorite_team", "points", "level",
            "follower_count", "following_count",
        ]

    def get_follower_count(self, obj: Profile) -> int:
        return Follow.objects.filter(followee=obj.user).count()

    def get_following_count(self, obj: Profile) -> int:
        return Follow.objects.filter(follower=obj.user).count()


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined", "profile"]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    display_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "display_name"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value.lower()

    def create(self, validated_data):
        display = validated_data.pop("display_name", "") or validated_data["username"]
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        # Profile is auto-created via signal; set display name.
        user.profile.display_name = display
        user.profile.save(update_fields=["display_name"])
        return user
