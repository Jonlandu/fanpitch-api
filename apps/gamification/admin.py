from django.contrib import admin

from .models import Badge, PointsEvent, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")


@admin.register(PointsEvent)
class PointsEventAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "delta", "note", "created_at")
    list_filter = ("source",)
