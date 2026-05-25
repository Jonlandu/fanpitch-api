"""
Service helpers for granting points + awarding badges.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from .models import Badge, PointsEvent, UserBadge

User = get_user_model()


BADGE_RULES = {
    "FIRST_KICK":      {"name": "First Kick",
                        "description": "Welcome to FanPitch."},
    "ORACLE":          {"name": "Oracle",
                        "description": "5 exact-score predictions."},
    "KEYBOARD_WARRIOR":{"name": "Keyboard Warrior",
                        "description": "100 reactions sent."},
    "MEME_LORD":       {"name": "Meme Lord",
                        "description": "3 statuses with 25+ reactions."},
    "LOYAL_FAN":       {"name": "Loyal Fan",
                        "description": "30-day login streak."},
    "LIVE_LEGEND":     {"name": "Live Legend",
                        "description": "Top-10 in a match leaderboard."},
}


def ensure_badges_exist() -> None:
    for code, defaults in BADGE_RULES.items():
        Badge.objects.update_or_create(code=code, defaults=defaults)


@transaction.atomic
def grant_points(user, source: str, *, source_id: int | None = None,
                 delta: int, note: str = "") -> PointsEvent:
    evt = PointsEvent.objects.create(
        user=user, source=source, source_id=source_id, delta=delta, note=note,
    )
    from apps.accounts.models import Profile
    Profile.objects.filter(user=user).update(points=F("points") + delta)
    return evt


def award_badge(user, code: str) -> UserBadge | None:
    badge, _ = Badge.objects.get_or_create(
        code=code, defaults=BADGE_RULES.get(code, {"name": code}),
    )
    ub, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return ub if created else None


def check_badges_for(user) -> list[str]:
    """Idempotent badge sweep for a user. Returns list of newly awarded codes."""
    awarded: list[str] = []

    from apps.feed.models import Status
    from apps.interactions.models import Prediction, Reaction

    if Prediction.objects.filter(user=user, points_awarded=50).count() >= 5:
        if award_badge(user, "ORACLE"):
            awarded.append("ORACLE")
    if Reaction.objects.filter(user=user).count() >= 100:
        if award_badge(user, "KEYBOARD_WARRIOR"):
            awarded.append("KEYBOARD_WARRIOR")
    if Status.objects.filter(author=user).count() >= 1:
        if not UserBadge.objects.filter(user=user, badge__code="FIRST_KICK").exists():
            award_badge(user, "FIRST_KICK")
            awarded.append("FIRST_KICK")
    return awarded
