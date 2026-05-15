from rest_framework import serializers

from .models import Match, MatchEvent, Team


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "short_name", "country", "crest_url",
                  "color_primary", "color_secondary"]


class MatchEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchEvent
        fields = ["id", "match", "minute", "type", "team", "player_name",
                  "detail", "payload", "created_at"]
        read_only_fields = ["created_at"]


class MatchSerializer(serializers.ModelSerializer):
    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    home_team_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Team.objects.all(), source="home_team")
    away_team_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Team.objects.all(), source="away_team")

    class Meta:
        model = Match
        fields = ["id", "home_team", "away_team", "home_team_id", "away_team_id",
                  "kickoff_at", "status", "home_score", "away_score",
                  "competition", "venue", "source", "external_id", "created_at"]
        read_only_fields = ["status", "home_score", "away_score", "created_at"]


class MatchDetailSerializer(MatchSerializer):
    recent_events = serializers.SerializerMethodField()

    class Meta(MatchSerializer.Meta):
        fields = MatchSerializer.Meta.fields + ["recent_events"]

    def get_recent_events(self, obj):
        return MatchEventSerializer(obj.events.order_by("-minute", "-id")[:10],
                                    many=True).data
