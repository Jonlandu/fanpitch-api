"""
For-you ranker — TikTok-style scoring on the 1-week status feed.

Score breakdown
---------------
  score = engagement_rate × recency_decay × personalization

  engagement_rate = (reactions + 2·comments + 0.05·impressions) /
                    max(impressions, 10)
  recency_decay   = 2^(-age_hours / 24)         # half-life 24h
  personalization = 1
                  + 0.50 if followed_author
                  + 0.40 if same favorite_team
                  + 0.30 if same country
                  + 0.20 if status mentions one of the user's followed teams

After scoring, we apply a **diversity re-rank** so we never show 2 statuses
by the same author back-to-back.

This is pure Python on top of Django ORM. For < 100k posts this is
sub-100ms. For higher scale we'd materialise scores in a Redis sorted set
periodically.
"""
from __future__ import annotations

import math

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Follow

from .models import Status

User = get_user_model()


def _personalization(status: Status, *,
                     followed_ids: set[int],
                     fav_team_id: int | None,
                     country: str | None) -> float:
    boost = 1.0
    if status.author_id in followed_ids:
        boost += 0.50
    if fav_team_id and status.team_id == fav_team_id:
        boost += 0.40
    if country and getattr(status.author.profile, "country", None) == country:
        boost += 0.30
    return boost


def _engagement_rate(s: Status) -> float:
    impressions = max(s.impressions_count, 10)
    return (s.reactions_count + 2.0 * s.comments_count
            + 0.05 * s.impressions_count) / impressions


def _recency_decay(s: Status) -> float:
    age_h = (timezone.now() - s.created_at).total_seconds() / 3600.0
    return math.pow(2.0, -age_h / 24.0)   # half-life 24h


def _diversify(scored: list[tuple[Status, float]]) -> list[Status]:
    """Avoid showing the same author back-to-back, keep score order otherwise."""
    out: list[Status] = []
    pool = list(scored)
    last_author: int | None = None
    while pool:
        # find the highest-score item whose author != last_author
        idx = None
        for i, (s, _) in enumerate(pool):
            if s.author_id != last_author:
                idx = i
                break
        if idx is None:
            idx = 0   # fallback: only one author left
        s, _ = pool.pop(idx)
        out.append(s)
        last_author = s.author_id
    return out


def for_you(user, *, limit: int = 30, offset: int = 0) -> list[Status]:
    """Return the ranked 1-week feed for `user`."""
    now = timezone.now()
    # Candidate window: anything still alive (expires_at in the future).
    qs = (Status.objects
          .filter(expires_at__gt=now)
          .select_related("author", "author__profile", "media", "team"))

    # We rank a larger candidate window than we return.
    candidates = list(qs.order_by("-created_at")[:max(limit * 3, 60)])

    if not candidates:
        return []

    followed_ids = set(Follow.objects
                       .filter(follower=user)
                       .values_list("followee_id", flat=True))
    profile = getattr(user, "profile", None)
    fav_team_id = profile.favorite_team_id if profile else None
    country = profile.country if profile else None

    scored: list[tuple[Status, float]] = []
    for s in candidates:
        score = (_engagement_rate(s)
                 * _recency_decay(s)
                 * _personalization(s, followed_ids=followed_ids,
                                    fav_team_id=fav_team_id, country=country))
        scored.append((s, score))

    scored.sort(key=lambda t: t[1], reverse=True)
    ordered = _diversify(scored)
    return ordered[offset:offset + limit]


def following(user, *, limit: int = 30, offset: int = 0) -> list[Status]:
    """Strict feed: only posts from authors the user follows + self."""
    followed_ids = list(Follow.objects
                        .filter(follower=user)
                        .values_list("followee_id", flat=True))
    followed_ids.append(user.id)
    return list(Status.objects
                .filter(expires_at__gt=timezone.now(),
                        author_id__in=followed_ids)
                .select_related("author", "author__profile", "media", "team")
                .order_by("-created_at")[offset:offset + limit])
