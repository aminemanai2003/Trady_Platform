"""
PHASE 2: Sentiment Features Calculator
LLM-based sentiment classification, entity relevance, time-aligned sentiment
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
import re

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from core.database import DatabaseManager
from core.llm_factory import LLMFactory
from features.models import SentimentFeatures


class SentimentFeaturesCalculator:
    """Calculate sentiment features from news using LLM"""
    
    CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD']
    
    # Sentiment classification prompt
    SENTIMENT_PROMPT = PromptTemplate(
        input_variables=["title", "content"],
        template="""Analyze the sentiment of this financial news article.

Title: {title}
Content: {content}

Classify the sentiment as:
- POSITIVE (bullish, optimistic, good news)
- NEGATIVE (bearish, pessimistic, bad news)
- NEUTRAL (no clear sentiment)

Also rate confidence from 0.0 to 1.0.

Respond in this exact format:
Sentiment: [POSITIVE/NEGATIVE/NEUTRAL]
Confidence: [0.0-1.0]
"""
    )
    
    def __init__(self):
        self.llm = LLMFactory.get_llm()
        self.sentiment_chain = LLMChain(llm=self.llm, prompt=self.SENTIMENT_PROMPT)
    
    def calculate_all(self, start_time: str, end_time: str) -> Dict:
        """Calculate sentiment features for time period"""
        
        # Fetch processed news
        df = self._fetch_news(start_time, end_time)
        
        if len(df) == 0:
            return {'processed': 0}
        
        # Extract sentiment using LLM
        df = self._classify_sentiment(df)
        
        # Extract currency relevance
        df = self._extract_currency_relevance(df)
        
        # Time-align sentiment to price windows
        df = self._time_align_sentiment(df)
        
        # Calculate volume metrics
        df = self._calculate_news_volume(df)
        
        # Save features
        self._save_features(df)
        
        return {
            'processed': len(df),
            'avg_sentiment': df['sentiment_score'].mean(),
            'currencies_mentioned': df['currency_mentioned'].nunique()
        }
    
    def _fetch_news(self, start_time: str, end_time: str) -> pd.DataFrame:
        """Fetch processed news articles"""
        
        query = """
            SELECT 
                id,
                title,
                content,
                published_date,
                source
            FROM news_articles
            WHERE published_date >= %s AND published_date <= %s
            AND processed = TRUE
            AND sentiment_processed = FALSE
            ORDER BY published_date
            LIMIT 1000
        """
        
        with DatabaseManager.get_postgres_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(start_time, end_time))
        
        df['published_date'] = pd.to_datetime(df['published_date'])
        
        return df
    
    def _classify_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify sentiment using LLM"""
        
        sentiments = []
        confidences = []
        
        for _, row in df.iterrows():
            # Truncate content to avoid token limits
            content = row['content'][:500] if pd.notna(row['content']) else ""
            
            try:
                # Get LLM response
                response = self.sentiment_chain.run(
                    title=row['title'],
                    content=content
                )
                
                # Parse response
                sentiment, confidence = self._parse_sentiment_response(response)
                
            except Exception as e:
                print(f"Error classifying sentiment: {e}")
                sentiment = 0.0
                confidence = 0.5
            
            sentiments.append(sentiment)
            confidences.append(confidence)
        
        df['sentiment_score'] = sentiments
        df['confidence'] = confidences
        
        return df
    
    def _parse_sentiment_response(self, response: str) -> tuple:
        """
        Parse LLM sentiment response
        Returns: (sentiment_score, confidence)
        """
        sentiment_score = 0.0
        confidence = 0.5
        
        # Extract sentiment
        if 'POSITIVE' in response.upper():
            sentiment_score = 1.0
        elif 'NEGATIVE' in response.upper():
            sentiment_score = -1.0
        elif 'NEUTRAL' in response.upper():
            sentiment_score = 0.0
        
        # Extract confidence
        confidence_match = re.search(r'Confidence:\s*([0-9.]+)', response)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                confidence = max(0.0, min(1.0, confidence))
            except:
                pass
        
        return sentiment_score, confidence
    
    def _extract_currency_relevance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract which currencies are mentioned and their relevance
        """
        
        # Expand dataframe to have one row per currency mentioned
        expanded_rows = []
        
        for _, row in df.iterrows():
            text = f"{row['title']} {row['content']}".upper()
            
            currencies_found = []
            relevance_scores = []
            
            for currency in self.CURRENCIES:
                # Count mentions
                mentions = text.count(currency)
                
                # Check for currency full name mentions
                currency_names = {
                    'USD': 'DOLLAR',
                    'EUR': 'EURO',
                    'GBP': 'POUND|STERLING',
                    'JPY': 'YEN',
                    'CHF': 'FRANC',
                    'CAD': 'CANADIAN',
                    'AUD': 'AUSTRALIAN',
                    'NZD': 'ZEALAND'
                }
                
                pattern = currency_names.get(currency, currency)
                full_name_matches = len(re.findall(pattern, text))
                
                total_mentions = mentions + full_name_matches
                
                if total_mentions > 0:
                    # Calculate relevance: more mentions = higher relevance
                    # Normalize by article length
                    article_length = len(text)
                    relevance = min(1.0, total_mentions / (article_length / 1000))
                    
                    currencies_found.append(currency)
                    relevance_scores.append(relevance)
            
            # Create row for each currency mentioned
            if len(currencies_found) == 0:
                # If no currency mentioned, skip or assign low relevance
                continue
            
            for currency, relevance in zip(currencies_found, relevance_scores):
                expanded_rows.append({
                    'article_id': row['id'],
                    'timestamp': row['published_date'],
                    'currency_mentioned': currency,
                    'sentiment_score': row['sentiment_score'],
                    'confidence': row['confidence'],
                    'relevance_score': relevance,
                    'source': row['source']
                })
        
        df_expanded = pd.DataFrame(expanded_rows)
        
        return df_expanded
    
    def _time_align_sentiment(self, df: pd.DataFrame, 
                              window: str = '1H') -> pd.DataFrame:
        """
        Time-align sentiment to price windows
        Aggregate sentiment within time windows
        """
        
        if len(df) == 0:
            return df
        
        # Set timestamp as index
        df = df.set_index('timestamp')
        
        # Group by currency and resample
        aligned_rows = []
        
        for currency in df['currency_mentioned'].unique():
            currency_df = df[df['currency_mentioned'] == currency]
            
            # Resample to time window and aggregate
            resampled = currency_df.resample(window).agg({
                'sentiment_score': 'mean',
                'confidence': 'mean',
                'relevance_score': 'mean',
                'article_id': 'count'  # Number of articles in window
            })
            
            resampled = resampled.dropna(subset=['sentiment_score'])
            resampled['currency_mentioned'] = currency
            resampled['source'] = currency_df['source'].iloc[0] if len(currency_df) > 0 else ''
            
            aligned_rows.append(resampled.reset_index())
        
        if aligned_rows:
            df_aligned = pd.concat(aligned_rows, ignore_index=True)
        else:
            df_aligned = pd.DataFrame()
        
        return df_aligned
    
    def _calculate_news_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate news volume metrics (1h, 24h)"""
        
        if len(df) == 0:
            return df
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        volume_1h = []
        volume_24h = []
        
        for i, row in df.iterrows():
            current_time = row['timestamp']
            currency = row['currency_mentioned']
            
            # Count news in last 1h
            time_1h_ago = current_time - timedelta(hours=1)
            count_1h = len(df[
                (df['currency_mentioned'] == currency) &
                (df['timestamp'] >= time_1h_ago) &
                (df['timestamp'] <= current_time)
            ])
            
            # Count news in last 24h
            time_24h_ago = current_time - timedelta(hours=24)
            count_24h = len(df[
                (df['currency_mentioned'] == currency) &
                (df['timestamp'] >= time_24h_ago) &
                (df['timestamp'] <= current_time)
            ])
            
            volume_1h.append(count_1h)
            volume_24h.append(count_24h)
        
        df['news_volume_1h'] = volume_1h
        df['news_volume_24h'] = volume_24h
        
        return df
    
    def _save_features(self, df: pd.DataFrame):
        """Save sentiment features to database"""
        
        if len(df) == 0:
            return
        
        features_to_create = []
        
        for _, row in df.iterrows():
            features_to_create.append(
                SentimentFeatures(
                    timestamp=row['timestamp'],
                    currency_mentioned=row['currency_mentioned'],
                    sentiment_score=row['sentiment_score'],
                    confidence=row['confidence'],
                    relevance_score=row['relevance_score'],
                    news_volume_1h=row.get('news_volume_1h', 0),
                    news_volume_24h=row.get('news_volume_24h', 0),
                    source=row['source'],
                    article_id=row.get('article_id', 0)
                )
            )
        
        # Bulk insert
        SentimentFeatures.objects.bulk_create(
            features_to_create,
            batch_size=1000,
            ignore_conflicts=True
        )
        
        # Mark articles as processed
        article_ids = df['article_id'].unique().tolist()
        
        if article_ids:
            with DatabaseManager.get_postgres_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE news_articles
                    SET sentiment_processed = TRUE
                    WHERE id = ANY(%s)
                """, (article_ids,))
                conn.commit()
