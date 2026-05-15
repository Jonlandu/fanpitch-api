"""
When a MatchEvent is saved:
- broadcast to the match WS group,
- if it's a GOAL/OG/PEN, bump the match score,
- if it's a FULLTIME, mark match finished and schedule prediction scoring.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Match, MatchEvent

log = logging.getLogger("fanpitch.matches")


def _broadcast(match_id: int, kind: str, data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f"match.{match_id}",
        {"type": kind.replace(".", "_"), "data": {"type": kind, **data}},
    )


@receiver(post_save, sender=MatchEvent)
def on_event_created(sender, instance: MatchEvent, created: bool, **kwargs):
    if not created:
        return
    payload = {
        "id": instance.id,
        "match_id": instance.match_id,
        "minute": instance.minute,
        "kind": instance.type,
        "team_id": instance.team_id,
        "player": instance.player_name,
        "detail": instance.detail,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
    }
    _broadcast(instance.match_id, "match.event", payload)

    # update score on scoring events
    if instance.type in (MatchEvent.Type.GOAL, MatchEvent.Type.PENALTY):
        if instance.team_id and instance.team_id == instance.match.home_team_id:
            Match.objects.filter(pk=instance.match_id).update(home_score=models_f_inc("home_score"))
        elif instance.team_id and instance.team_id == instance.match.away_team_id:
            Match.objects.filter(pk=instance.match_id).update(away_score=models_f_inc("away_score"))
        _broadcast_score(instance.match_id)
    elif instance.type == MatchEvent.Type.OWN_GOAL:
        if instance.team_id and instance.team_id == instance.match.home_team_id:
            Match.objects.filter(pk=instance.match_id).update(away_score=models_f_inc("away_score"))
        else:
            Match.objects.filter(pk=instance.match_id).update(home_score=models_f_inc("home_score"))
        _broadcast_score(instance.match_id)
    elif instance.type == MatchEvent.Type.FULLTIME:
        Match.objects.filter(pk=instance.match_id).update(status=Match.Status.FINISHED)
        try:
            from apps.gamification.tasks import score_match_predictions
            score_match_predictions.delay(instance.match_id)
        except Exception as exc:  # pragma: no cover
            log.warning("Could not schedule prediction scoring: %s", exc)


def models_f_inc(field: str):
    from django.db.models import F
    return F(field) + 1


def _broadcast_score(match_id: int) -> None:
    match = Match.objects.only("home_score", "away_score").get(pk=match_id)
    _broadcast(match_id, "match.score",
               {"home": match.home_score, "away": match.away_score})
