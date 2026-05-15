"""
Auto-create polls on key match events (RED card, late goal).
Broadcast new polls + vote updates over Channels.
"""
from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from apps.matches.models import MatchEvent

from .models import Poll, PollVote

log = logging.getLogger("fanpitch.interactions")


def _broadcast(match_id: int, kind: str, payload: dict) -> None:
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        f"match.{match_id}",
        {"type": kind.replace(".", "_"), "data": {"type": kind, **payload}},
    )


@receiver(post_save, sender=MatchEvent)
def auto_poll_on_card(sender, instance: MatchEvent, created: bool, **kwargs):
    if not created:
        return
    template = None
    if instance.type == MatchEvent.Type.RED:
        template = {
            "question": f"Carton rouge pour {instance.player_name or 'le joueur'} — juste ?",
            "options": ["Oui, mérité", "Non, sévère", "À revoir au ralenti"],
        }
    elif instance.type == MatchEvent.Type.GOAL and instance.minute >= 75:
        template = {
            "question": f"But à la {instance.minute}' — le tournant du match ?",
            "options": ["Oui, ça change tout", "Non, juste un détail",
                        "Trop tôt pour le dire"],
        }
    if template:
        poll = Poll.objects.create(
            match_id=instance.match_id,
            question=template["question"],
            options=template["options"],
            closes_at=timezone.now() + timedelta(minutes=3),
            auto_generated=True,
        )
        _broadcast(instance.match_id, "match.poll.open", {
            "id": poll.id, "question": poll.question, "options": poll.options,
            "closes_at": poll.closes_at.isoformat(),
        })


@receiver(post_save, sender=PollVote)
def broadcast_poll_vote(sender, instance: PollVote, created: bool, **kwargs):
    if not created:
        return
    poll = instance.poll
    if not poll.match_id:
        return
    counts = (
        PollVote.objects.filter(poll=poll)
        .values("option_index")
        .order_by()
    )
    tallied = [0] * len(poll.options)
    for row in PollVote.objects.filter(poll=poll).values_list("option_index", flat=True):
        if 0 <= row < len(tallied):
            tallied[row] += 1
    _broadcast(poll.match_id, "match.poll.update", {
        "id": poll.id, "counts": tallied, "total": sum(tallied),
    })
