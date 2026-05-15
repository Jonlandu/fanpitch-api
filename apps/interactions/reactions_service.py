"""
Shared helper to add a reaction and broadcast its updated count.

Used both by:
- the WebSocket consumer (apps.realtime.consumers.MatchConsumer)
- the demo bot engine (apps.matches.services.bots)
"""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from .models import Reaction

REACTION_COUNTER_KEY = "match:{match_id}:event:{event_id}:{emoji}"
REACTION_BUCKET_TTL = 60 * 60 * 24


def add_reaction_and_broadcast(*, user_id: int, match_id: int,
                                target_type: str, target_id: int, emoji: str) -> int:
    """Create the Reaction (idempotent), bump the Redis counter, broadcast."""
    Reaction.objects.get_or_create(
        user_id=user_id, target_type=target_type,
        target_id=target_id, emoji=emoji,
    )
    key = REACTION_COUNTER_KEY.format(
        match_id=match_id, event_id=target_id, emoji=emoji,
    )
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, REACTION_BUCKET_TTL)
        count = 1

    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(
            f"match.{match_id}",
            {
                "type": "match_reaction",
                "data": {
                    "type": "match.reaction",
                    "target_id": target_id,
                    "emoji": emoji,
                    "count": count,
                },
            },
        )
    return count
