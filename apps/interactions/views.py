from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Comment, Poll, PollVote, Prediction, Reaction
from .serializers import (
    CommentSerializer,
    PollSerializer,
    PollVoteSerializer,
    PredictionSerializer,
    ReactionSerializer,
)


class ReactionViewSet(viewsets.ModelViewSet):
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Reaction.objects.all()
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)
        return qs.select_related("user")


class PredictionViewSet(viewsets.ModelViewSet):
    serializer_class = PredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user).select_related("match")

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response(PredictionSerializer(self.get_queryset(), many=True).data)


class PollViewSet(viewsets.ModelViewSet):
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Poll.objects.all().select_related("author")
        match_id = self.request.query_params.get("match_id")
        if match_id:
            qs = qs.filter(match_id=match_id)
        return qs

    @action(detail=True, methods=["post"], url_path="vote")
    def vote(self, request, pk=None):
        poll = self.get_object()
        ser = PollVoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        idx = ser.validated_data["option_index"]
        if idx >= len(poll.options):
            return Response({"detail": "option_index out of range."},
                            status=status.HTTP_400_BAD_REQUEST)
        PollVote.objects.update_or_create(
            poll=poll, user=request.user,
            defaults={"option_index": idx},
        )
        return Response(PollSerializer(poll, context={"request": request}).data)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Comment.objects.all()
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)
        return qs.select_related("author")
