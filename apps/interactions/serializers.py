from rest_framework import serializers

from apps.matches.models import Match

from .models import Comment, Poll, PollVote, Prediction, Reaction


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = ["id", "user", "target_type", "target_id", "emoji", "created_at"]
        read_only_fields = ["user", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        obj, _ = Reaction.objects.get_or_create(**validated_data)
        return obj


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ["id", "user", "match", "home_score", "away_score",
                  "first_scorer_name", "points_awarded", "created_at"]
        read_only_fields = ["user", "points_awarded", "created_at"]

    def validate(self, data):
        match: Match = data.get("match")
        if match and match.status != Match.Status.UPCOMING:
            raise serializers.ValidationError(
                "Predictions are locked once kickoff happens."
            )
        for k in ("home_score", "away_score"):
            if data.get(k) is None or data[k] < 0 or data[k] > 20:
                raise serializers.ValidationError({k: "Must be between 0 and 20."})
        return data

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        obj, _ = Prediction.objects.update_or_create(
            user=validated_data["user"], match=validated_data["match"],
            defaults={
                "home_score": validated_data["home_score"],
                "away_score": validated_data["away_score"],
                "first_scorer_name": validated_data.get("first_scorer_name", ""),
            },
        )
        return obj


class PollSerializer(serializers.ModelSerializer):
    counts = serializers.SerializerMethodField()
    my_vote = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ["id", "match", "author", "question", "options",
                  "closes_at", "auto_generated", "counts", "my_vote", "created_at"]
        read_only_fields = ["author", "auto_generated", "created_at"]

    def get_counts(self, obj: Poll) -> list[int]:
        tallied = [0] * len(obj.options)
        for idx in PollVote.objects.filter(poll=obj).values_list("option_index", flat=True):
            if 0 <= idx < len(tallied):
                tallied[idx] += 1
        return tallied

    def get_my_vote(self, obj: Poll):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        v = PollVote.objects.filter(poll=obj, user=request.user).first()
        return v.option_index if v else None

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)


class PollVoteSerializer(serializers.Serializer):
    option_index = serializers.IntegerField(min_value=0)


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "author", "target_type", "target_id", "body", "created_at"]
        read_only_fields = ["author", "created_at"]

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)
