from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as static_serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthz(_request):
    return JsonResponse({"status": "ok", "service": "fanpitch"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.matches.urls")),
    path("api/v1/", include("apps.feed.urls")),
    path("api/v1/", include("apps.interactions.urls")),
    path("api/v1/", include("apps.gamification.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Serve uploaded media via Django/daphne. Django's `static()` helper no-ops
# when DEBUG=False, so we register the view directly. Acceptable for the demo
# because the Innovation Sandbox can't provision a public S3 bucket or
# CloudFront, and posts are public user-generated content anyway.
_media_prefix = settings.MEDIA_URL.lstrip("/")
urlpatterns += [
    re_path(
        rf"^{_media_prefix}(?P<path>.*)$",
        static_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
