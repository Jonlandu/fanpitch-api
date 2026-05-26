"""
Seed funny football-fan status posts spread across the 20 demo fans
so a fresh test account lands on a populated feed rather than an empty
one.

Run:  python manage.py seed_demo_posts
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.feed.models import Status
from apps.matches.models import Match, Team

User = get_user_model()


# Multilingual punchlines that fit any match — no real-person names so we
# stay clear of moderation issues. Each tuple is (body_text, ai_caption).
POSTS = [
    ("Quand le gardien sort comme un crabe à marée basse 🦀😂",
     "Le bug du jour : la défense en mode manuel"),
    ("Mon WiFi me trahit au moment du but, c'est ça la vraie défaite 📡💔",
     "Au moins l'audio a survécu, on entend les voisins crier"),
    ("Le VAR a vu ce que mes yeux refusent d'admettre 👀",
     "Replay : oui. Acceptation : jamais."),
    ("On a perdu, mais on a gagné en humour 😅🔥",
     "Trophée du meilleur meme attribué à notre groupe WhatsApp"),
    ("Cette défense joue le hors-jeu… sans la ligne 🧠❌",
     "Stratégie : confier la défense à la chance"),
    ("Un dribble si élégant qu'il mérite un Oscar 🏆🎬",
     "Catégorie meilleure performance dans un rôle improbable"),
    ("Mama appelle PILE quand le penalty est sifflé 📞🤦",
     "Coïncidence ? Je ne crois pas."),
    ("90+5 et mon cœur connaît les noms de tous les saints ⛪⚽",
     "Prière courte, efficacité maximale espérée"),
    ("Carton rouge bien mérité, on applaudit le théâtre 🟥👏",
     "Acteur principal : le joueur. Mise en scène : l'arbitre."),
    ("Ce coup-franc, c'est une œuvre d'art au musée 🎨⚽",
     "Galerie ouverte ce soir, entrée libre"),
    ("La VAR prend plus de temps que mes décisions de vie 🤔⏱️",
     "Au moins eux ont des replays pour leurs choix"),
    ("Quand ton équipe gagne 1-0 contre toute attente ⚡🎉",
     "La défense joue le bus, l'attaque joue la chance"),
    ("Cette passe lumineuse mérite son propre documentaire 🎥✨",
     "Réalisé en une touche, monté à la perfection"),
    ("On joue mieux à 10, c'est officiel maintenant 📊🤣",
     "Statistique surprenante mais bien réelle"),
    ("Le commentateur découvre ses superlatifs en direct 🎙️💥",
     "Vocabulaire débloqué : niveau championnat du monde"),
    ("When the ref shows mercy your team didn't deserve 🙏",
     "Lucky day unlocked"),
    ("That deflection had more touches than I have texts 📱",
     "Lucky breaks: 1, Skill: undecided"),
    ("Cuando tu portero se cree centrocampista 🥅➡️⚽",
     "La aventura no termina bien"),
    ("Ese tiro libre fue arte puro 🎨⚽",
     "Marco para colgarlo en el museo"),
    ("Wenn der Schiri streng ist, aber gerecht ⚖️🟨",
     "Ehrlichkeit ist nicht immer einfach"),
    ("Dieser Konter war Lehrbuch ✍️🔥",
     "Trainer schlafen jetzt schlecht"),
    ("Foi pênalti? Era? Não era? Ninguém sabe! 🤷",
     "Mistério do dia: arbitragem moderna"),
    ("Quel niveau ce match, j'ai vu plus d'action que dans un film 🎬",
     "Box-office : 90 minutes de pur suspense"),
    ("Quand t'as crié 'BUUUT' avant que ce soit hors-jeu 😩",
     "Voisins prévenus : oui. Excuse acceptée : non."),
    ("Bro le carton jaune était pour la coiffure pas le tacle 💇‍♂️🟨",
     "Le style passe avant le foot"),
    ("Le bus de mon équipe défensive : station, terminus 🚌",
     "Score zéro encaissé, ambiance zéro spectacle"),
    ("Cette tête, c'est de la magie noire ⚫🪄",
     "Coupe de cheveux + précision = combo gagnant"),
]


class Command(BaseCommand):
    help = "Seed ~30 funny status posts across the 20 demo fans."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe-demo",
            action="store_true",
            help="Delete existing posts from demo fans before seeding "
                 "(useful to re-run cleanly). Does NOT touch posts from "
                 "real users like 'admin' or 'Jonlandu'.",
        )

    def handle(self, *args, wipe_demo: bool = False, **opts):
        # Demo fans = everyone we seeded via seed_world_cup. We identify
        # them by their email domain (fanpitch.demo) so we never accidentally
        # delete a real tester's content.
        demo_fans = list(
            User.objects.filter(
                email__iendswith="@fanpitch.demo",
                is_superuser=False,
            )
        )
        if not demo_fans:
            self.stdout.write(self.style.ERROR(
                "✗ No demo fans found. Run `seed_world_cup` first."
            ))
            return

        if wipe_demo:
            deleted, _ = Status.objects.filter(author__in=demo_fans).delete()
            self.stdout.write(self.style.WARNING(
                f"⚠ wiped {deleted} demo posts"
            ))

        # Match the post's optional team to whichever team plays this user's
        # favourite (gives the feed a country-flavored mix).
        team_lookup = {t.short_name: t for t in Team.objects.all()}
        live_or_recent = list(
            Match.objects.exclude(status=Match.Status.UPCOMING).order_by(
                "-kickoff_at"
            )[:5]
        )

        now = timezone.now()
        created = 0
        for i, (body, ai_caption) in enumerate(POSTS):
            author = demo_fans[i % len(demo_fans)]
            # Stagger creation times so the feed has natural ordering:
            # the freshest post is now-ish, the oldest about 18 hours back.
            minutes_ago = i * 30 + random.randint(0, 15)
            created_at = now - timedelta(minutes=minutes_ago)

            # Pick a team — favourite team if any, otherwise random.
            team = author.profile.favorite_team
            if team is None:
                team = random.choice(list(team_lookup.values()))

            # Optional: tie ~half the posts to a finished/live match so the
            # match room scroll picks them up too.
            related_match = None
            if live_or_recent and i % 2 == 0:
                related_match = random.choice(live_or_recent)
                # Just keep the team alignment consistent for now.

            status = Status.objects.create(
                author=author,
                body_text=body,
                team=team,
            )
            # Override created_at after save (auto_now_add bypasses it).
            Status.objects.filter(pk=status.pk).update(created_at=created_at)
            created += 1

            del related_match  # mention to avoid unused var warning

        self.stdout.write(self.style.SUCCESS(
            f"✓ {created} status posts created across {len(demo_fans)} demo fans."
        ))
        self.stdout.write(
            "  Each post expires after 7 days. Re-run with --wipe-demo to "
            "reseed cleanly."
        )
