import os

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import ranker
from .models import Impression, MediaPost, Status as StatusModel
from .serializers import (
    ImpressionBatchSerializer,
    MediaPostSerializer,
    StatusSerializer,
)
from .services.s3_uploads import MAX_UPLOAD_SIZE, presign_put


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author_id == request.user.id


class StatusViewSet(viewsets.ModelViewSet):
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        return (StatusModel.objects
                .filter(expires_at__gt=timezone.now())
                .select_related("author", "author__profile", "media", "team")
                .order_by("-created_at"))


class MediaPostViewSet(viewsets.ModelViewSet):
    serializer_class = MediaPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MediaPost.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def media_upload_url(request):
    """Presigned PUT (S3) or local-upload URL (dev), absolute either way."""
    filename = request.data.get("filename", "upload.bin")
    content_type = request.data.get("content_type", "image/jpeg")
    try:
        payload = presign_put(filename, content_type)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if payload.get("backend") == "local":
        key = payload["key"]
        payload["url"] = request.build_absolute_uri(
            f"/api/v1/media/local-upload/?key={key}"
        )
        payload["cdn_url"] = request.build_absolute_uri(
            f"{settings.MEDIA_URL}{key}"
        )
        payload["method"] = "POST"
        payload["field"] = "file"
    return Response(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def local_upload(request):
    """Local fallback when S3 isn't configured. Path-traversal-safe."""
    key = request.query_params.get("key", "")
    if not key or ".." in key or key.startswith("/"):
        return Response({"detail": "invalid key"},
                        status=status.HTTP_400_BAD_REQUEST)
    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "missing file field"},
                        status=status.HTTP_400_BAD_REQUEST)
    if f.size > MAX_UPLOAD_SIZE:
        return Response({"detail": "file too large"},
                        status=status.HTTP_400_BAD_REQUEST)

    dest = os.path.join(settings.MEDIA_ROOT, key)
    real_dest = os.path.realpath(dest)
    real_root = os.path.realpath(settings.MEDIA_ROOT)
    if not real_dest.startswith(real_root + os.sep):
        return Response({"detail": "invalid path"},
                        status=status.HTTP_400_BAD_REQUEST)

    os.makedirs(os.path.dirname(real_dest), exist_ok=True)
    with open(real_dest, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    return Response(
        {"key": key, "size": f.size, "content_type": f.content_type},
        status=status.HTTP_201_CREATED,
    )


# ---------- TikTok-style feed endpoints ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_statuses(request, user_id: int):
    """Public timeline for a given user — paginated, newest first.

    Used by the clickable profile screen on mobile.
    """
    try:
        limit = min(int(request.query_params.get("limit", 20)), 50)
        offset = max(int(request.query_params.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 20, 0

    qs = (StatusModel.objects
          .filter(author_id=user_id, expires_at__gt=timezone.now())
          .select_related("author", "author__profile", "media", "team")
          .order_by("-created_at"))
    total = qs.count()
    items = list(qs[offset:offset + limit])
    data = StatusSerializer(items, many=True, context={"request": request}).data
    return Response({
        "results": data,
        "count": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def for_you_feed(request):
    """Ranked feed — engagement × recency × personalisation, diversified."""
    try:
        limit = min(int(request.query_params.get("limit", 20)), 50)
        offset = max(int(request.query_params.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 20, 0
    statuses = ranker.for_you(request.user, limit=limit, offset=offset)
    data = StatusSerializer(statuses, many=True, context={"request": request}).data
    return Response({"results": data, "limit": limit, "offset": offset})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def following_feed(request):
    """Strict feed: only authors the user follows + self, newest first."""
    try:
        limit = min(int(request.query_params.get("limit", 20)), 50)
        offset = max(int(request.query_params.get("offset", 0)), 0)
    except ValueError:
        limit, offset = 20, 0
    statuses = ranker.following(request.user, limit=limit, offset=offset)
    data = StatusSerializer(statuses, many=True, context={"request": request}).data
    return Response({"results": data, "limit": limit, "offset": offset})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def impressions_batch(request):
    """
    Bulk-record impressions. Body: {"status_ids":[1,2,3], "dwell_ms":[2100,800,3400]}.

    To prevent gaming the algorithm:
    - cap per request: 50 ids
    - skip any pair (user, status) already logged in the last hour
    """
    ser = ImpressionBatchSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    status_ids = ser.validated_data["status_ids"]
    dwells = ser.validated_data.get("dwell_ms") or [0] * len(status_ids)

    # Anti-gaming: existing impressions for the same (user, status) in last hour
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=1)
    seen = set(Impression.objects
               .filter(user=request.user, status_id__in=status_ids,
                       created_at__gte=cutoff)
               .values_list("status_id", flat=True))

    from collections import Counter

    from django.db.models import F

    from .models import Status as StatusModel

    to_create = [
        Impression(user=request.user, status_id=sid, dwell_ms=int(dwell))
        for sid, dwell in zip(status_ids, dwells)
        if sid not in seen
    ]
    Impression.objects.bulk_create(to_create)
    # bulk_create doesn't fire post_save → bump the denorm counter manually.
    per_status = Counter(imp.status_id for imp in to_create)
    for sid, n in per_status.items():
        StatusModel.objects.filter(pk=sid).update(
            impressions_count=F("impressions_count") + n,
        )
    return Response({"recorded": len(to_create),
                     "skipped": len(status_ids) - len(to_create)})
