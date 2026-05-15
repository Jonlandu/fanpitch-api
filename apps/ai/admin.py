from django.contrib import admin

from .models import BedrockCall


@admin.register(BedrockCall)
class BedrockCallAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "model_id", "success",
                    "input_tokens", "output_tokens", "created_at")
    list_filter = ("kind", "success")
