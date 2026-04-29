"""
Macro Data Loader - Pure data retrieval from PostgreSQL
Reads from macro_indicators table (unified schema)
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
from core.database import DatabaseManager


class MacroDataLoader:
    """Load macroeconomic data from PostgreSQL macro_indicators table"""
    
    def __init__(self):
        pass

    def latest_timestamp(self, currencies: Optional[List[str]] = None) -> Optional[datetime]:
        """Return the latest macro data timestamp (best of PostgreSQL and SQLite)."""
        pg_ts = None
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                try:
                    if currencies:
                        query = """
                        SELECT MAX(date) AS last_ts
                        FROM macro_indicators
                        WHERE currency = ANY(%s)
                        """
                        df = pd.read_sql(query, conn, params=(currencies,))
                    else:
                        query = "SELECT MAX(date) AS last_ts FROM macro_indicators"
                        df = pd.read_sql(query, conn)
                except Exception:
                    query = "SELECT MAX(date) AS last_ts FROM economic_indicators"
                    df = pd.read_sql(query, conn)

                if not df.empty and df.loc[0, 'last_ts'] is not None:
                    pg_ts = pd.to_datetime(df.loc[0, 'last_ts']).to_pydatetime().replace(tzinfo=None)
        except Exception:
            pass

        sqlite_ts = self._sqlite_latest_timestamp()

        # Return the freshest timestamp from either source
        if pg_ts and sqlite_ts:
            return max(pg_ts, sqlite_ts)
        return pg_ts or sqlite_ts

    def _sqlite_latest_timestamp(self) -> Optional[datetime]:
        """Read latest macro timestamp from SQLite MacroIndicator model."""
        try:
            from scheduling.models import MacroIndicator
            latest = MacroIndicator.objects.order_by('-date').values_list('date', flat=True).first()
            if latest is None:
                return None
            return datetime(latest.year, latest.month, latest.day)
        except Exception:
            return None
    
    def load_interest_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load central bank interest rates from macro_indicators
        
        Returns:
            DataFrame with columns: date, currency, rate
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = """
                SELECT date, currency, value as rate
                FROM macro_indicators
                WHERE indicator_name = 'interest_rate'
                AND currency = ANY(%s)
                AND date BETWEEN %s AND %s
                ORDER BY date, currency
                """
                df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
            return df
        except Exception:
            return pd.DataFrame(columns=['date', 'currency', 'rate'])
    
    def load_inflation_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load CPI/inflation data from macro_indicators"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = """
                SELECT date, currency, value as inflation_rate
                FROM macro_indicators
                WHERE indicator_name = 'inflation_rate'
                AND currency = ANY(%s)
                AND date BETWEEN %s AND %s
                ORDER BY date, currency
                """
                df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
            return df
        except Exception:
            return pd.DataFrame(columns=['date', 'currency', 'inflation_rate'])
    
    def load_gdp_data(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load GDP growth data from macro_indicators"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=730)
        if end_date is None:
            end_date = datetime.now()
        
        try:
            with DatabaseManager.get_postgres_connection() as conn:
                query = """
                SELECT date, currency, value as gdp_growth_rate
                FROM macro_indicators
                WHERE indicator_name = 'gdp_growth'
                AND currency = ANY(%s)
                AND date BETWEEN %s AND %s
                ORDER BY date, currency
                """
                df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
            return df
        except Exception:
            return pd.DataFrame(columns=['date', 'currency', 'gdp_growth_rate'])
