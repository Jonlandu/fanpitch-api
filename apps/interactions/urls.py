from rest_framework.routers import DefaultRouter

from .views import (
    CommentViewSet,
    PollViewSet,
    PredictionViewSet,
    ReactionViewSet,
)

router = DefaultRouter()
router.register(r"reactions", ReactionViewSet, basename="reaction")
router.register(r"predictions", PredictionViewSet, basename="prediction")
router.register(r"polls", PollViewSet, basename="poll")
router.register(r"comments", CommentViewSet, basename="comment")

urlpatterns = router.urls
