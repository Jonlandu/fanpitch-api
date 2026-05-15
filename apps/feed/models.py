from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def one_week_from_now():
    return timezone.now() + timedelta(days=7)


class MediaPost(models.Model):
    class Type(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="media_posts")
    s3_key = models.CharField(max_length=240)
    media_type = models.CharField(max_length=8, choices=Type.choices, default=Type.IMAGE)
    cdn_url = models.URLField(blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    ai_caption = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Status(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="statuses")
    body_text = models.CharField(max_length=280, blank=True)
    media = models.ForeignKey(MediaPost, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="statuses")
    team = models.ForeignKey("matches.Team", null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="statuses")
    expires_at = models.DateTimeField(default=one_week_from_now, db_index=True)
    # Denormalised counters — bumped from signals so feed queries don't aggregate.
    impressions_count = models.IntegerField(default=0)
    reactions_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["-created_at", "expires_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.expires_at > timezone.now()


class Impression(models.Model):
    """
    One row per (user, status) view. Used to compute engagement_rate
    (reactions+comments) / impressions for the for-you ranker.

    The mobile client batches impressions and pushes them via
    POST /api/v1/impressions/ once every 5-10s, max 50 per batch.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name="impressions")
    status = models.ForeignKey(Status, on_delete=models.CASCADE,
                               related_name="impression_logs")
    dwell_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]
        # Same user → same status can happen multiple times, but we cap
        # the bump to once per hour to prevent gaming the algo.
