"""
Data Loader Module
Handles loading data from PostgreSQL and InfluxDB
"""

import pandas as pd
import psycopg2
from influxdb_client import InfluxDBClient
from sqlalchemy import create_engine
from loguru import logger
import sys
from typing import Optional, List, Dict
from datetime import datetime, timedelta

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


class DataLoader:
    """Load data from various sources"""
    
    def __init__(self, postgres_config: Dict, influxdb_config: Dict):
        """
        Initialize DataLoader
        
        Args:
            postgres_config: PostgreSQL connection parameters
            influxdb_config: InfluxDB connection parameters
        """
        self.postgres_config = postgres_config
        self.influxdb_config = influxdb_config
        self.pg_engine = None
        self.influx_client = None
        
    def connect_postgres(self):
        """Connect to PostgreSQL"""
        try:
            conn_string = f"postgresql://{self.postgres_config['user']}:{self.postgres_config['password']}@{self.postgres_config['host']}:{self.postgres_config['port']}/{self.postgres_config['database']}"
            self.pg_engine = create_engine(conn_string)
            logger.info(f"✓ Connected to PostgreSQL: {self.postgres_config['database']}")
            return True
        except Exception as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            return False
    
    def connect_influxdb(self):
        """Connect to InfluxDB"""
        try:
            self.influx_client = InfluxDBClient(
                url=self.influxdb_config['url'],
                token=self.influxdb_config['token'],
                org=self.influxdb_config['org']
            )
            logger.info(f"✓ Connected to InfluxDB: {self.influxdb_config['url']}")
            return True
        except Exception as e:
            logger.error(f"✗ InfluxDB connection failed: {e}")
            return False
    
    def load_economic_indicators(self, 
                                 series_ids: Optional[List[str]] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load economic indicators from PostgreSQL
        
        Args:
            series_ids: List of FRED series IDs to load (None = all)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with economic indicators
        """
        if not self.pg_engine:
            self.connect_postgres()
        
        query = "SELECT * FROM economic_indicators WHERE 1=1"
        
        if series_ids:
            series_list = "', '".join(series_ids)
            query += f" AND series_id IN ('{series_list}')"
        
        if start_date:
            query += f" AND date >= '{start_date}'"
        
        if end_date:
            query += f" AND date <= '{end_date}'"
        
        query += " ORDER BY date, series_id"
        
        logger.info("Loading economic indicators from PostgreSQL...")
        df = pd.read_sql(query, self.pg_engine)
        logger.info(f"✓ Loaded {len(df):,} economic indicator records")
        
        return df
    
    def load_news_articles(self,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          sources: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load news articles from PostgreSQL
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sources: List of news sources to filter
            
        Returns:
            DataFrame with news articles
        """
        if not self.pg_engine:
            self.connect_postgres()
        
        query = "SELECT * FROM news_articles WHERE 1=1"
        
        if start_date:
            query += f" AND published_at >= '{start_date}'"
        
        if end_date:
            query += f" AND published_at <= '{end_date}'"
        
        if sources:
            source_list = "', '".join(sources)
            query += f" AND source IN ('{source_list}')"
        
        query += " ORDER BY published_at DESC"
        
        logger.info("Loading news articles from PostgreSQL...")
        df = pd.read_sql(query, self.pg_engine)
        logger.info(f"✓ Loaded {len(df):,} news articles")
        
        return df
    
    def load_ohlc_data(self,
                       symbol: str,
                       timeframe: str,
                       start_date: Optional[str] = None,
                       days_back: int = 365) -> pd.DataFrame:
        """
        Load OHLC price data from InfluxDB
        
        Args:
            symbol: Currency pair (e.g., 'EURUSD')
            timeframe: Timeframe (e.g., '1H', '4H', '1D')
            start_date: Start date (YYYY-MM-DD) or None for days_back
            days_back: Number of days to look back (default 365)
            
        Returns:
            DataFrame with OHLC data
        """
        if not self.influx_client:
            self.connect_influxdb()
        
        if start_date:
            range_str = f'start: {start_date}'
        else:
            range_str = f'start: -{days_back}d'
        
        query = f'''
        from(bucket: "{self.influxdb_config['bucket']}")
          |> range({range_str})
          |> filter(fn: (r) => r["_measurement"] == "forex_prices")
          |> filter(fn: (r) => r["symbol"] == "{symbol}")
          |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        logger.info(f"Loading OHLC data for {symbol} {timeframe}...")
        
        try:
            query_api = self.influx_client.query_api()
            tables = query_api.query(query)
            
            # Convert to DataFrame
            data = []
            for table in tables:
                for record in table.records:
                    data.append({
                        'time': record.get_time(),
                        'open': record.values.get('open'),
                        'high': record.values.get('high'),
                        'low': record.values.get('low'),
                        'close': record.values.get('close'),
                        'volume': record.values.get('volume', 0),
                        'symbol': symbol,
                        'timeframe': timeframe
                    })
            
            df = pd.DataFrame(data)
            
            if len(df) > 0:
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time').reset_index(drop=True)
                logger.info(f"✓ Loaded {len(df):,} OHLC candles for {symbol} {timeframe}")
            else:
                logger.warning(f"⚠ No OHLC data found for {symbol} {timeframe}")
            
            return df
            
        except Exception as e:
            logger.error(f"✗ Error loading OHLC data: {e}")
            return pd.DataFrame()
    
    def get_data_summary(self) -> Dict:
        """
        Get summary of available data
        
        Returns:
            Dictionary with data counts
        """
        if not self.pg_engine:
            self.connect_postgres()
        
        summary = {}
        
        # Economic indicators
        query = "SELECT COUNT(*) as count FROM economic_indicators"
        result = pd.read_sql(query, self.pg_engine)
        summary['economic_indicators'] = int(result.iloc[0]['count'])
        
        # News articles
        query = "SELECT COUNT(*) as count FROM news_articles"
        result = pd.read_sql(query, self.pg_engine)
        summary['news_articles'] = int(result.iloc[0]['count'])
        
        # FRED series detail
        query = "SELECT series_id, COUNT(*) as count FROM economic_indicators GROUP BY series_id"
        result = pd.read_sql(query, self.pg_engine)
        summary['fred_series'] = result.to_dict('records')
        
        return summary
    
    def close(self):
        """Close all connections"""
        if self.pg_engine:
            self.pg_engine.dispose()
            logger.info("PostgreSQL connection closed")
        
        if self.influx_client:
            self.influx_client.close()
            logger.info("InfluxDB connection closed")


if __name__ == '__main__':
    # Test the DataLoader
    from config import POSTGRES_CONFIG, INFLUXDB_CONFIG
    
    loader = DataLoader(POSTGRES_CONFIG, INFLUXDB_CONFIG)
    
    # Test PostgreSQL connection
    loader.connect_postgres()
    
    # Get data summary
    summary = loader.get_data_summary()
    
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print(f"Economic Indicators: {summary['economic_indicators']:,}")
    print(f"News Articles: {summary['news_articles']:,}")
    print("\nFRED Series:")
    for series in summary['fred_series']:
        print(f"  {series['series_id']:15s}: {series['count']:5,} records")
    print("=" * 60)
    
    loader.close()
