"""
Populate FanPitch with a world-cup-style demo dataset:
- 10 country teams with primary colours
- 20 demo fan accounts (2 per country) with shareable credentials
- 8 matches spanning past / live / upcoming so the feed has variety

Idempotent: re-running updates rather than duplicates.

Run:  python manage.py seed_world_cup
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.matches.models import Match, Team

User = get_user_model()

DEMO_PASSWORD = "fanpitch2026"

COUNTRIES = [
    # (full_name,    short, country,        primary,   secondary)
    ("DR Congo",     "COD", "DR Congo",     "#0096FF", "#FFFFFF"),
    ("Portugal",     "POR", "Portugal",     "#FF0000", "#006600"),
    ("France",       "FRA", "France",       "#0055A4", "#EF4135"),
    ("Argentina",    "ARG", "Argentina",    "#75AADB", "#FFFFFF"),
    ("Brazil",       "BRA", "Brazil",       "#FEDB00", "#009B3A"),
    ("Morocco",      "MAR", "Morocco",      "#C1272D", "#006233"),
    ("Senegal",      "SEN", "Senegal",      "#00853F", "#FDEF42"),
    ("Cameroon",     "CMR", "Cameroon",     "#007A5E", "#FCD116"),
    ("Spain",        "ESP", "Spain",        "#AA151B", "#F1BF00"),
    ("Nigeria",      "NGA", "Nigeria",      "#008751", "#FFFFFF"),
]

# 2 fans per country — shareable credentials
FANS = [
    # (username,        display_name,        country_short)
    ("congo_general",   "Le General Kin",    "COD"),
    ("kinshasa_kid",    "Kinshasa Kid",      "COD"),
    ("lisbon_lion",     "Lisbon Lion",       "POR"),
    ("ronaldo_fan",     "RonaldoFan7",       "POR"),
    ("paris_fan",       "Paris Saint-Fan",   "FRA"),
    ("mbappe_addict",   "Mbappé Addict",     "FRA"),
    ("messi_devoto",    "Messi Devoto",      "ARG"),
    ("buenos_fan",      "Buenos Aires Boy",  "ARG"),
    ("samba_king",      "Samba King",        "BRA"),
    ("rio_carioca",     "Rio Carioca",       "BRA"),
    ("atlas_lion",      "Atlas Lion",        "MAR"),
    ("casablanca_fan",  "Casa Blanca",       "MAR"),
    ("teranga_fan",     "Teranga Fan",       "SEN"),
    ("dakar_diva",      "Dakar Diva",        "SEN"),
    ("indomitable_fan", "Indomitable Fan",   "CMR"),
    ("yaounde_yoda",    "Yaoundé Yoda",      "CMR"),
    ("la_furia",        "La Furia",          "ESP"),
    ("madrid_madrugada","Madrid Madrugada",  "ESP"),
    ("naija_naija",     "Naija Naija",       "NGA"),
    ("lagos_legend",    "Lagos Legend",      "NGA"),
]


def _matches_schedule(team_lookup: dict[str, Team]) -> list[dict]:
    """Build a mix of finished / live / upcoming matches around 'now'."""
    now = timezone.now()

    return [
        # ── Past (finished) ───────────────────────────────────────
        dict(
            home="POR", away="FRA",
            kickoff=now - timedelta(days=2),
            status=Match.Status.FINISHED,
            home_score=2, away_score=1,
            competition="FanPitch Cup — Group A",
            venue="Stade des Étoiles",
        ),
        dict(
            home="BRA", away="ARG",
            kickoff=now - timedelta(days=1, hours=4),
            status=Match.Status.FINISHED,
            home_score=1, away_score=2,
            competition="FanPitch Cup — Group B",
            venue="Estadio Sambo",
        ),
        dict(
            home="MAR", away="SEN",
            kickoff=now - timedelta(hours=20),
            status=Match.Status.FINISHED,
            home_score=0, away_score=0,
            competition="FanPitch Cup — Group C",
            venue="Stade Atlas",
        ),
        # ── Live (right now) ──────────────────────────────────────
        dict(
            home="COD", away="POR",
            kickoff=now - timedelta(minutes=23),
            status=Match.Status.LIVE,
            home_score=1, away_score=1,
            competition="FanPitch Cup — Quarter Final",
            venue="Stade des Martyrs",
        ),
        dict(
            home="ESP", away="CMR",
            kickoff=now - timedelta(minutes=12),
            status=Match.Status.LIVE,
            home_score=0, away_score=1,
            competition="FanPitch Cup — Quarter Final",
            venue="Estadio Cibeles",
        ),
        # ── Upcoming ──────────────────────────────────────────────
        dict(
            home="FRA", away="ARG",
            kickoff=now + timedelta(hours=3),
            status=Match.Status.UPCOMING,
            home_score=0, away_score=0,
            competition="FanPitch Cup — Semi Final",
            venue="Parc des Vainqueurs",
        ),
        dict(
            home="NGA", away="BRA",
            kickoff=now + timedelta(hours=6),
            status=Match.Status.UPCOMING,
            home_score=0, away_score=0,
            competition="FanPitch Cup — Semi Final",
            venue="National Stadium Lagos",
        ),
        dict(
            home="COD", away="MAR",
            kickoff=now + timedelta(days=1, hours=2),
            status=Match.Status.UPCOMING,
            home_score=0, away_score=0,
            competition="FanPitch Cup — Final",
            venue="FanPitch Arena",
        ),
    ]


class Command(BaseCommand):
    help = "Seed 10 countries, 20 demo fans and 8 matches for the hackathon demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset every demo fan password back to the shared DEMO_PASSWORD.",
        )

    def handle(self, *args, reset_passwords: bool = False, **opts):
        # 1. Teams
        team_lookup: dict[str, Team] = {}
        for name, short, country, primary, secondary in COUNTRIES:
            team, _ = Team.objects.update_or_create(
                short_name=short,
                defaults={
                    "name": name,
                    "country": country,
                    "color_primary": primary,
                    "color_secondary": secondary,
                },
            )
            team_lookup[short] = team
        self.stdout.write(self.style.SUCCESS(f"✓ {len(team_lookup)} teams ready"))

        # 2. Demo admin (idempotent)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", "admin@fanpitch.local", "admin12345"
            )
            self.stdout.write("✓ admin / admin12345 created")

        # 3. Fans (2 per country)
        created_count = 0
        for username, display, country_short in FANS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@fanpitch.demo"},
            )
            if created or reset_passwords:
                user.set_password(DEMO_PASSWORD)
                user.save()
            if created:
                created_count += 1

            team = team_lookup[country_short]
            user.profile.display_name = display
            user.profile.favorite_team = team
            user.profile.country = team.country
            user.profile.save()
        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(FANS)} fans ready ({created_count} newly created)"
        ))

        # 4. Matches
        match_count = 0
        for m in _matches_schedule(team_lookup):
            obj, _ = Match.objects.update_or_create(
                home_team=team_lookup[m["home"]],
                away_team=team_lookup[m["away"]],
                kickoff_at__date=m["kickoff"].date(),
                defaults={
                    "kickoff_at": m["kickoff"],
                    "status": m["status"],
                    "home_score": m["home_score"],
                    "away_score": m["away_score"],
                    "competition": m["competition"],
                    "venue": m["venue"],
                    "source": "SEED",
                },
            )
            match_count += 1
        self.stdout.write(self.style.SUCCESS(f"✓ {match_count} matches scheduled"))

        # 5. Predictions for upcoming matches
        try:
            from apps.interactions.models import Prediction
            upcoming = Match.objects.filter(status=Match.Status.UPCOMING)
            users = list(User.objects.filter(is_superuser=False))
            for match in upcoming:
                # Each upcoming match gets predictions from ~half the demo fans
                for user in random.sample(users, k=min(10, len(users))):
                    Prediction.objects.update_or_create(
                        user=user, match=match,
                        defaults={
                            "home_score": random.randint(0, 3),
                            "away_score": random.randint(0, 3),
                        },
                    )
            self.stdout.write(self.style.SUCCESS(
                f"✓ predictions seeded across {upcoming.count()} upcoming matches"
            ))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f"⚠ could not seed predictions: {exc}"
            ))

        # 6. Print credentials block
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "═══════════════════════════════════════════════════════════"
        ))
        self.stdout.write(self.style.SUCCESS(
            "  DEMO CREDENTIALS — share with your testers"
        ))
        self.stdout.write(self.style.SUCCESS(
            "═══════════════════════════════════════════════════════════"
        ))
        self.stdout.write(f"  Password for ALL demo fans:  {DEMO_PASSWORD}")
        self.stdout.write(f"  Admin:                        admin / admin12345")
        self.stdout.write("")
        self.stdout.write("  Usernames by country:")
        by_country: dict[str, list[str]] = {}
        for username, _display, country_short in FANS:
            by_country.setdefault(country_short, []).append(username)
        for short, names in by_country.items():
            team = team_lookup[short]
            self.stdout.write(f"    {team.name:<14} {', '.join(names)}")
        self.stdout.write("")
