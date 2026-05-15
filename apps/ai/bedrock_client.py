"""
Thin Bedrock wrapper.

Behaviour:
- If BEDROCK_ENABLED is False, returns a curated funny fallback so the demo
  works without an AWS bill.
- If True, calls Anthropic Claude on Bedrock (Haiku by default).
- Every call is recorded in BedrockCall for cost monitoring.
"""
from __future__ import annotations

import json
import logging
import random

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from .models import BedrockCall

log = logging.getLogger("fanpitch.bedrock")


FALLBACK_CAPTIONS = [
    "Quand ton gardien sort comme un crabe à marée basse 🦀",
    "Le VAR a vu ce que mes yeux refusent d'admettre 👀",
    "On a perdu mais on a gagné en humour 😅",
    "Cette défense joue le hors-jeu… sans la ligne",
    "Un dribble si élégant qu'il mérite un Oscar 🏆",
]

FALLBACK_MEMES = [
    {"top": "WHEN YOUR DEFENDER PLAYS THE OFFSIDE TRAP",
     "bottom": "BUT FORGETS THE LINE EXISTS"},
    {"top": "ME ON KICKOFF",
     "bottom": "ME AT THE 90TH MINUTE"},
    {"top": "VAR REVIEW IN PROGRESS",
     "bottom": "ENTIRE STADIUM HOLDS ITS BREATH"},
]


def _bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def generate_caption(user, *, match_summary: str = "") -> dict:
    """Return {"caption": str, "backend": "bedrock"|"fallback"}."""
    if not settings.BEDROCK_ENABLED:
        cap = random.choice(FALLBACK_CAPTIONS)
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id="fallback",
            output={"caption": cap}, success=True,
        )
        return {"caption": cap, "backend": "fallback"}

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 80,
        "messages": [{
            "role": "user",
            "content": (
                "Écris UNE seule légende football drôle (max 18 mots), "
                "ton joueur, ambiance fan dans un groupe d'amis. "
                f"Contexte: {match_summary or 'un moment fou du match'}. "
                "Pas de discrimination, pas de cliché plat."
            ),
        }],
    }
    try:
        resp = _bedrock_client().invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        data = json.loads(resp["body"].read())
        text = data["content"][0]["text"].strip()
        usage = data.get("usage", {})
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id=settings.BEDROCK_MODEL_ID,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            output={"caption": text}, success=True,
        )
        return {"caption": text, "backend": "bedrock"}
    except (BotoCoreError, ClientError, KeyError, json.JSONDecodeError) as exc:
        log.exception("bedrock caption failed: %s", exc)
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id=settings.BEDROCK_MODEL_ID,
            success=False, error=str(exc)[:230],
        )
        return {"caption": random.choice(FALLBACK_CAPTIONS), "backend": "fallback"}


def generate_meme(user, *, match_summary: str = "") -> dict:
    if not settings.BEDROCK_ENABLED:
        out = random.choice(FALLBACK_MEMES)
        BedrockCall.objects.create(
            user=user, kind="MEME", model_id="fallback",
            output=out, success=True,
        )
        return {**out, "backend": "fallback"}

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 120,
        "messages": [{
            "role": "user",
            "content": (
                "Write a TWO-PART meme text (TOP and BOTTOM) about this football "
                f"moment: {match_summary or 'a wild match moment'}. "
                "Funny, fan-style, no slurs. Return JSON: "
                '{"top":"...","bottom":"..."} only.'
            ),
        }],
    }
    try:
        resp = _bedrock_client().invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        data = json.loads(resp["body"].read())
        text = data["content"][0]["text"].strip()
        parsed = json.loads(text)
        usage = data.get("usage", {})
        BedrockCall.objects.create(
            user=user, kind="MEME", model_id=settings.BEDROCK_MODEL_ID,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            output=parsed, success=True,
        )
        return {**parsed, "backend": "bedrock"}
    except (BotoCoreError, ClientError, KeyError, json.JSONDecodeError) as exc:
        log.exception("bedrock meme failed: %s", exc)
        out = random.choice(FALLBACK_MEMES)
        BedrockCall.objects.create(
            user=user, kind="MEME", model_id=settings.BEDROCK_MODEL_ID,
            success=False, error=str(exc)[:230],
        )
        return {**out, "backend": "fallback"}
