from django.contrib import admin

from .models import Follow, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "country", "points", "level")
    search_fields = ("user__username", "display_name", "country")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "followee", "created_at")
