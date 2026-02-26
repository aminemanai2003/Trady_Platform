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
        self.db = DatabaseManager()
    
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
        
        with self.db.get_postgres_connection() as conn:
            if currencies:
                query = """
                SELECT id, published_at as timestamp, title, content, source, currencies
                FROM news_articles
                WHERE published_at BETWEEN %s AND %s
                AND currencies && %s
                ORDER BY published_at DESC
                LIMIT %s
                """
                df = pd.read_sql(query, conn, params=(start_time, end_time, currencies, limit))
            else:
                query = """
                SELECT id, published_at as timestamp, title, content, source, currencies
                FROM news_articles
                WHERE published_at BETWEEN %s AND %s
                ORDER BY published_at DESC
                LIMIT %s
                """
                df = pd.read_sql(query, conn, params=(start_time, end_time, limit))
        
        return df
