from collections import Counter

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import MediaPost, Status


class MediaPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaPost
        fields = ["id", "s3_key", "media_type", "cdn_url",
                  "width", "height", "duration_ms", "ai_caption", "created_at"]
        read_only_fields = ["created_at"]


class StatusSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    media = MediaPostSerializer(read_only=True)
    media_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=MediaPost.objects.all(),
        source="media", required=False, allow_null=True,
    )
    reactions_breakdown = serializers.SerializerMethodField()
    my_reactions = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = ["id", "author", "body_text", "media", "media_id",
                  "team", "expires_at",
                  "impressions_count", "reactions_count", "comments_count",
                  "reactions_breakdown", "my_reactions",
                  "created_at"]
        read_only_fields = ["expires_at", "created_at",
                            "impressions_count", "reactions_count",
                            "comments_count"]

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

    def get_reactions_breakdown(self, obj: Status) -> dict[str, int]:
        from apps.interactions.models import Reaction
        rows = (Reaction.objects
                .filter(target_type="STATUS", target_id=obj.id)
                .values_list("emoji", flat=True))
        return dict(Counter(rows))

    def get_my_reactions(self, obj: Status) -> list[str]:
        from apps.interactions.models import Reaction
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []
        return list(Reaction.objects
                    .filter(target_type="STATUS", target_id=obj.id,
                            user=request.user)
                    .values_list("emoji", flat=True))


class ImpressionBatchSerializer(serializers.Serializer):
    """Mobile clients batch up to 50 impressions per request."""
    status_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1, max_length=50,
    )
    dwell_ms = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        required=False, default=list,
    )

    def validate(self, attrs):
        dwell = attrs.get("dwell_ms") or []
        if dwell and len(dwell) != len(attrs["status_ids"]):
            raise serializers.ValidationError(
                "dwell_ms length must match status_ids length")
        return attrs
