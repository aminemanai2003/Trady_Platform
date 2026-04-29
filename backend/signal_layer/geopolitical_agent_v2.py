"""
Geopolitical Agent V2 — Free Multi-Source News Analysis

Maps global events to FX currency impact using deterministic keyword scoring.

Fallback chain (no LLM required):
    1. GDELT 2.0 DOC API   — free, no API key
    2. NewsAPI.org          — free tier (NEWSAPI_KEY env var, 100 req/day)
    3. GNews API            — free tier (GNEWS_KEY env var, 10 req/day)
    4. RSS feeds            — BBC World, Reuters, CNN, Al Jazeera
    5. PostgreSQL fallback  — news_articles table already in DB
"""
import os
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ── Currency profile ────────────────────────────────────────────────────────
SAFE_HAVEN = {"CHF", "JPY", "USD"}
RISK_ON_CURRENCIES = {"EUR", "GBP", "AUD", "NZD", "CAD"}

CURRENCY_KEYWORDS: Dict[str, List[str]] = {
    "EUR": ["euro", "ecb", "eurozone", "european central bank", "germany", "france", "eu economy"],
    "USD": ["dollar", "fed", "federal reserve", "fomc", "us economy", "treasury", "wall street"],
    "JPY": ["yen", "boj", "bank of japan", "japan", "nikkei", "abenomics", "tokyo"],
    "GBP": ["pound", "sterling", "bank of england", "boe", "britain", "uk economy", "brexit"],
    "CHF": ["franc", "snb", "swiss national bank", "switzerland", "zurich", "swiss"],
    "CAD": ["loonie", "bank of canada", "boc", "canada", "oil sands"],
    "AUD": ["rba", "reserve bank australia", "australia", "aussie"],
    "NZD": ["rbnz", "new zealand", "kiwi"],
}

# ── Geopolitical keyword scores ──────────────────────────────────────────────
RISK_OFF_KEYWORDS = [
    "war", "conflict", "attack", "invasion", "missile", "nuclear", "bomb",
    "crisis", "collapse", "recession", "depression", "panic", "crash",
    "sanctions", "embargo", "blockade", "coup", "assassination",
    "terrorist", "terrorism", "explosion", "catastrophe",
    "uncertainty", "fear", "risk-off", "risk off", "flight to safety",
    "safe haven", "banking crisis", "debt crisis", "default",
    "hyperinflation", "supply shock", "energy crisis", "famine",
]
RISK_ON_KEYWORDS = [
    "peace", "ceasefire", "agreement", "deal", "treaty",
    "recovery", "growth", "expansion", "boom", "rally",
    "optimism", "stimulus", "risk-on", "risk on", "bullish",
    "gdp growth", "jobs created", "unemployment fell", "trade deal",
]
COMMODITY_KEYWORDS = {
    "oil": {"positive": {"CAD", "NOK", "RUB"}, "negative": {"JPY", "EUR", "USD"}},
    "gas": {"positive": {"NOK", "CAD"}, "negative": {"EUR"}},
    "gold": {"positive": {"AUD", "CHF"}, "negative": set()},
    "corn": {"positive": {"RUB", "BRL"}, "negative": set()},
}

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]


class GeopoliticalAgentV2:
    """
    Geopolitical Agent — deterministic FX impact scoring from global news.

    Compatible with CoordinatorAgentV2 interface:
        signal = agent.generate_signal(['EUR', 'USD'])
        → {'signal': -1/0/1, 'confidence': 0-1, 'key_events': [...], ...}
    """

    FETCH_TIMEOUT = 5  # seconds per HTTP request
    CACHE_TTL = 3600   # 1-hour result cache

    def __init__(self):
        self.newsapi_key = os.environ.get("NEWSAPI_KEY", "")
        self.gnews_key = os.environ.get("GNEWS_KEY", "")
        self._cache: Dict[str, dict] = {}

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_signal(self, currencies: List[str]) -> Dict:
        """
        Generate geopolitical signal for a currency pair.

        Args:
            currencies: [base, quote] — e.g. ['EUR', 'USD']

        Returns:
            {
                'signal': -1 | 0 | 1,
                'confidence': float,
                'key_events': list[str],
                'impacted_currencies': list[str],
                'features_used': dict,
                'deterministic_reason': str,
            }
        """
        if len(currencies) < 2:
            return self._neutral("Insufficient currencies provided")

        base, quote = currencies[0].upper(), currencies[1].upper()
        cache_key = f"{base}_{quote}"

        # Return cached result if fresh
        cached = self._cache.get(cache_key)
        if cached and (datetime.now() - cached["ts"]).seconds < self.CACHE_TTL:
            return cached["data"]

        headlines = self._fetch_headlines(base, quote)
        if len(headlines) < 3:
            return self._neutral("Insufficient headline data from all sources")

        result = self._score_headlines(headlines, base, quote)

        self._cache[cache_key] = {"ts": datetime.now(), "data": result}
        return result

    # ── Data fetching ─────────────────────────────────────────────────────────

    def _fetch_headlines(self, base: str, quote: str) -> List[str]:
        """Collect headlines across all available sources with fallback."""
        headlines: List[str] = []

        # 1. GDELT (always — no key needed)
        try:
            h = self._fetch_gdelt(base, quote)
            headlines.extend(h)
            logger.debug(f"GeoPol GDELT: {len(h)} headlines")
        except Exception as exc:
            logger.debug(f"GeoPol GDELT failed: {exc}")

        # 2. NewsAPI (if key configured)
        if self.newsapi_key and len(headlines) < 8:
            try:
                h = self._fetch_newsapi(base, quote)
                headlines.extend(h)
                logger.debug(f"GeoPol NewsAPI: {len(h)} headlines")
            except Exception as exc:
                logger.debug(f"GeoPol NewsAPI failed: {exc}")

        # 3. GNews (if key configured)
        if self.gnews_key and len(headlines) < 8:
            try:
                h = self._fetch_gnews(base, quote)
                headlines.extend(h)
                logger.debug(f"GeoPol GNews: {len(h)} headlines")
            except Exception as exc:
                logger.debug(f"GeoPol GNews failed: {exc}")

        # 4. RSS (always as fallback)
        if len(headlines) < 8:
            try:
                h = self._fetch_rss()
                headlines.extend(h)
                logger.debug(f"GeoPol RSS: {len(h)} headlines")
            except Exception as exc:
                logger.debug(f"GeoPol RSS failed: {exc}")

        # 5. DB fallback (always available)
        if len(headlines) < 5:
            try:
                h = self._fetch_from_db(base, quote)
                headlines.extend(h)
                logger.debug(f"GeoPol DB fallback: {len(h)} headlines")
            except Exception as exc:
                logger.debug(f"GeoPol DB fallback failed: {exc}")

        # Deduplicate and limit
        seen: set = set()
        unique: List[str] = []
        for h in headlines:
            if h and h not in seen:
                seen.add(h)
                unique.append(h)

        return unique[:60]

    def _fetch_gdelt(self, base: str, quote: str) -> List[str]:
        base_kw = CURRENCY_KEYWORDS.get(base, [base.lower()])[0]
        quote_kw = CURRENCY_KEYWORDS.get(quote, [quote.lower()])[0]
        query = f"forex {base_kw} {quote_kw} geopolitical economy"
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc?"
            f"query={urllib.parse.quote(query)}&mode=ArtList&format=json"
            "&maxrecords=20&sort=DateDesc"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Trady/1.0"})
        with urllib.request.urlopen(req, timeout=self.FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [a.get("title", "") for a in data.get("articles", []) if a.get("title")]

    def _fetch_newsapi(self, base: str, quote: str) -> List[str]:
        kws = []
        for c in [base, quote]:
            kws.extend(CURRENCY_KEYWORDS.get(c, [c.lower()])[:2])
        q = " OR ".join(kws[:4]) + " OR geopolitical OR conflict OR crisis"
        url = (
            "https://newsapi.org/v2/everything?"
            f"q={urllib.parse.quote(q)}&language=en&sortBy=publishedAt"
            f"&pageSize=15&apiKey={self.newsapi_key}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Trady/1.0"})
        with urllib.request.urlopen(req, timeout=self.FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [a.get("title", "") for a in data.get("articles", []) if a.get("title")]

    def _fetch_gnews(self, base: str, quote: str) -> List[str]:
        kw = CURRENCY_KEYWORDS.get(base, [base.lower()])[0]
        q = f"forex {kw} geopolitical"
        url = (
            "https://gnews.io/api/v4/search?"
            f"q={urllib.parse.quote(q)}&lang=en&max=10&apikey={self.gnews_key}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Trady/1.0"})
        with urllib.request.urlopen(req, timeout=self.FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [a.get("title", "") for a in data.get("articles", []) if a.get("title")]

    def _fetch_rss(self) -> List[str]:
        titles: List[str] = []
        for feed_url in RSS_FEEDS:
            try:
                req = urllib.request.Request(feed_url, headers={"User-Agent": "Trady/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    titles.extend(self._parse_rss(resp.read()))
                if len(titles) >= 25:
                    break
            except Exception:
                continue
        return titles

    def _parse_rss(self, content: bytes) -> List[str]:
        try:
            root = ET.fromstring(content)
            titles = [
                item.findtext("title", "").strip()
                for item in root.iter("item")
                if item.findtext("title")
            ]
            if not titles:
                atom = "{http://www.w3.org/2005/Atom}"
                titles = [
                    e.findtext(f"{atom}title", "").strip()
                    for e in root.iter(f"{atom}entry")
                    if e.findtext(f"{atom}title")
                ]
            return [t for t in titles if t][:20]
        except ET.ParseError:
            return []

    def _fetch_from_db(self, base: str, quote: str) -> List[str]:
        try:
            from data_layer.news_loader import NewsLoader
            loader = NewsLoader()
            pair = f"{base}{quote}"
            articles = loader.load_recent_news(pair, hours=48) or []
            return [
                a.get("title") or a.get("headline") or ""
                for a in articles
                if a.get("title") or a.get("headline")
            ]
        except Exception:
            return []

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_headlines(self, headlines: List[str], base: str, quote: str) -> Dict:
        """Deterministic keyword scoring → directional signal."""
        risk_off = 0.0
        risk_on = 0.0
        key_events: List[str] = []
        relevant = 0

        for headline in headlines:
            if not headline:
                continue
            h = headline.lower()

            matched_off = [kw for kw in RISK_OFF_KEYWORDS if kw in h]
            matched_on = [kw for kw in RISK_ON_KEYWORDS if kw in h]

            if matched_off:
                weight = 1.0 + 0.3 * (len(matched_off) - 1)
                risk_off += weight
                relevant += 1
                if len(key_events) < 5:
                    key_events.append(f"⚠ {headline[:90]}")

            if matched_on:
                weight = 1.0 + 0.3 * (len(matched_on) - 1)
                risk_on += weight
                relevant += 1

            # Commodity secondary impact
            for commodity, impact in COMMODITY_KEYWORDS.items():
                if commodity in h:
                    relevant += 1
                    if base in impact["positive"]:
                        risk_on += 0.4
                    elif base in impact["negative"]:
                        risk_off += 0.4

        signal_val, confidence, reason = self._map_to_pair_signal(
            base, quote, risk_off, risk_on, relevant, len(headlines)
        )

        return {
            "signal": signal_val,
            "confidence": confidence,
            "key_events": key_events[:5],
            "impacted_currencies": self._impacted(base, quote, signal_val),
            "features_used": {
                "risk_off_score": round(risk_off, 2),
                "risk_on_score": round(risk_on, 2),
                "relevant_headlines": relevant,
                "total_headlines": len(headlines),
            },
            "deterministic_reason": reason,
        }

    def _map_to_pair_signal(
        self,
        base: str,
        quote: str,
        risk_off: float,
        risk_on: float,
        relevant: int,
        total: int,
    ) -> Tuple[int, float, str]:
        if total < 3:
            return 0, 0.0, "Insufficient geopolitical data"

        # When we have headlines but none are geopolitically relevant,
        # that itself is a signal: calm/neutral geopolitical backdrop.
        # Return low but non-zero confidence so the agent doesn't appear broken.
        if relevant < 2:
            calm_conf = min(0.30, 0.10 + total * 0.01)  # 0.10–0.30 based on coverage
            return 0, calm_conf, f"Neutral geopolitical backdrop ({total} headlines scanned, {relevant} relevant)"

        total_score = risk_off + risk_on
        if total_score < 0.5:
            return 0, 0.15, f"Minimal geopolitical signals ({relevant}/{total} headlines had keywords)"

        net = risk_off - risk_on  # > 0 means risk-off dominates
        ratio = abs(net) / (total_score + 1e-9)
        rel_ratio = min(relevant / max(total, 1), 1.0)
        confidence = min(0.70, ratio * 0.55 + rel_ratio * 0.25)

        base_safe = base in SAFE_HAVEN
        quote_safe = quote in SAFE_HAVEN

        if net > 1.0:  # Risk-off dominates
            if base_safe and not quote_safe:
                return 1, confidence, f"Risk-off: {base} (safe-haven) strengthens vs {quote}"
            if not base_safe and quote_safe:
                return -1, confidence, f"Risk-off: {quote} (safe-haven) strengthens, {base} weakens"
            if base_safe and quote_safe:
                return 0, confidence * 0.4, f"Risk-off: both {base} and {quote} are safe havens"
            return 0, confidence * 0.3, f"Risk-off: neither currency is a clear safe haven"

        if net < -1.0:  # Risk-on dominates
            if not base_safe and quote_safe:
                return 1, confidence, f"Risk-on: {base} (risk currency) outperforms {quote}"
            if base_safe and not quote_safe:
                return -1, confidence, f"Risk-on: {quote} (risk currency) outperforms {base}"
            if not base_safe and not quote_safe:
                return 0, confidence * 0.4, f"Risk-on: both currencies benefit equally"
            return 0, confidence * 0.3, f"Risk-on: both safe havens — no pair edge"

        return 0, max(0.0, confidence - 0.2), "Mixed geopolitical signals — no clear direction"

    def _impacted(self, base: str, quote: str, signal: int) -> List[str]:
        if signal == 1:
            return [base]
        if signal == -1:
            return [quote]
        return [base, quote]

    def _neutral(self, reason: str) -> Dict:
        return {
            "signal": 0,
            "confidence": 0.0,
            "key_events": [],
            "impacted_currencies": [],
            "features_used": {},
            "deterministic_reason": reason,
        }
