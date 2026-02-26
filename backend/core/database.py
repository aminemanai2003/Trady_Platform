"""
Database connection managers for PostgreSQL and InfluxDB
"""
import psycopg2
from influxdb_client import InfluxDBClient
from django.conf import settings
from contextlib import contextmanager


class DatabaseManager:
    """Centralized database connection management"""
    
    @staticmethod
    @contextmanager
    def get_postgres_connection():
        """Get PostgreSQL connection"""
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        try:
            yield conn
        finally:
            conn.close()
    
    @staticmethod
    @contextmanager
    def get_influx_client():
        """Get InfluxDB client"""
        client = InfluxDBClient(
            url=settings.INFLUX_URL,
            token=settings.INFLUX_TOKEN,
            org=settings.INFLUX_ORG
        )
        try:
            yield client
        finally:
            client.close()


class TimeSeriesQuery:
    """Helper for time-series queries"""
    
    @staticmethod
    def query_ohlcv(symbol: str, start_time: str, end_time: str, bucket: str = "5m"):
        """Query OHLCV data from InfluxDB"""
        with DatabaseManager.get_influx_client() as client:
            query_api = client.query_api()
            
            query = f'''
            from(bucket: "{settings.INFLUX_BUCKET}")
              |> range(start: {start_time}, stop: {end_time})
              |> filter(fn: (r) => r["_measurement"] == "ohlcv")
              |> filter(fn: (r) => r["symbol"] == "{symbol}")
              |> filter(fn: (r) => r["_field"] == "open" or r["_field"] == "high" or r["_field"] == "low" or r["_field"] == "close" or r["_field"] == "volume")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = query_api.query(query=query)
            return result
