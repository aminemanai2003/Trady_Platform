"""
NewsAPI.org collector — fetches financial/forex news and stores in SQLite.
Requires NEWSAPI_KEY in environment or .env file.
Free tier: 100 req/day, 1-month history.
"""
import os
import logging
from datetime import datetime, timezone

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import requests

logger = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

FOREX_KEYWORDS = [
    "forex", "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF",
    "Federal Reserve", "ECB", "interest rate", "currency",
    "exchange rate", "central bank", "inflation",
]

CURRENCY_TAGS = {
    "EUR": ["EUR", "euro", "ECB", "eurozone"],
    "USD": ["USD", "dollar", "Federal Reserve", "Fed"],
    "JPY": ["JPY", "yen", "Bank of Japan", "BOJ"],
    "GBP": ["GBP", "pound", "sterling", "Bank of England", "BOE"],
    "CHF": ["CHF", "franc", "SNB", "Swiss"],
}


def _detect_currencies(text: str):
    """Return list of currency codes mentioned in text."""
    text_upper = text.upper()
    found = []
    for code, keywords in CURRENCY_TAGS.items():
        if any(k.upper() in text_upper for k in keywords):
            found.append(code)
    return found or ["USD"]


def _simple_sentiment(text: str) -> float:
    """Very simple keyword-based sentiment (-1 to 1)."""
    positive = ["rise", "gain", "rally", "strong", "bullish", "surge", "up", "high"]
    negative = ["fall", "drop", "weak", "bearish", "decline", "down", "low", "crash"]
    text_lower = text.lower()
    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def collect_newsapi(max_articles: int = 50) -> dict:
    """
    Fetch news from NewsAPI.org and store in SQLite NewsArticle model.
    Returns {'inserted': int, 'skipped': int, 'error': str|None}
    """
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — skipping NewsAPI collection")
        return {"inserted": 0, "skipped": 0, "error": "NEWSAPI_KEY missing"}

    from scheduling.models import NewsArticle, IngestionLog

    log = IngestionLog.objects.create(source="news")

    try:
        params = {
            "q": " OR ".join(FOREX_KEYWORDS[:6]),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(max_articles, 100),
            "apiKey": NEWSAPI_KEY,
        }
        resp = requests.get(NEWSAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])

        inserted = 0
        skipped = 0

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
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                )
            except ValueError:
                skipped += 1
                continue

            content = (art.get("content") or art.get("description") or "")[:2000]
            source = (art.get("source") or {}).get("name", "")[:100]
            url = (art.get("url") or "")[:800]
            currencies = _detect_currencies(title + " " + content)
            sentiment = _simple_sentiment(title + " " + content)

            _, created = NewsArticle.objects.get_or_create(
                title=title,
                published_at=published_at,
                defaults={
                    "content": content,
                    "source": source,
                    "url": url,
                    "currencies": currencies,
                    "sentiment_score": sentiment,
                },
            )
            if created:
                inserted += 1
            else:
                skipped += 1

        log.records_inserted = inserted
        log.status = "success"
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()

        logger.info(f"[NewsAPI] inserted={inserted} skipped={skipped}")
        return {"inserted": inserted, "skipped": skipped, "error": None}

    except Exception as exc:
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        logger.error(f"[NewsAPI] error: {exc}", exc_info=True)
        return {"inserted": 0, "skipped": 0, "error": str(exc)}
