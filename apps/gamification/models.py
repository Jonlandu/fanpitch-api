from django.conf import settings
from django.db import models


class Badge(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240, blank=True)
    icon_url = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="user_badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")


class PointsEvent(models.Model):
    class Source(models.TextChoices):
        PREDICTION = "PREDICTION"
        POLL_VOTE = "POLL_VOTE"
        REACTION = "REACTION"
        STATUS = "STATUS"
        DAILY = "DAILY"
        REFERRAL = "REFERRAL"
        BADGE = "BADGE"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="points_events")
    source = models.CharField(max_length=20, choices=Source.choices)
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    delta = models.IntegerField()
    note = models.CharField(max_length=140, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
