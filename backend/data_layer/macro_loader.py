"""
Macro Data Loader - Pure data retrieval from PostgreSQL
No calculations, no aggregations - just raw economic data
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
from core.database import DatabaseManager


class MacroDataLoader:
    """Load macroeconomic data from PostgreSQL"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def load_interest_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load central bank interest rates
        
        Returns:
            DataFrame with columns: date, currency, rate
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT date, currency, rate
            FROM macro_interest_rates
            WHERE currency = ANY(%s)
            AND date BETWEEN %s AND %s
            ORDER BY date, currency
            """
            df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
        
        return df
    
    def load_inflation_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load CPI/inflation data"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT date, currency, inflation_rate
            FROM macro_inflation
            WHERE currency = ANY(%s)
            AND date BETWEEN %s AND %s
            ORDER BY date, currency
            """
            df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
        
        return df
    
    def load_gdp_data(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load GDP growth data"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=730)
        if end_date is None:
            end_date = datetime.now()
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT date, currency, gdp_growth_rate
            FROM macro_gdp
            WHERE currency = ANY(%s)
            AND date BETWEEN %s AND %s
            ORDER BY date, currency
            """
            df = pd.read_sql(query, conn, params=(currencies, start_date, end_date))
        
        return df
