from django.contrib import admin

from .models import MediaPost, Status


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("author", "body_text", "expires_at", "created_at")
    search_fields = ("author__username", "body_text")


@admin.register(MediaPost)
class MediaPostAdmin(admin.ModelAdmin):
    list_display = ("author", "media_type", "s3_key", "created_at")
