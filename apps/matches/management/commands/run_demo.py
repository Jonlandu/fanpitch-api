"""
One-shot demo orchestrator.

Equivalent to running, in order:
  1. demo_setup        (teams + fans + signature match + predictions)
  2. run_simulator     (with bots)

So for the hackathon demo, presenters only type:

    python manage.py run_demo

…and the entire experience unfolds.
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "End-to-end demo: seed everything and run the match with bots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--speed", type=float, default=10.0,
            help="Match minutes per real-time second. 1 = real time.",
        )
        parser.add_argument(
            "--skip-seed", action="store_true",
            help="Don't re-run demo_setup (assume the data is already there).",
        )
        parser.add_argument(
            "--match-id", type=int, default=None,
            help="Use a specific match id (otherwise pick the latest demo match).",
        )

    def handle(self, *args, **opts):
        if not opts["skip_seed"]:
            self.stdout.write(self.style.MIGRATE_HEADING("== Seeding demo data =="))
            call_command("demo_setup")

        match_id = opts["match_id"] or self._latest_match_id()
        if not match_id:
            self.stderr.write(self.style.ERROR(
                "No demo match found. Run `python manage.py demo_setup` first."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n== Running match {match_id} at speed {opts['speed']} =="))
        call_command(
            "run_simulator",
            **{"match_id": match_id, "speed": opts["speed"]},
        )

    def _latest_match_id(self) -> int | None:
        from apps.matches.models import Match
        m = (Match.objects
             .filter(source="SIMULATOR")
             .order_by("-id")
             .first())
        return m.id if m else None
