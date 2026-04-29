"""
News Data Loader - Retrieves news from PostgreSQL *and* SQLite,
returning whichever source has fresher data.
"""
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import pandas as pd
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

EMPTY_NEWS_COLUMNS = ['id', 'timestamp', 'title', 'content', 'source', 'currencies', 'sentiment_score']


class NewsLoader:
    """Load news articles from PostgreSQL and/or SQLite"""

    def __init__(self):
        pass

    def load_news(
        self,
        currencies: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Load raw news articles from the freshest available source.

        Checks both PostgreSQL and SQLite, returns whichever has more
        recent data. Collectors write to SQLite; PG may have stale data.

        Returns:
            DataFrame with columns: id, timestamp, title, content, source, currencies, sentiment_score
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now()

        pg_df = self._load_news_pg(currencies, start_time, end_time, limit)
        sqlite_df = self._load_news_sqlite(currencies, start_time, end_time, limit)

        # Return whichever source has fresher data
        pg_max = pd.to_datetime(pg_df['timestamp']).max() if not pg_df.empty else pd.NaT
        sq_max = pd.to_datetime(sqlite_df['timestamp']).max() if not sqlite_df.empty else pd.NaT

        if pg_df.empty and sqlite_df.empty:
            return pd.DataFrame(columns=EMPTY_NEWS_COLUMNS)
        if sqlite_df.empty:
            return pg_df
        if pg_df.empty:
            return sqlite_df

        # Both have data — return the one with the most recent article
        if pd.notna(sq_max) and (pd.isna(pg_max) or sq_max > pg_max):
            logger.debug(f"NewsLoader: using SQLite ({len(sqlite_df)} articles, newest {sq_max})")
            return sqlite_df
        logger.debug(f"NewsLoader: using PostgreSQL ({len(pg_df)} articles, newest {pg_max})")
        return pg_df

    def _load_news_pg(
        self,
        currencies: Optional[List[str]],
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> pd.DataFrame:
        """Load news from PostgreSQL."""
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                try:
                    if currencies:
                        query = """
                        SELECT id, published_at as timestamp, title, content, source,
                               mentioned_currencies as currencies, sentiment_score
                        FROM news_articles
                        WHERE published_at BETWEEN %s AND %s
                        AND mentioned_currencies ?| %s
                        ORDER BY published_at DESC
                        LIMIT %s
                        """
                        return pd.read_sql(query, conn, params=(start_time, end_time, currencies, limit))
                    query = """
                    SELECT id, published_at as timestamp, title, content, source,
                           mentioned_currencies as currencies, sentiment_score
                    FROM news_articles
                    WHERE published_at BETWEEN %s AND %s
                    ORDER BY published_at DESC
                    LIMIT %s
                    """
                    return pd.read_sql(query, conn, params=(start_time, end_time, limit))
                except Exception:
                    if currencies:
                        query = """
                        SELECT id, published_at as timestamp, title, content, source,
                               currencies as currencies, sentiment_score
                        FROM news_articles
                        WHERE published_at BETWEEN %s AND %s
                        AND currencies && %s
                        ORDER BY published_at DESC
                        LIMIT %s
                        """
                        return pd.read_sql(query, conn, params=(start_time, end_time, currencies, limit))
                    query = """
                    SELECT id, published_at as timestamp, title, content, source,
                           currencies as currencies, sentiment_score
                    FROM news_articles
                    WHERE published_at BETWEEN %s AND %s
                    ORDER BY published_at DESC
                    LIMIT %s
                    """
                    return pd.read_sql(query, conn, params=(start_time, end_time, limit))
        except Exception:
            return pd.DataFrame(columns=EMPTY_NEWS_COLUMNS)

    def _load_news_sqlite(
        self,
        currencies: Optional[List[str]],
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> pd.DataFrame:
        """Load news from SQLite via Django ORM (where collectors write)."""
        try:
            from scheduling.models import NewsArticle
            from django.utils import timezone as dj_tz

            qs = NewsArticle.objects.filter(
                published_at__gte=start_time,
                published_at__lte=end_time,
            ).order_by('-published_at')

            # Filter by currencies if provided.
            # JSONField __contains is not supported on SQLite, so we
            # filter in Python after fetching a broader set.
            if currencies:
                currency_set = {c.upper() for c in currencies}
                all_rows = list(
                    qs[:limit * 3].values('id', 'published_at', 'title', 'content', 'source', 'currencies', 'sentiment_score')
                )
                filtered = [
                    r for r in all_rows
                    if isinstance(r.get('currencies'), list) and currency_set & {c.upper() for c in r['currencies']}
                ]
                # If currency filter yields nothing, fall back to all articles
                if not filtered:
                    filtered = all_rows[:limit]
                else:
                    filtered = filtered[:limit]

                if not filtered:
                    return pd.DataFrame(columns=EMPTY_NEWS_COLUMNS)
                df = pd.DataFrame(filtered)
                df.rename(columns={'published_at': 'timestamp'}, inplace=True)
                return df

            rows = list(
                qs[:limit].values('id', 'published_at', 'title', 'content', 'source', 'currencies', 'sentiment_score')
            )
            if not rows:
                return pd.DataFrame(columns=EMPTY_NEWS_COLUMNS)

            df = pd.DataFrame(rows)
            df.rename(columns={'published_at': 'timestamp'}, inplace=True)
            return df
        except Exception as exc:
            logger.debug(f"SQLite news load failed: {exc}")
            return pd.DataFrame(columns=EMPTY_NEWS_COLUMNS)

    def latest_timestamp(self) -> Optional[datetime]:
        """Return the most recent news publication timestamp (best of PostgreSQL and SQLite)."""
        pg_ts = None
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = "SELECT MAX(published_at) AS last_ts FROM news_articles"
                df = pd.read_sql(query, conn)
                if not df.empty and df.loc[0, 'last_ts'] is not None:
                    pg_ts = pd.to_datetime(df.loc[0, 'last_ts']).to_pydatetime()
                    if pg_ts.tzinfo:
                        pg_ts = pg_ts.replace(tzinfo=None)
        except Exception:
            pass

        sqlite_ts = self._sqlite_latest_timestamp()

        # Return the freshest timestamp from either source
        if pg_ts and sqlite_ts:
            return max(pg_ts, sqlite_ts)
        return pg_ts or sqlite_ts

    def _sqlite_latest_timestamp(self) -> Optional[datetime]:
        """Read latest news timestamp from SQLite NewsArticle model."""
        try:
            from scheduling.models import NewsArticle
            latest = NewsArticle.objects.order_by('-published_at').values_list('published_at', flat=True).first()
            if latest is None:
                return None
            return latest.replace(tzinfo=None) if latest.tzinfo else latest
        except Exception:
            return None

    def latest_transfer_delay_minutes(self) -> float:
        """
        Estimate ingestion transfer delay for the latest news article.

        Transfer delay = max(fetched_at - published_at, 0).
        Checks SQLite first (where collectors write), falls back to PostgreSQL.
        """
        # Try SQLite first (primary data source)
        try:
            from scheduling.models import NewsArticle
            latest = NewsArticle.objects.filter(
                published_at__isnull=False,
                fetched_at__isnull=False,
            ).order_by('-published_at').values('published_at', 'fetched_at').first()
            if latest:
                pub = latest['published_at']
                fetched = latest['fetched_at']
                if pub.tzinfo:
                    pub = pub.replace(tzinfo=None)
                if fetched.tzinfo:
                    fetched = fetched.replace(tzinfo=None)
                delay = max((fetched - pub).total_seconds() / 60.0, 0.0)
                return round(delay, 2)
        except Exception:
            pass

        # Fallback: PostgreSQL
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                col_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'news_articles'
                  AND column_name IN ('updated_at', 'created_at', 'scraped_at')
                """
                cols_df = pd.read_sql(col_query, conn)
                available = set(cols_df['column_name'].tolist()) if not cols_df.empty else set()
                ingestion_col = next((c for c in ('updated_at', 'created_at', 'scraped_at') if c in available), None)
                if ingestion_col is None:
                    return 0.0
                delay_query = f"""
                SELECT published_at, {ingestion_col} AS ingested_at
                FROM news_articles
                WHERE published_at IS NOT NULL AND {ingestion_col} IS NOT NULL
                ORDER BY published_at DESC LIMIT 1
                """
                df = pd.read_sql(delay_query, conn)
            if df.empty:
                return 0.0
            published_at = pd.to_datetime(df.loc[0, 'published_at']).to_pydatetime().replace(tzinfo=None)
            ingested_at = pd.to_datetime(df.loc[0, 'ingested_at']).to_pydatetime().replace(tzinfo=None)
            return round(max((ingested_at - published_at).total_seconds() / 60.0, 0.0), 2)
        except Exception:
            return 0.0

    def get_freshness_health(self, freshness_target_minutes: int = 240) -> dict:
        """
        Compute freshness KPIs for news ingestion.

        Checks BOTH PostgreSQL and SQLite and returns whichever is fresher.
        Collectors write to SQLite; PostgreSQL may have stale data from an
        older Docker setup, so we must compare rather than blindly trust PG.

        Returns:
            {
                'status': 'PASS'|'WARN'|'NO_DATA',
                'last_news_timestamp': str|None,
                'age_minutes': float|None,
                'articles_last_1h': int,
                'articles_last_24h': int,
                'freshness_score': float,
                'target_max_age_minutes': int
            }
        """
        # Get freshness from SQLite (primary — collectors write here)
        sqlite_result = self._sqlite_freshness_health(freshness_target_minutes)

        # Try PostgreSQL too and pick the fresher one
        pg_result = None
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = """
                SELECT
                    MAX(published_at) AS last_ts,
                    COUNT(*) FILTER (WHERE published_at >= NOW() - INTERVAL '1 hour') AS c1h,
                    COUNT(*) FILTER (WHERE published_at >= NOW() - INTERVAL '24 hours') AS c24h
                FROM news_articles
                """
                df = pd.read_sql(query, conn)

            if not df.empty:
                row = df.iloc[0]
                last_ts = row.get('last_ts')
                if last_ts is not None:
                    last_ts_dt = pd.to_datetime(last_ts).to_pydatetime().replace(tzinfo=None)
                    c1h = int(row.get('c1h', 0) or 0)
                    c24h = int(row.get('c24h', 0) or 0)
                    age_minutes = max((datetime.now() - last_ts_dt).total_seconds() / 60.0, 0.0)
                    age_score = max(0.0, 1.0 - (age_minutes / max(float(freshness_target_minutes), 1.0)))
                    activity_score = min(c24h / 20.0, 1.0)
                    freshness_score = round((0.7 * age_score + 0.3 * activity_score) * 100.0, 1)
                    status = 'PASS' if age_minutes <= freshness_target_minutes and c24h > 0 else 'WARN'
                    pg_result = {
                        'status': status,
                        'last_news_timestamp': last_ts_dt.isoformat(),
                        'age_minutes': round(age_minutes, 1),
                        'articles_last_1h': c1h,
                        'articles_last_24h': c24h,
                        'freshness_score': freshness_score,
                        'target_max_age_minutes': freshness_target_minutes,
                    }
        except Exception:
            pass

        # Return the fresher result (higher freshness_score wins)
        if pg_result and pg_result.get('freshness_score', 0) > sqlite_result.get('freshness_score', 0):
            return pg_result
        return sqlite_result

    def _sqlite_freshness_health(self, freshness_target_minutes: int = 240) -> dict:
        """Compute freshness from SQLite NewsArticle when PostgreSQL is unavailable."""
        try:
            from scheduling.models import NewsArticle
            from django.utils import timezone as dj_tz

            now = datetime.now()
            cutoff_1h = now - timedelta(hours=1)
            cutoff_24h = now - timedelta(hours=24)
            cutoff_48h = now - timedelta(hours=48)

            latest = NewsArticle.objects.order_by('-published_at').values_list('published_at', flat=True).first()
            c1h = NewsArticle.objects.filter(published_at__gte=cutoff_1h).count()
            c24h = NewsArticle.objects.filter(published_at__gte=cutoff_24h).count()
            c48h = NewsArticle.objects.filter(published_at__gte=cutoff_48h).count()

            if latest is None:
                return {
                    'status': 'NO_DATA',
                    'last_news_timestamp': None,
                    'age_minutes': None,
                    'articles_last_1h': 0,
                    'articles_last_24h': 0,
                    'freshness_score': 0.0,
                    'target_max_age_minutes': freshness_target_minutes,
                }

            last_ts_dt = latest.replace(tzinfo=None) if latest.tzinfo else latest
            age_minutes = max((now - last_ts_dt).total_seconds() / 60.0, 0.0)
            age_score = max(0.0, 1.0 - (age_minutes / max(float(freshness_target_minutes), 1.0)))
            activity_score = min(c48h / 20.0, 1.0)  # 48h window — robust for weekends
            freshness_score = round((0.7 * age_score + 0.3 * activity_score) * 100.0, 1)
            health_status = 'PASS' if age_minutes <= freshness_target_minutes and c48h > 0 else 'WARN'

            return {
                'status': health_status,
                'last_news_timestamp': last_ts_dt.isoformat(),
                'age_minutes': round(age_minutes, 1),
                'articles_last_1h': c1h,
                'articles_last_24h': c24h,
                'freshness_score': freshness_score,
                'target_max_age_minutes': freshness_target_minutes,
            }
        except Exception:
            return {
                'status': 'WARN',
                'last_news_timestamp': None,
                'age_minutes': None,
                'articles_last_1h': 0,
                'articles_last_24h': 0,
                'freshness_score': 0.0,
                'target_max_age_minutes': freshness_target_minutes,
            }