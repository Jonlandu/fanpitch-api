from django.contrib import admin

from .models import Match, MatchEvent, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "country")
    search_fields = ("name", "short_name", "country")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "home_score", "away_score", "competition")
    list_filter = ("status", "competition")
    search_fields = ("home_team__name", "away_team__name")


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("match", "minute", "type", "team", "player_name")
    list_filter = ("type",)
