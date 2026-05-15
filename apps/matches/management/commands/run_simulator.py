from django.core.management.base import BaseCommand

from apps.matches.services.simulator import run_simulator


class Command(BaseCommand):
    help = "Run the FanPitch live-match simulator for the given match id."

    def add_arguments(self, parser):
        parser.add_argument("--match-id", type=int, required=True)
        parser.add_argument(
            "--speed", type=float, default=10.0,
            help="Match minutes per real-time second. 10 = 90' in ~9s.",
        )
        parser.add_argument(
            "--no-bots", action="store_true",
            help="Disable demo fan bots (only emits raw events).",
        )

    def handle(self, *args, **opts):
        run_simulator(
            opts["match_id"],
            speed=opts["speed"],
            with_bots=not opts["no_bots"],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Simulator finished for match {opts['match_id']}"))
