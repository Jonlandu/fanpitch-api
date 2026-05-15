"""
Simulator for live match events.

Use either:
- the management command:  python manage.py run_simulator --match-id <id>
- the async starter:       start_simulator_async(match_id) — runs in a daemon thread.

`with_bots=True` (default) makes the demo personas react / comment / post a
status as each event drops. Without it, the room feels empty until a real
human reacts.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from django.utils import timezone

from apps.matches.models import Match, MatchEvent

log = logging.getLogger("fanpitch.simulator")


@dataclass(frozen=True)
class _ScriptedEvent:
    minute: int
    type: str
    side: str | None   # "HOME" / "AWAY" / None
    player: str
    detail: str = ""


# Demo script for Portugal (HOME) vs DR Congo (AWAY).
# Lots of drama on purpose — judges only watch this once, so make it count.
DEFAULT_SCRIPT: list[_ScriptedEvent] = [
    _ScriptedEvent(0,  "KICKOFF",    None,   "",                  "C'est parti, le stade s'enflamme !"),
    _ScriptedEvent(3,  "COMMENTARY", None,   "",                  "Le Portugal pose son jeu, la RDC presse haut."),
    _ScriptedEvent(8,  "YELLOW",     "HOME", "Renato Sanches",    "Tacle un peu trop appuyé sur Wissa."),
    _ScriptedEvent(12, "GOAL",       "HOME", "Cristiano Ronaldo", "Tête imparable sur corner. CR7 toujours là."),
    _ScriptedEvent(18, "COMMENTARY", None,   "",                  "Bakambu pousse, les Léopards y croient !"),
    _ScriptedEvent(23, "YELLOW",     "AWAY", "Chancel Mbemba",    "Faute tactique au milieu pour casser un contre."),
    _ScriptedEvent(29, "COMMENTARY", None,   "",                  "Frappe de Wissa, à côté du poteau gauche !"),
    _ScriptedEvent(34, "COMMENTARY", None,   "",                  "Le rythme s'accélère, l'arbitre laisse jouer."),
    _ScriptedEvent(40, "COMMENTARY", None,   "",                  "Bruno Fernandes tente la lucarne, parade superbe du gardien !"),
    _ScriptedEvent(45, "HALFTIME",   None,   "",                  "Mi-temps. 1-0 Portugal. Les Léopards ont des occasions."),
    _ScriptedEvent(48, "COMMENTARY", None,   "",                  "Reprise des hostilités. La RDC a changé le visage du match."),
    _ScriptedEvent(56, "GOAL",       "AWAY", "Cédric Bakambu",    "Contre-attaque éclair ! Égalisation pour la RDC !"),
    _ScriptedEvent(62, "COMMENTARY", None,   "",                  "Le stade prend feu. Banderoles, drapeaux, fumigènes."),
    _ScriptedEvent(67, "COMMENTARY", None,   "",                  "Le Portugal pousse, gros pressing dans le camp adverse."),
    _ScriptedEvent(74, "COMMENTARY", None,   "",                  "Bruno Fernandes voit son tir frôler la barre. Quel match !"),
    _ScriptedEvent(78, "RED",        "HOME", "Pepe",              "Second jaune sur un retour limite. Le Portugal à 10 !"),
    _ScriptedEvent(82, "COMMENTARY", None,   "",                  "Les Léopards sentent le coup parfait. Tout est possible."),
    _ScriptedEvent(86, "COMMENTARY", None,   "",                  "Mbemba sauve sur sa ligne ! Quelle intervention !"),
    _ScriptedEvent(88, "COMMENTARY", None,   "",                  "Wissa tente le lob… juste à côté ! Aaaaah."),
    _ScriptedEvent(90, "FULLTIME",   None,   "",                  "Coup de sifflet final. Match nul 1-1, mais quel spectacle !"),
]


def _resolve_team(match: Match, side: str | None):
    if side == "HOME":
        return match.home_team
    if side == "AWAY":
        return match.away_team
    return None


def run_simulator(match_id: int, *, speed: float = 10.0,
                  script: list[_ScriptedEvent] | None = None,
                  with_bots: bool = True) -> None:
    """
    Walk a scripted script and create MatchEvent objects at the right wall-clock
    pace. `speed = match minutes per real second`. speed=10 → 90' in ~9s.
    """
    match = Match.objects.select_related("home_team", "away_team").get(pk=match_id)
    if match.status != Match.Status.LIVE:
        match.status = Match.Status.LIVE
        match.kickoff_at = match.kickoff_at or timezone.now()
        match.save(update_fields=["status", "kickoff_at"])

    # Pre-build personas once so we don't re-query for every event.
    personas = None
    if with_bots:
        try:
            from .bots import _build_personas, kickoff_pregame_chatter
            personas = _build_personas()
            kickoff_pregame_chatter(match)
        except Exception as exc:  # pragma: no cover
            log.warning("bot init failed: %s", exc)

    sec_per_min = 1.0 / max(speed, 0.001)
    last_minute = 0
    log.info("Simulator started for match=%s speed=%s bots=%s",
             match_id, speed, with_bots)
    for ev in script or DEFAULT_SCRIPT:
        delay = max(0.0, (ev.minute - last_minute) * sec_per_min)
        time.sleep(delay)
        last_minute = ev.minute
        match_event = MatchEvent.objects.create(
            match=match,
            minute=ev.minute,
            type=ev.type,
            team=_resolve_team(match, ev.side),
            player_name=ev.player,
            detail=ev.detail,
        )
        log.info("emit match=%s %s' %s", match_id, ev.minute, ev.type)

        if with_bots and personas:
            try:
                from .bots import react_to_event
                react_to_event(match_event, personas=personas)
            except Exception as exc:  # pragma: no cover
                log.warning("bot react_to_event failed: %s", exc)

    # Let trailing bot Timers (reactions/comments/statuses scheduled for the
    # final event) finish before the simulator returns — otherwise they fire
    # after interpreter shutdown when run from the command line.
    if with_bots:
        time.sleep(3.5)
    log.info("Simulator finished for match=%s", match_id)


def start_simulator_async(match_id: int, *, speed: float = 10.0,
                          with_bots: bool = True) -> None:
    """Fire-and-forget in a daemon thread. Good enough for the demo."""
    t = threading.Thread(
        target=run_simulator,
        kwargs={"match_id": match_id, "speed": speed, "with_bots": with_bots},
        daemon=True,
        name=f"sim-{match_id}",
    )
    t.start()
