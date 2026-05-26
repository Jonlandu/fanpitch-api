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
    is_me = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined", "profile",
                  "is_me", "is_following"]
        read_only_fields = ["id", "date_joined", "is_me", "is_following"]

    def _request_user(self):
        req = self.context.get("request")
        return req.user if req and req.user.is_authenticated else None

    def get_is_me(self, obj) -> bool:
        me = self._request_user()
        return bool(me and me.id == obj.id)

    def get_is_following(self, obj) -> bool:
        me = self._request_user()
        if not me or me.id == obj.id:
            return False
        return Follow.objects.filter(follower=me, followee=obj).exists()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    display_name = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(
        required=False, allow_blank=True, max_length=80
    )

    class Meta:
        model = User
        fields = ["username", "email", "password", "display_name", "country"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value.lower()

    def create(self, validated_data):
        display = validated_data.pop("display_name", "") or validated_data["username"]
        country = validated_data.pop("country", "") or ""
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        # Profile is auto-created via signal; set display name + country.
        user.profile.display_name = display
        if country:
            user.profile.country = country
        user.profile.save(update_fields=["display_name", "country"])
        return user
