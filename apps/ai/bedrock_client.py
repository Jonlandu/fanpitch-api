"""
Thin Bedrock wrapper.

Behaviour:
- If BEDROCK_ENABLED is False, returns a curated funny fallback so the demo
  works without an AWS bill.
- If True, calls Anthropic Claude on Bedrock (Haiku by default).
- Every call is recorded in BedrockCall for cost monitoring.

Languages supported by generate_caption: French, Lingala, Swahili, English.
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


# Per-language fallbacks so the demo works even without Bedrock credentials.
FALLBACK_CAPTIONS: dict[str, list[str]] = {
    "fr": [
        "Quand ton gardien sort comme un crabe à marée basse 🦀",
        "Le VAR a vu ce que mes yeux refusent d'admettre 👀",
        "On a perdu mais on a gagné en humour 😅",
        "Cette défense joue le hors-jeu… sans la ligne",
        "Un dribble si élégant qu'il mérite un Oscar 🏆",
    ],
    "ln": [  # Lingala — Kinshasa
        "Goal oyo, ata mama na ngai akoki kobeta yango 😂",
        "Equipe oyo ezali ko sambela liboso ya match 🙏",
        "Soki ngai na zali coach, na sukisa match na minute ya 30 ⚽",
    ],
    "sw": [  # Swahili — Afrique de l'Est
        "Goli kama hii, hata mama yangu angepiga bora 😆",
        "Hii timu inacheza kama wanasubiri pizza kufika 🍕",
        "VAR imegundua kuwa tumelala wakati wa mchezo 😴",
    ],
    "en": [
        "When your keeper rushes out like a confused tourist 🧳",
        "VAR saw something my eyes refuse to admit 👀",
        "Lost the match, won the meme 😅",
        "That defence is playing offside… without the line",
    ],
}

LANG_NAME: dict[str, str] = {
    "fr": "français",
    "ln": "lingala (la langue parlée à Kinshasa, RDC)",
    "sw": "swahili (Afrique de l'Est)",
    "en": "english",
}


FALLBACK_MEMES = [
    {"top": "WHEN YOUR DEFENDER PLAYS THE OFFSIDE TRAP",
     "bottom": "BUT FORGETS THE LINE EXISTS"},
    {"top": "ME ON KICKOFF",
     "bottom": "ME AT THE 90TH MINUTE"},
    {"top": "VAR REVIEW IN PROGRESS",
     "bottom": "ENTIRE STADIUM HOLDS ITS BREATH"},
]


def _normalize_lang(lang: str | None) -> str:
    """Coerce an incoming lang string to one of our supported codes."""
    if not lang:
        return "fr"
    code = lang.strip().lower()[:2]
    return code if code in FALLBACK_CAPTIONS else "fr"


def _bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def generate_caption(
    user, *, match_summary: str = "", lang: str = "fr", user_brief: str = ""
) -> dict:
    """Return {"caption": str, "backend": "bedrock"|"fallback", "lang": str}.

    Args:
        user: the requesting user (for BedrockCall accounting).
        match_summary: structured context like "POR 2-1 COD (LIVE)".
        lang: target language code — fr | ln | sw | en. Defaults to fr.
        user_brief: free-form text the user typed/dictated describing the
            vibe they want — e.g. "a fan crying because Mbappé missed".
    """
    lang = _normalize_lang(lang)

    if not settings.BEDROCK_ENABLED:
        cap = random.choice(FALLBACK_CAPTIONS[lang])
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id="fallback",
            output={"caption": cap, "lang": lang}, success=True,
        )
        return {"caption": cap, "backend": "fallback", "lang": lang}

    prompt = (
        f"Écris UNE seule légende football drôle (max 20 mots) en {LANG_NAME[lang]}. "
        f"Style: ton supporter dans un groupe WhatsApp, avec emojis. "
        f"Contexte du match: {match_summary or 'un moment fou du match'}. "
    )
    if user_brief:
        prompt += f"Le fan veut illustrer ce moment: {user_brief}. "
    prompt += (
        "Règles: pas de propos haineux, pas d'insultes, pas de personnes réelles "
        "identifiables (politiciens, célébrités). Renvoie SEULEMENT la légende, "
        "sans guillemets ni explication."
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = _bedrock_client().invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        data = json.loads(resp["body"].read())
        text = data["content"][0]["text"].strip().strip('"').strip()
        usage = data.get("usage", {})
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id=settings.BEDROCK_MODEL_ID,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            output={"caption": text, "lang": lang}, success=True,
        )
        return {"caption": text, "backend": "bedrock", "lang": lang}
    except (BotoCoreError, ClientError, KeyError, json.JSONDecodeError) as exc:
        log.exception("bedrock caption failed: %s", exc)
        BedrockCall.objects.create(
            user=user, kind="CAPTION", model_id=settings.BEDROCK_MODEL_ID,
            success=False, error=str(exc)[:230],
        )
        return {
            "caption": random.choice(FALLBACK_CAPTIONS[lang]),
            "backend": "fallback",
            "lang": lang,
        }


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
