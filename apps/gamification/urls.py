from django.urls import path

from .views import all_badges, leaderboard, my_badges

urlpatterns = [
    path("leaderboard/", leaderboard, name="leaderboard"),
    path("badges/", all_badges, name="badges"),
    path("badges/me/", my_badges, name="badges-me"),
]
