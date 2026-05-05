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
            if not df.empty:
                return df
        except Exception:
            pass

        # Fallback: read from SQLite (FRED data stored by the scheduler)
        return self._sqlite_load_interest_rates(currencies, start_date, end_date)

    # Maps FRED series_id → (currency, indicator_name used in macro_indicators)
    _RATE_SERIES = {
        'FEDFUNDS': 'USD',
        'ECBDFR':   'EUR',
        'SONIA':    'GBP',
        'SNBPRA':   'CHF',
        'IRSTCI01JPM156N': 'JPY',
    }

    def _sqlite_load_interest_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Read central-bank rates from the SQLite MacroIndicator table."""
        try:
            from scheduling.models import MacroIndicator
            relevant = [sid for sid, cur in self._RATE_SERIES.items() if cur in currencies]
            if not relevant:
                return pd.DataFrame(columns=['date', 'currency', 'rate'])
            qs = MacroIndicator.objects.filter(series_id__in=relevant)
            if start_date:
                qs = qs.filter(date__gte=start_date.date() if hasattr(start_date, 'date') else start_date)
            if end_date:
                qs = qs.filter(date__lte=end_date.date() if hasattr(end_date, 'date') else end_date)
            rows = qs.values('date', 'series_id', 'value').order_by('date')
            if not rows:
                return pd.DataFrame(columns=['date', 'currency', 'rate'])
            df = pd.DataFrame(list(rows))
            df['currency'] = df['series_id'].map(self._RATE_SERIES)
            df = df.rename(columns={'value': 'rate'})[['date', 'currency', 'rate']]
            df = df[df['currency'].isin(currencies)].dropna(subset=['rate'])
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values(['date', 'currency']).reset_index(drop=True)
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
            if not df.empty:
                return df
        except Exception:
            pass

        # Fallback: read from SQLite (FRED data stored by the scheduler)
        return self._sqlite_load_inflation_rates(currencies, start_date, end_date)

    # Maps FRED series_id → currency for CPI/inflation
    _CPI_SERIES = {
        'CPIAUCSL': 'USD',
        'CP0000EZ19M086NEST': 'EUR',
        'GBRCPIALLMINMEI':    'GBP',
        'CHECPIALLMINMEI':    'CHF',
        'JPNCPIALLMINMEI':    'JPY',
    }

    def _sqlite_load_inflation_rates(
        self,
        currencies: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Read CPI/inflation data from the SQLite MacroIndicator table.

        CPIAUCSL is a price-level index (base 1982-84=100), NOT a percentage.
        We convert it to a YoY % change so the inflation differential is
        expressed in the same units as interest rates (percentage points).
        """
        try:
            from scheduling.models import MacroIndicator
            relevant = [sid for sid, cur in self._CPI_SERIES.items() if cur in currencies]
            if not relevant:
                return pd.DataFrame(columns=['date', 'currency', 'inflation_rate'])

            # Fetch 13+ months of data so we can compute YoY for the most recent month
            from datetime import timedelta as _td
            fetch_start = (
                (start_date - _td(days=400))
                if start_date
                else (datetime.now() - _td(days=760))
            )
            fetch_end = end_date or datetime.now()

            qs = MacroIndicator.objects.filter(
                series_id__in=relevant,
                date__gte=fetch_start.date() if hasattr(fetch_start, 'date') else fetch_start,
                date__lte=fetch_end.date() if hasattr(fetch_end, 'date') else fetch_end,
            ).values('date', 'series_id', 'value').order_by('series_id', 'date')

            if not qs:
                return pd.DataFrame(columns=['date', 'currency', 'inflation_rate'])

            df = pd.DataFrame(list(qs))
            df['date'] = pd.to_datetime(df['date'])

            result_frames = []
            for sid, group in df.groupby('series_id'):
                currency = self._CPI_SERIES.get(sid)
                if currency not in currencies:
                    continue
                group = group.sort_values('date').drop_duplicates('date')
                # Compute YoY % change: (value / value_12m_ago - 1) * 100
                group = group.set_index('date')
                group['inflation_rate'] = group['value'].pct_change(
                    periods=12  # 12 monthly observations = 1 year
                ) * 100
                group = group.dropna(subset=['inflation_rate']).reset_index()
                group['currency'] = currency
                result_frames.append(group[['date', 'currency', 'inflation_rate']])

            if not result_frames:
                return pd.DataFrame(columns=['date', 'currency', 'inflation_rate'])

            out = pd.concat(result_frames, ignore_index=True)
            # Apply the original date filter after YoY computation
            if start_date:
                sd = pd.Timestamp(start_date)
                out = out[out['date'] >= sd]
            if end_date:
                ed = pd.Timestamp(end_date)
                out = out[out['date'] <= ed]
            return out.sort_values(['date', 'currency']).reset_index(drop=True)
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
