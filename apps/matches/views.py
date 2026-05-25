from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Match, Team
from .serializers import (
    MatchDetailSerializer,
    MatchEventSerializer,
    MatchSerializer,
    TeamSerializer,
)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "short_name", "country"]


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Match.objects.select_related("home_team", "away_team")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "competition"]
    ordering_fields = ["kickoff_at"]
    ordering = ["-kickoff_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MatchDetailSerializer
        return MatchSerializer

    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        match = self.get_object()
        since = request.query_params.get("since")
        qs = match.events.all()
        if since is not None:
            try:
                qs = qs.filter(minute__gte=int(since))
            except ValueError:
                pass
        return Response(MatchEventSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="sim/start",
            permission_classes=[permissions.IsAdminUser])
    def sim_start(self, request, pk=None):
        from .services.simulator import start_simulator_async
        match = self.get_object()
        speed = float(request.data.get("speed", 10))
        start_simulator_async(match.id, speed=speed)
        return Response({"status": "started", "match_id": match.id, "speed": speed})
