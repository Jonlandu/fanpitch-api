"""
Maintain denormalised counters on Status so the feed query doesn't need
to aggregate from Reaction / Comment / Impression every render.
"""
from __future__ import annotations

from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.interactions.models import Comment, Reaction

from .models import Impression, Status


@receiver(post_save, sender=Reaction)
def bump_reaction_count(sender, instance: Reaction, created: bool, **kwargs):
    if not created or instance.target_type != "STATUS":
        return
    Status.objects.filter(pk=instance.target_id).update(
        reactions_count=F("reactions_count") + 1,
    )


@receiver(post_save, sender=Comment)
def bump_comment_count(sender, instance: Comment, created: bool, **kwargs):
    if not created or instance.target_type != "STATUS":
        return
    Status.objects.filter(pk=instance.target_id).update(
        comments_count=F("comments_count") + 1,
    )


@receiver(post_save, sender=Impression)
def bump_impression_count(sender, instance: Impression, created: bool, **kwargs):
    if not created:
        return
    Status.objects.filter(pk=instance.status_id).update(
        impressions_count=F("impressions_count") + 1,
    )
