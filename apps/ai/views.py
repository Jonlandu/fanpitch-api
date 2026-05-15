from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.matches.models import Match

from .bedrock_client import generate_caption, generate_meme


class AiThrottle(UserRateThrottle):
    scope = "ai"


def _match_summary(match_id: int | None) -> str:
    if not match_id:
        return ""
    try:
        m = Match.objects.select_related("home_team", "away_team").get(pk=match_id)
    except Match.DoesNotExist:
        return ""
    return (f"{m.home_team.name} {m.home_score}-{m.away_score} {m.away_team.name} "
            f"({m.status})")


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([AiThrottle])
def ai_caption(request):
    match_id = request.data.get("match_id")
    summary = _match_summary(match_id) if match_id else request.data.get("summary", "")
    return Response(generate_caption(request.user, match_summary=summary))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([AiThrottle])
def ai_meme(request):
    match_id = request.data.get("match_id")
    summary = _match_summary(match_id) if match_id else request.data.get("summary", "")
    return Response(generate_meme(request.user, match_summary=summary))
