from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Badge, PointsEvent, UserBadge

User = get_user_model()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def leaderboard(request):
    scope = request.query_params.get("scope", "global")
    match_id = request.query_params.get("match_id")
    qs = PointsEvent.objects.all()

    if scope == "match" and match_id:
        qs = qs.filter(source="PREDICTION", note__icontains=f"match {match_id}")
    elif scope == "week":
        since = timezone.now() - timedelta(days=7)
        qs = qs.filter(created_at__gte=since)
    # else global

    rows = (qs.values("user_id")
            .annotate(score=Sum("delta"))
            .order_by("-score")[:50])
    # enrich with username + display_name
    user_map = {
        u.id: u for u in User.objects.filter(id__in=[r["user_id"] for r in rows])
        .select_related("profile")
    }
    out = []
    for r in rows:
        u = user_map.get(r["user_id"])
        if not u:
            continue
        out.append({
            "user_id": u.id,
            "username": u.username,
            "display_name": u.profile.display_name or u.username,
            "country": u.profile.country,
            "points": r["score"] or 0,
        })
    return Response({"scope": scope, "match_id": match_id, "entries": out})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_badges(request):
    rows = (UserBadge.objects
            .filter(user=request.user)
            .select_related("badge"))
    return Response([
        {"code": r.badge.code, "name": r.badge.name,
         "description": r.badge.description, "awarded_at": r.awarded_at}
        for r in rows
    ])


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def all_badges(request):
    return Response([
        {"code": b.code, "name": b.name, "description": b.description,
         "icon_url": b.icon_url}
        for b in Badge.objects.all()
    ])
