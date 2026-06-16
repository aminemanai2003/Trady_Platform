"""
Geopolitical-event collector.

The Geopolitical agent (`signal_layer/geopolitical_agent_v2.py`) fetches
headlines on every signal generation from GDELT/NewsAPI/GNews/RSS, with a
SQLite fallback through `NewsLoader.load_recent_news`. So "refreshing
geopolitics" effectively means topping up that SQLite fallback with the
broader risk/conflict keywords the agent's headline classifier cares about.

This collector calls NewsAPI with a separate keyword set targeted at
geopolitical risk (war, sanctions, central-bank intervention, etc.) and
stores the results in the same `NewsArticle` table the agent reads from.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"

GEOPOLITICAL_KEYWORDS = [
    "war",
    "conflict",
    "sanctions",
    "ceasefire",
    "central bank intervention",
    "tariffs",
    "trade war",
    "geopolitical risk",
    "safe haven",
    "energy crisis",
    "oil price shock",
    "election",
    "political instability",
]

# Currencies the geopolitical agent maps risk-on/risk-off pressure to
RISK_CURRENCIES = {
    "USD": ["dollar", "Federal Reserve", "Treasury", "United States"],
    "EUR": ["euro", "ECB", "European Union", "Eurozone"],
    "JPY": ["yen", "Bank of Japan", "Japan"],
    "GBP": ["pound", "sterling", "Bank of England", "United Kingdom"],
    "CHF": ["franc", "SNB", "Switzerland"],
}


def _detect_currencies(text: str) -> list[str]:
    upper = text.upper()
    found = []
    for code, words in RISK_CURRENCIES.items():
        if any(w.upper() in upper for w in words):
            found.append(code)
    return found


def collect_geopolitical(max_articles: int = 60) -> dict[str, Any]:
    """
    Pull geopolitical-risk headlines from NewsAPI and store them in the same
    NewsArticle table the agents already read from.

    Returns the standard `{inserted, skipped, errors}` shape so the front-end
    status poller can render results consistently.
    """
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        return {
            "inserted": 0,
            "skipped": 0,
            "errors": ["NEWSAPI_KEY missing — set it to enable geopolitical refresh"],
        }

    try:
        import requests
    except ImportError:
        return {"inserted": 0, "skipped": 0, "errors": ["requests not installed"]}

    try:
        from scheduling.models import NewsArticle, IngestionLog
    except Exception as exc:
        return {"inserted": 0, "skipped": 0, "errors": [f"models unavailable: {exc}"]}

    log = IngestionLog.objects.create(source="news", status="running")
    inserted = 0
    skipped = 0
    errors: list[str] = []

    try:
        params = {
            "q": " OR ".join(f'"{kw}"' for kw in GEOPOLITICAL_KEYWORDS[:8]),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(max(int(max_articles), 10), 100),
            "apiKey": api_key,
        }
        resp = requests.get(NEWSAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        articles = resp.json().get("articles", []) or []

        for art in articles:
            title = (art.get("title") or "")[:500]
            if not title or title == "[Removed]":
                skipped += 1
                continue

            published_raw = art.get("publishedAt")
            if not published_raw:
                skipped += 1
                continue
            try:
                published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                skipped += 1
                continue

            content = (art.get("content") or art.get("description") or "")[:2000]
            url = (art.get("url") or "")[:800]
            source = (art.get("source") or {}).get("name", "")[:100]
            full = f"{title} {content}"

            currencies = _detect_currencies(full)
            if not currencies:
                currencies = ["FX"]

            if url and NewsArticle.objects.filter(url=url).exists():
                skipped += 1
                continue
            if NewsArticle.objects.filter(title=title, published_at=published_at).exists():
                skipped += 1
                continue

            NewsArticle.objects.create(
                title=title,
                published_at=published_at,
                content=content,
                source=source,
                url=url,
                currencies=currencies,
                sentiment_score=0.0,  # geopolitical lens is event-based, not sentiment-based
            )
            inserted += 1

        log.records_inserted = inserted
        log.status = "success" if not errors else "partial"
        log.error_message = "; ".join(errors)[:1000]
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        return {"inserted": inserted, "skipped": skipped, "errors": errors}

    except Exception as exc:
        logger.exception("[GEO] fatal error")
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        return {"inserted": inserted, "skipped": skipped, "errors": errors + [str(exc)]}
