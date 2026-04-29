"""
FRED (Federal Reserve Economic Data) collector for SQLite.
Fetches key macroeconomic indicators and stores them in the MacroIndicator model.
Requires FRED_API_KEY in environment or .env file.
Free tier: unlimited public data access.
"""
import os
import logging
from datetime import datetime, timezone, date

import requests
import pandas as pd

logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Key macroeconomic series to track
INDICATORS = {
    "FEDFUNDS": "Federal Funds Rate",
    "CPIAUCSL": "US CPI (YoY Inflation)",
    "UNRATE": "US Unemployment Rate",
    "GDP": "US GDP (Quarterly)",
    "DEXUSEU": "EUR/USD Exchange Rate",
    "DEXJPUS": "USD/JPY Exchange Rate",
    "DEXUSUK": "GBP/USD Exchange Rate",
    "DGS10": "US 10Y Treasury Yield",
    "T10YIE": "US 10Y Inflation Expectations",
    "ECBDFR": "ECB Deposit Facility Rate",
}


def _fetch_series(series_id: str, observation_start: str = "2020-01-01") -> pd.DataFrame:
    """Fetch a FRED series, return DataFrame with date/value columns."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": observation_start,
        "sort_order": "desc",
        "limit": 500,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    observations = data.get("observations", [])
    rows = []
    for obs in observations:
        val_str = obs.get("value", ".")
        if val_str == ".":
            continue
        try:
            rows.append({
                "date": date.fromisoformat(obs["date"]),
                "value": float(val_str),
            })
        except (ValueError, KeyError):
            continue

    return pd.DataFrame(rows)


def collect_fred_macro() -> dict:
    """
    Fetch all FRED indicators and store in SQLite MacroIndicator model.
    Returns {'inserted': int, 'skipped': int, 'errors': list}
    """
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — skipping macro collection")
        return {"inserted": 0, "skipped": 0, "errors": ["FRED_API_KEY missing"]}

    from scheduling.models import MacroIndicator, IngestionLog

    log = IngestionLog.objects.create(source="macro")
    total_inserted = 0
    total_skipped = 0
    errors = []

    try:
        for series_id, indicator_name in INDICATORS.items():
            try:
                df = _fetch_series(series_id)
                if df.empty:
                    logger.warning(f"[FRED] {series_id}: empty response")
                    continue

                inserted = 0
                skipped = 0
                for _, row in df.iterrows():
                    _, created = MacroIndicator.objects.get_or_create(
                        series_id=series_id,
                        date=row["date"],
                        defaults={
                            "indicator_name": indicator_name,
                            "value": row["value"],
                        },
                    )
                    if created:
                        inserted += 1
                    else:
                        skipped += 1

                total_inserted += inserted
                total_skipped += skipped
                logger.info(
                    f"[FRED] {series_id}: inserted={inserted} skipped={skipped}"
                )

            except Exception as exc:
                msg = f"{series_id}: {exc}"
                errors.append(msg)
                logger.error(f"[FRED] error fetching {msg}")

        log.records_inserted = total_inserted
        log.status = "success" if not errors else "partial"
        log.error_message = "; ".join(errors)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()

        return {"inserted": total_inserted, "skipped": total_skipped, "errors": errors}

    except Exception as exc:
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        logger.error(f"[FRED] fatal error: {exc}", exc_info=True)
        return {"inserted": 0, "skipped": 0, "errors": [str(exc)]}
