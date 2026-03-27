"""
News Data Loader - Pure data retrieval from PostgreSQL
No sentiment analysis here - just raw news text
"""
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
from core.database import DatabaseManager


class NewsLoader:
    """Load news articles from PostgreSQL"""
    
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
        Load raw news articles
        
        Returns:
            DataFrame with columns: id, timestamp, title, content, source, currencies
            NO SENTIMENT - just raw text
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now()
        
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                try:
                    # Primary schema (mentioned_currencies JSONB)
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
                    # Compatibility schema (currencies TEXT[])
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
            return pd.DataFrame(columns=['id', 'timestamp', 'title', 'content', 'source', 'currencies', 'sentiment_score'])

    def latest_timestamp(self) -> Optional[datetime]:
        """Return the most recent news publication timestamp."""
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = "SELECT MAX(published_at) AS last_ts FROM news_articles"
                df = pd.read_sql(query, conn)
                if df.empty or df.loc[0, 'last_ts'] is None:
                    return None
                return pd.to_datetime(df.loc[0, 'last_ts']).to_pydatetime()
        except Exception:
            return None

    def get_freshness_health(self, freshness_target_minutes: int = 240) -> dict:
        """
        Compute freshness KPIs for news ingestion.

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

            if df.empty:
                return {
                    'status': 'NO_DATA',
                    'last_news_timestamp': None,
                    'age_minutes': None,
                    'articles_last_1h': 0,
                    'articles_last_24h': 0,
                    'freshness_score': 0.0,
                    'target_max_age_minutes': freshness_target_minutes,
                }

            row = df.iloc[0]
            last_ts = row.get('last_ts')
            c1h = int(row.get('c1h', 0) or 0)
            c24h = int(row.get('c24h', 0) or 0)

            if last_ts is None:
                return {
                    'status': 'NO_DATA',
                    'last_news_timestamp': None,
                    'age_minutes': None,
                    'articles_last_1h': c1h,
                    'articles_last_24h': c24h,
                    'freshness_score': 0.0,
                    'target_max_age_minutes': freshness_target_minutes,
                }

            last_ts_dt = pd.to_datetime(last_ts).to_pydatetime().replace(tzinfo=None)
            age_minutes = max((datetime.now() - last_ts_dt).total_seconds() / 60.0, 0.0)

            # Age score in [0,1], where 1 means perfectly fresh and 0 means stale beyond target.
            age_score = max(0.0, 1.0 - (age_minutes / max(float(freshness_target_minutes), 1.0)))
            # Activity score gives signal that feeds are active recently.
            activity_score = min(c24h / 20.0, 1.0)
            freshness_score = round((0.7 * age_score + 0.3 * activity_score) * 100.0, 1)

            status = 'PASS' if age_minutes <= freshness_target_minutes and c24h > 0 else 'WARN'

            return {
                'status': status,
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
