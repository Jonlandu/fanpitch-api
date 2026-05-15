"""
Match-room WebSocket consumer.

URL: /ws/match/<match_id>/?token=<JWT_ACCESS>

Server → client envelopes:
  {"type":"match.event",        "data":{...}}
  {"type":"match.score",        "data":{"home":1,"away":1}}
  {"type":"match.reaction",     "data":{"target_id":..,"emoji":"🔥","count":1284}}
  {"type":"match.poll.open",    "data":{"id":..,"question":"...","options":[...]}}
  {"type":"match.poll.update",  "data":{"id":..,"counts":[..],"total":..}}

Client → server:
  {"type":"reaction.send","target_type":"MATCH_EVENT","target_id":41,"emoji":"🔥"}
  {"type":"poll.vote","poll_id":9,"option_index":1}
"""
from __future__ import annotations

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

log = logging.getLogger("fanpitch.ws")


class MatchConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.match_id = int(self.scope["url_route"]["kwargs"]["match_id"])
        self.group = f"match.{self.match_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({
            "type": "match.welcome",
            "data": {"match_id": self.match_id, "user_id": user.id},
        })

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        if kind == "reaction.send":
            await self._handle_reaction(content)
        elif kind == "poll.vote":
            await self._handle_vote(content)
        elif kind == "ping":
            await self.send_json({"type": "pong"})

    async def _handle_reaction(self, content):
        target_type = content.get("target_type", "MATCH_EVENT")
        target_id = int(content.get("target_id") or 0)
        emoji = (content.get("emoji") or "").strip()[:8]
        if not target_id or not emoji:
            return
        user_id = self.scope["user"].id
        await self._add_reaction(user_id, target_type, target_id, emoji)

    @database_sync_to_async
    def _add_reaction(self, user_id, target_type, target_id, emoji):
        from apps.interactions.reactions_service import add_reaction_and_broadcast
        add_reaction_and_broadcast(
            user_id=user_id, match_id=self.match_id,
            target_type=target_type, target_id=target_id, emoji=emoji,
        )

    async def _handle_vote(self, content):
        try:
            poll_id = int(content["poll_id"])
            option_index = int(content["option_index"])
        except (KeyError, ValueError, TypeError):
            return
        await self._save_vote(self.scope["user"].id, poll_id, option_index)

    @database_sync_to_async
    def _save_vote(self, user_id, poll_id, option_index):
        from apps.interactions.models import Poll, PollVote
        try:
            poll = Poll.objects.get(pk=poll_id)
        except Poll.DoesNotExist:
            return
        if 0 <= option_index < len(poll.options):
            PollVote.objects.update_or_create(
                poll=poll, user_id=user_id,
                defaults={"option_index": option_index},
            )

    # group event handlers (named after consumer dispatch key)
    async def match_event(self, event):     await self.send_json(event["data"])
    async def match_score(self, event):     await self.send_json(event["data"])
    async def match_reaction(self, event):  await self.send_json(event["data"])
    async def match_poll_open(self, event): await self.send_json(event["data"])
    async def match_poll_update(self, event): await self.send_json(event["data"])
