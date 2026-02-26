"""
PHASE 1: News Data Validation & Preprocessing
Deduplication, cleaning, embedding storage
"""
import pandas as pd
import numpy as np
from typing import Dict, List
import re
from difflib import SequenceMatcher

from core.database import DatabaseManager
from core.llm_factory import LLMFactory
from validation.models import ValidationReport, DataQualityMetric


class NewsPreprocessor:
    """Validates and preprocesses news data"""
    
    SIMILARITY_THRESHOLD = 0.85  # For deduplication
    
    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date
        self.embeddings_model = LLMFactory.get_embeddings()
    
    def process(self) -> Dict:
        """Process news: deduplicate, clean, embed"""
        
        # Fetch raw news
        df = self._fetch_news_data()
        
        issues = []
        metrics = {'original_count': len(df)}
        
        # 1. Deduplicate by title similarity
        df_deduplicated = self._deduplicate_by_similarity(df)
        duplicates_removed = len(df) - len(df_deduplicated)
        if duplicates_removed > 0:
            issues.append(f"Removed {duplicates_removed} duplicate news items")
        metrics['duplicates_removed'] = duplicates_removed
        
        # 2. Clean HTML artifacts and boilerplate
        df_cleaned = self._clean_text(df_deduplicated)
        
        # 3. Generate and store embeddings
        df_with_embeddings = self._generate_embeddings(df_cleaned)
        
        # Save cleaned data back to DB
        self._save_cleaned_news(df_with_embeddings)
        
        metrics['final_count'] = len(df_with_embeddings)
        metrics['cleaning_rate'] = duplicates_removed / max(len(df), 1)
        
        # Save report
        self._save_report(len(issues) == 0, issues, metrics)
        
        return {
            'issues': issues,
            'metrics': metrics,
            'processed_count': len(df_with_embeddings)
        }
    
    def _fetch_news_data(self) -> pd.DataFrame:
        """Fetch news from PostgreSQL"""
        query = """
            SELECT 
                id,
                title,
                content,
                published_date,
                source
            FROM news_articles
            WHERE published_date >= %s AND published_date <= %s
            AND processed = FALSE
            ORDER BY published_date DESC
        """
        
        with DatabaseManager.get_postgres_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(self.start_date, self.end_date))
        
        return df
    
    def _deduplicate_by_similarity(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove near-duplicate news by title similarity"""
        if len(df) == 0:
            return df
        
        keep_indices = []
        seen_titles = []
        
        for idx, row in df.iterrows():
            title = row['title']
            is_duplicate = False
            
            # Compare with previously seen titles
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, title.lower(), seen_title.lower()).ratio()
                if similarity >= self.SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep_indices.append(idx)
                seen_titles.append(title)
        
        return df.loc[keep_indices].reset_index(drop=True)
    
    def _clean_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean HTML artifacts and boilerplate"""
        df_clean = df.copy()
        
        for col in ['title', 'content']:
            if col in df_clean.columns:
                # Remove HTML tags
                df_clean[col] = df_clean[col].apply(self._remove_html_tags)
                
                # Remove extra whitespace
                df_clean[col] = df_clean[col].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
                
                # Remove common boilerplate phrases
                df_clean[col] = df_clean[col].apply(self._remove_boilerplate)
        
        return df_clean
    
    @staticmethod
    def _remove_html_tags(text: str) -> str:
        """Remove HTML tags"""
        if pd.isna(text):
            return ""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
    
    @staticmethod
    def _remove_boilerplate(text: str) -> str:
        """Remove common boilerplate phrases"""
        if pd.isna(text):
            return ""
        
        boilerplate_patterns = [
            r'Click here to read more',
            r'Subscribe to our newsletter',
            r'Read the full article',
            r'Copyright \d{4}',
            r'All rights reserved'
        ]
        
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def _generate_embeddings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate embeddings for news content"""
        df_embed = df.copy()
        
        # Combine title and content for embedding
        texts = (df_embed['title'] + " " + df_embed['content'].fillna("")).tolist()
        
        # Generate embeddings in batches
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            embeddings = self.embeddings_model.embed_documents(batch)
            all_embeddings.extend(embeddings)
        
        df_embed['embedding'] = all_embeddings
        
        return df_embed
    
    def _save_cleaned_news(self, df: pd.DataFrame):
        """Save cleaned news and embeddings to PostgreSQL"""
        
        with DatabaseManager.get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                # Convert embedding to PostgreSQL array format
                embedding_str = '{' + ','.join(map(str, row['embedding'])) + '}'
                
                cursor.execute("""
                    UPDATE news_articles
                    SET 
                        title = %s,
                        content = %s,
                        embedding = %s::float[],
                        processed = TRUE
                    WHERE id = %s
                """, (row['title'], row['content'], embedding_str, row['id']))
            
            conn.commit()
    
    def _save_report(self, is_valid: bool, issues: List[str], metrics: Dict):
        """Save validation report"""
        ValidationReport.objects.create(
            report_type=ValidationReport.ReportType.NEWS,
            is_valid=is_valid,
            issues_found=len(issues),
            details={
                'issues': issues,
                'metrics': metrics
            },
            records_checked=metrics.get('original_count', 0),
            duplicate_count=metrics.get('duplicates_removed', 0)
        )
        
        DataQualityMetric.objects.create(
            source="news_data",
            metric_name="deduplication_rate",
            metric_value=metrics.get('cleaning_rate', 0),
            threshold=0.10,
            is_passing=metrics.get('cleaning_rate', 0) <= 0.10
        )
