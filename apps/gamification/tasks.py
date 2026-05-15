from celery import shared_task
from django.db import transaction

from apps.interactions.models import Prediction
from apps.matches.models import Match

from .services import check_badges_for, grant_points


@shared_task
def score_match_predictions(match_id: int) -> dict:
    """
    Scoring rules:
      +50  exact score
      +20  correct winner (not exact)
      +10  correct goal difference (not exact, not winner — rare)
    """
    match = Match.objects.get(pk=match_id)
    h, a = match.home_score, match.away_score
    awarded = {"exact": 0, "winner": 0, "diff": 0}
    with transaction.atomic():
        qs = (Prediction.objects
              .select_for_update()
              .filter(match=match, points_awarded=0))
        for p in qs:
            delta = 0
            if p.home_score == h and p.away_score == a:
                delta, awarded["exact"] = 50, awarded["exact"] + 1
            elif ((p.home_score > p.away_score and h > a) or
                  (p.home_score < p.away_score and h < a) or
                  (p.home_score == p.away_score and h == a)):
                delta, awarded["winner"] = 20, awarded["winner"] + 1
            elif (p.home_score - p.away_score) == (h - a):
                delta, awarded["diff"] = 10, awarded["diff"] + 1
            if delta:
                p.points_awarded = delta
                p.save(update_fields=["points_awarded"])
                grant_points(p.user, "PREDICTION", source_id=p.id,
                             delta=delta, note=f"match {match_id}")
                check_badges_for(p.user)
    return awarded
