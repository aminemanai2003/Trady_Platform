"""
Database connection managers for PostgreSQL and InfluxDB
"""
import time
import psycopg2
from influxdb_client import InfluxDBClient
from django.conf import settings
from contextlib import contextmanager

# ── Circuit-breaker state (module-level, shared across all calls) ──────────
_influx_unavailable_until: float = 0.0   # epoch seconds
_influx_circuit_open_seconds: int = 60   # back-off window

_postgres_unavailable_until: float = 0.0
_postgres_circuit_open_seconds: int = 30


class DatabaseManager:
    """Centralized database connection management"""

    @staticmethod
    @contextmanager
    def get_postgres_connection():
        """Get PostgreSQL connection — raises immediately if circuit is open."""
        global _postgres_unavailable_until
        if time.time() < _postgres_unavailable_until:
            raise ConnectionError("PostgreSQL circuit open — skipping connection attempt")
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                connect_timeout=3,  # 3s max — fall back to SQLite quickly
            )
        except Exception:
            _postgres_unavailable_until = time.time() + _postgres_circuit_open_seconds
            raise
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    @contextmanager
    def get_influx_client():
        """Get InfluxDB client — raises immediately if circuit is open."""
        global _influx_unavailable_until
        if time.time() < _influx_unavailable_until:
            raise ConnectionError("InfluxDB circuit open — skipping connection attempt")
        client = InfluxDBClient(
            url=settings.INFLUX_URL,
            token=settings.INFLUX_TOKEN,
            org=settings.INFLUX_ORG,
            timeout=1_000,  # 1 s — fail fast when InfluxDB is unavailable
        )
        try:
            yield client
        except Exception:
            _influx_unavailable_until = time.time() + _influx_circuit_open_seconds
            client.close()
            raise
        else:
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
