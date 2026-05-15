from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
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

# Serve uploaded media in DEBUG / dev mode so the local-upload fallback works
# end-to-end without S3. In production, CloudFront serves the S3 bucket
# instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
