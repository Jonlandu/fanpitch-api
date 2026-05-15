"""
JWT auth middleware for Channels.

Accepts ?token=<access> in the WebSocket querystring. Resolves to a Django
user and stashes it on scope["user"]. If invalid, scope["user"] = AnonymousUser.
"""
from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

User = get_user_model()


@database_sync_to_async
def _resolve(token: str):
    try:
        validated = UntypedToken(token)
        user_id = validated["user_id"]
        return User.objects.select_related("profile").get(pk=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        qs = parse_qs((scope.get("query_string") or b"").decode())
        token = (qs.get("token") or [None])[0]
        if token:
            scope["user"] = await _resolve(token)
        scope.setdefault("user", AnonymousUser())
        return await super().__call__(scope, receive, send)
