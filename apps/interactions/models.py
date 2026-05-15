from django.conf import settings
from django.db import models


class ReactionTarget(models.TextChoices):
    STATUS = "STATUS"
    MATCH_EVENT = "MATCH_EVENT"
    MEDIA_POST = "MEDIA_POST"
    COMMENT = "COMMENT"
    POLL = "POLL"


class Reaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="reactions")
    target_type = models.CharField(max_length=16, choices=ReactionTarget.choices)
    target_id = models.PositiveBigIntegerField()
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "target_type", "target_id", "emoji")
        indexes = [models.Index(fields=["target_type", "target_id"])]


class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="predictions")
    match = models.ForeignKey("matches.Match", on_delete=models.CASCADE,
                              related_name="predictions")
    home_score = models.IntegerField()
    away_score = models.IntegerField()
    first_scorer_name = models.CharField(max_length=120, blank=True)
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "match")
        indexes = [models.Index(fields=["match", "user"])]


class Poll(models.Model):
    match = models.ForeignKey("matches.Match", null=True, blank=True,
                              on_delete=models.CASCADE, related_name="polls")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="polls")
    question = models.CharField(max_length=240)
    options = models.JSONField(default=list)  # list[str]
    closes_at = models.DateTimeField(null=True, blank=True)
    auto_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="poll_votes")
    option_index = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("poll", "user")


class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="comments")
    target_type = models.CharField(max_length=16, choices=ReactionTarget.choices)
    target_id = models.PositiveBigIntegerField()
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["target_type", "target_id"])]
