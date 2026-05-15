from django.contrib import admin

from .models import Comment, Poll, PollVote, Prediction, Reaction


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("user", "target_type", "target_id", "emoji", "created_at")
    list_filter = ("target_type", "emoji")


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "match", "home_score", "away_score", "points_awarded")
    list_filter = ("match",)


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "match", "auto_generated", "closes_at", "created_at")
    list_filter = ("auto_generated",)


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "user", "option_index", "created_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "target_type", "target_id", "body", "created_at")
