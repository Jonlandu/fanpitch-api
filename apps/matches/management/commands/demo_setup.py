"""
One-shot seeding for the hackathon demo.

Creates:
- Teams: Portugal, DR Congo, France, Brazil, Argentina, Morocco.
- A demo admin (admin/admin) and 6 fans with predictions.
- The signature match Portugal vs DR Congo, kicking off in 1 minute.

Run:  python manage.py demo_setup
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.matches.models import Match, Team

User = get_user_model()


TEAMS = [
    ("Portugal", "POR", "Portugal", "#FF0000"),
    ("DR Congo", "COD", "DR Congo", "#0096FF"),
    ("France", "FRA", "France", "#0055A4"),
    ("Brazil", "BRA", "Brazil", "#FEDB00"),
    ("Argentina", "ARG", "Argentina", "#75AADB"),
    ("Morocco", "MAR", "Morocco", "#C1272D"),
]

DEMO_FANS = [
    ("kinshasa_kid", "kinshasa_kid@example.com", "Kinshasa Kid"),
    ("lisbon_lion",  "lisbon_lion@example.com",  "Lisbon Lion"),
    ("ronaldo_fan",  "ronaldo_fan@example.com",  "RonaldoFan7"),
    ("bakambu_fan",  "bakambu_fan@example.com",  "BakambuRules"),
    ("neutral_neil", "neutral_neil@example.com", "Neutral Neil"),
    ("tactical_tom", "tactical_tom@example.com", "Tactical Tom"),
]


class Command(BaseCommand):
    help = "Seed teams, demo fans and the signature Portugal vs DR Congo match."

    def handle(self, *args, **opts):
        # Teams
        team_lookup: dict[str, Team] = {}
        for name, short, country, color in TEAMS:
            team, _ = Team.objects.update_or_create(
                short_name=short,
                defaults={"name": name, "country": country, "color_primary": color},
            )
            team_lookup[short] = team
            self.stdout.write(f"team: {team}")

        # Admin
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@fanpitch.local", "admin12345")
            self.stdout.write("admin / admin12345 created")

        # Demo fans
        fans = []
        for username, email, display in DEMO_FANS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            if created:
                user.set_password("fanpitch1234")
                user.save()
            user.profile.display_name = display
            user.profile.favorite_team = team_lookup["COD"] if "kinshasa" in username or "bakambu" in username else team_lookup["POR"]
            user.profile.country = "DR Congo" if "kinshasa" in username or "bakambu" in username else "Portugal"
            user.profile.save()
            fans.append(user)

        # Signature match Portugal vs DR Congo, kickoff in +1 minute (UTC)
        kickoff = timezone.now() + timedelta(minutes=1)
        match, _ = Match.objects.update_or_create(
            home_team=team_lookup["POR"],
            away_team=team_lookup["COD"],
            kickoff_at__date=kickoff.date(),
            defaults={
                "kickoff_at": kickoff,
                "status": Match.Status.UPCOMING,
                "competition": "FanPitch Showcase",
                "venue": "FanPitch Arena",
                "source": "SIMULATOR",
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Match seeded: {match} (id={match.id})"))

        # Seed predictions: half pick 1-1, two pick 2-1 POR, two pick 0-1 COD
        try:
            from apps.interactions.models import Prediction
            scripted = [(1, 1), (1, 1), (2, 1), (2, 1), (0, 1), (1, 0)]
            for user, (h, a) in zip(fans, scripted):
                Prediction.objects.update_or_create(
                    user=user, match=match,
                    defaults={"home_score": h, "away_score": a},
                )
            self.stdout.write("predictions seeded for demo fans")
        except Exception as exc:  # pragma: no cover
            self.stdout.write(self.style.WARNING(f"could not seed predictions: {exc}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDONE. To start the live match:\n"
            f"  python manage.py run_simulator --match-id {match.id} --speed 10\n"
            f"\nLogin as admin/admin12345 or any demo fan with password fanpitch1234.\n"
        ))
