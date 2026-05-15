from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    MediaPostViewSet, StatusViewSet,
    following_feed, for_you_feed, impressions_batch,
    local_upload, media_upload_url,
)

router = DefaultRouter()
router.register(r"statuses", StatusViewSet, basename="status")
router.register(r"media", MediaPostViewSet, basename="media")

urlpatterns = [
    path("media/upload-url/", media_upload_url, name="media-upload-url"),
    path("media/local-upload/", local_upload, name="media-local-upload"),
    path("feed/for-you/", for_you_feed, name="feed-for-you"),
    path("feed/following/", following_feed, name="feed-following"),
    path("impressions/", impressions_batch, name="impressions-batch"),
] + router.urls
