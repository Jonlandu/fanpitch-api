from django.urls import path

from .views import ai_caption, ai_meme

urlpatterns = [
    path("caption/", ai_caption, name="ai-caption"),
    path("meme/", ai_meme, name="ai-meme"),
]
