"""
Demo bot engine — gives the live match the feeling of being packed with fans.

Each of the 6 demo fans seeded by `demo_setup` is mapped to a persona
(POR_ULTRA, DRC_ULTRA, NEUTRAL, ANALYST, PROVOCATEUR…). When the simulator
emits a MatchEvent, the bot engine fires a fan-out:
- 3-5 reactions (different emojis, different users) — visible live in the
  match room because they go through the same channel layer broadcast as
  human reactions.
- 1-3 short Comment objects.
- Occasionally (on KICKOFF / GOAL / RED / FULLTIME) a Status post in the
  one-week feed.

Everything is best-effort: bot writes are wrapped in try/except so a missing
DB row never crashes the simulator.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from apps.interactions.models import Comment, ReactionTarget
from apps.interactions.reactions_service import add_reaction_and_broadcast

from .bot_lines import EVENT_EMOJIS, LINES, STATUS_LINES

log = logging.getLogger("fanpitch.bots")
User = get_user_model()


PERSONA_OF: dict[str, str] = {
    "kinshasa_kid": "DRC_ULTRA",
    "lisbon_lion":  "POR_CASUAL",
    "ronaldo_fan":  "POR_ULTRA",
    "bakambu_fan":  "DRC_ULTRA",
    "neutral_neil": "NEUTRAL",
    "tactical_tom": "ANALYST",
    "admin":        "PROVOCATEUR",  # the troll account, on purpose
}


@dataclass
class _Persona:
    user_id: int
    username: str
    kind: str
    # cycle through used lines so a fan never repeats themselves in a match
    used_lines: deque


def _build_personas() -> list[_Persona]:
    personas: list[_Persona] = []
    for u in User.objects.filter(username__in=PERSONA_OF.keys()):
        personas.append(_Persona(
            user_id=u.id,
            username=u.username,
            kind=PERSONA_OF[u.username],
            used_lines=deque(maxlen=12),
        ))
    return personas


def _line_for(persona: _Persona, event_kind: str) -> str | None:
    """Pick an unused line. Falls back to ANY line if the persona has none."""
    pool = LINES.get(event_kind, {}).get(persona.kind, [])
    if not pool:
        # fallback to NEUTRAL voice if the persona has no line for this event
        pool = LINES.get(event_kind, {}).get("NEUTRAL", [])
    if not pool:
        return None
    fresh = [l for l in pool if l not in persona.used_lines]
    pick = random.choice(fresh) if fresh else random.choice(pool)
    persona.used_lines.append(pick)
    return pick


def _status_line_for(persona: _Persona) -> str | None:
    pool = STATUS_LINES.get(persona.kind) or STATUS_LINES.get("NEUTRAL", [])
    return random.choice(pool) if pool else None


def react_to_event(event, personas: list[_Persona] | None = None) -> None:
    """
    Called right after a MatchEvent is created. Spawns reactions + comments.
    Optionally schedules a status post.
    """
    personas = personas or _build_personas()
    if not personas:
        log.warning("bot engine: no demo personas found")
        return

    # Determine the bot event "kind" — map GOAL to HOME/AWAY for line selection
    home_id = event.match.home_team_id
    kind = event.type
    if event.type in ("GOAL", "PEN") and event.team_id == home_id:
        kind = "GOAL_HOME"
    elif event.type in ("GOAL", "PEN") and event.team_id and event.team_id != home_id:
        kind = "GOAL_AWAY"
    elif event.type == "OG":
        kind = "GOAL_AWAY" if event.team_id == home_id else "GOAL_HOME"

    emojis = EVENT_EMOJIS.get(kind, ["🔥", "⚽"])

    # 1. Reactions: 3-5 personas tap an emoji, jittered
    reactors = random.sample(personas, k=min(len(personas), random.randint(3, 5)))
    for i, p in enumerate(reactors):
        emoji = random.choice(emojis)
        # small jitter so the counts tick up live, not all at once
        threading.Timer(
            0.10 + i * random.uniform(0.15, 0.40),
            _safe_react,
            args=(p.user_id, event.match_id, event.id, emoji),
        ).start()

    # 2. Comments: 1-3 personas drop a line
    commenters = random.sample(personas, k=min(len(personas), random.randint(1, 3)))
    for i, p in enumerate(commenters):
        line = _line_for(p, kind)
        if not line:
            continue
        threading.Timer(
            0.40 + i * random.uniform(0.30, 0.80),
            _safe_comment,
            args=(p.user_id, event.id, line),
        ).start()

    # 3. Status posts on the big moments only, to avoid feed flood
    if kind in ("KICKOFF", "GOAL_HOME", "GOAL_AWAY", "RED", "FULLTIME"):
        candidates = [p for p in personas if random.random() < 0.45]
        for i, p in enumerate(candidates[:2]):
            text = _status_line_for(p)
            if not text:
                continue
            threading.Timer(
                1.5 + i * random.uniform(0.5, 1.2),
                _safe_status,
                args=(p.user_id, text),
            ).start()


def _safe_react(user_id: int, match_id: int, event_id: int, emoji: str) -> None:
    try:
        add_reaction_and_broadcast(
            user_id=user_id, match_id=match_id,
            target_type=ReactionTarget.MATCH_EVENT,
            target_id=event_id, emoji=emoji,
        )
    except Exception as exc:  # pragma: no cover
        log.warning("bot react failed: %s", exc)


def _safe_comment(user_id: int, event_id: int, body: str) -> None:
    try:
        Comment.objects.create(
            author_id=user_id,
            target_type=ReactionTarget.MATCH_EVENT,
            target_id=event_id,
            body=body[:500],
        )
    except Exception as exc:  # pragma: no cover
        log.warning("bot comment failed: %s", exc)


def _safe_status(user_id: int, body: str) -> None:
    try:
        from apps.feed.models import Status
        Status.objects.create(author_id=user_id, body_text=body[:280])
    except Exception as exc:  # pragma: no cover
        log.warning("bot status failed: %s", exc)


def kickoff_pregame_chatter(match) -> None:
    """
    A small pre-match status flurry — gives the feed life when judges open it
    *before* the simulator starts.
    """
    personas = _build_personas()
    for p in personas:
        text = _status_line_for(p)
        if text:
            _safe_status(p.user_id, text)
            time.sleep(0.05)
