"""
Presigned S3 PUT URL generator.

If AWS keys are not configured, returns a local fallback that lets the mobile
app save files to the Django MEDIA_ROOT — handy for offline demos.
"""
from __future__ import annotations

import logging
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

log = logging.getLogger("fanpitch.s3")

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif",
                  "video/mp4", "video/quicktime", "video/webm"}
# 50 MiB — videos need more headroom; lifecycle rule moves to S3-IA after 7d.
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


def _client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        config=Config(signature_version="s3v4"),
    )


def s3_configured() -> bool:
    return bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY
                and settings.S3_BUCKET)


def presign_put(filename: str, content_type: str) -> dict:
    if content_type not in _ALLOWED_TYPES:
        raise ValueError(f"unsupported content-type: {content_type}")
    key = f"uploads/{uuid.uuid4().hex}/{filename}"
    if not s3_configured():
        return {
            "url": f"/api/v1/media/local-upload/?key={key}",
            "key": key,
            "method": "PUT",
            "cdn_url": f"{settings.MEDIA_URL}{key}",
            "expires_in": 0,
            "backend": "local",
        }
    try:
        url = _client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=300,
        )
    except (BotoCoreError, ClientError) as exc:
        log.exception("presign failed: %s", exc)
        raise
    cdn_url = (
        f"https://{settings.CLOUDFRONT_DOMAIN}/{key}"
        if settings.CLOUDFRONT_DOMAIN
        else f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    )
    return {
        "url": url,
        "key": key,
        "method": "PUT",
        "cdn_url": cdn_url,
        "expires_in": 300,
        "backend": "s3",
        "max_size": MAX_UPLOAD_SIZE,
    }
