"""
Thin client over Football-Data.org v4 API.

Free tier: 10 calls/min, today/yesterday matches.
We aggressively cache and gracefully degrade to the simulator if the key is missing
or the call fails.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("fanpitch.football_data")


class FootballDataClient:
    def __init__(self) -> None:
        self.base = settings.FOOTBALL_DATA_BASE_URL.rstrip("/")
        self.api_key = settings.FOOTBALL_DATA_API_KEY

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, *, ttl: int = 60) -> dict | None:
        if not self.configured:
            return None
        cache_key = f"fdo:{path}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = requests.get(
                f"{self.base}{path}",
                headers={"X-Auth-Token": self.api_key},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            cache.set(cache_key, data, ttl)
            return data
        except requests.RequestException as exc:
            log.warning("football-data call failed (%s): %s", path, exc)
            return None

    def matches_today(self) -> list[dict[str, Any]]:
        data = self._get("/matches", ttl=60)
        return (data or {}).get("matches", [])

    def match(self, external_id: str) -> dict | None:
        return self._get(f"/matches/{external_id}", ttl=10)
