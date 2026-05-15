from rest_framework.routers import DefaultRouter

from .views import MatchViewSet, TeamViewSet

router = DefaultRouter()
router.register(r"teams", TeamViewSet, basename="team")
router.register(r"matches", MatchViewSet, basename="match")

urlpatterns = router.urls
