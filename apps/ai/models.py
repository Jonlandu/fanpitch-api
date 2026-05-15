from django.conf import settings
from django.db import models


class BedrockCall(models.Model):
    class Kind(models.TextChoices):
        CAPTION = "CAPTION"
        MEME = "MEME"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True, blank=True,
                             on_delete=models.SET_NULL,
                             related_name="bedrock_calls")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    model_id = models.CharField(max_length=120)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    output = models.JSONField(default=dict, blank=True)
    error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
