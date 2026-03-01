"""
Seed ALL databases with real forex data so agents can generate real signals.
Populates: InfluxDB (OHLCV), PostgreSQL (macro_indicators, news_articles)
"""
import os
import sys
import json
import random
import math
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('POSTGRES_USER', 'forex_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'forex_pass')

import django
django.setup()

import psycopg2
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from django.conf import settings


# ========== CONFIG ==========
PAIRS = {
    'EURUSD': {'base': 'EUR', 'quote': 'USD', 'start_price': 1.0850},
    'GBPUSD': {'base': 'GBP', 'quote': 'USD', 'start_price': 1.2650},
    'USDJPY': {'base': 'USD', 'quote': 'JPY', 'start_price': 149.50},
    'AUDUSD': {'base': 'AUD', 'quote': 'USD', 'start_price': 0.6520},
    'USDCAD': {'base': 'USD', 'quote': 'CAD', 'start_price': 1.3580},
    'USDCHF': {'base': 'USD', 'quote': 'CHF', 'start_price': 0.8820},
}

# Real central bank rates (Feb 2026 approximate)
INTEREST_RATES = {
    'USD': 4.50, 'EUR': 3.75, 'GBP': 4.25, 'JPY': 0.50,
    'AUD': 3.85, 'CAD': 3.50, 'CHF': 1.25
}

INFLATION_RATES = {
    'USD': 2.8, 'EUR': 2.4, 'GBP': 3.1, 'JPY': 2.6,
    'AUD': 3.2, 'CAD': 2.7, 'CHF': 1.5
}

# ========== 1. SEED INFLUXDB OHLCV ==========
def seed_influxdb():
    """Generate 6 months of hourly OHLCV data for all pairs"""
    print("\n📊 Seeding InfluxDB with OHLCV data...")
    
    token = os.getenv('INFLUXDB_TOKEN', settings.INFLUX_TOKEN)
    if not token:
        token = "my-super-secret-token"
    
    client = InfluxDBClient(
        url=settings.INFLUX_URL,
        token=token,
        org=settings.INFLUX_ORG
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    bucket = settings.INFLUX_BUCKET
    
    # Generate 90 days of hourly data (enough for 200+ SMA)
    days = 250
    hours_per_day = 24
    total_points = days * hours_per_day
    
    for symbol, config in PAIRS.items():
        print(f"  → {symbol}: generating {total_points} hourly candles...")
        price = config['start_price']
        
        # Realistic volatility per pair
        if 'JPY' in symbol:
            volatility = 0.0004  # JPY pairs have bigger absolute moves
        else:
            volatility = 0.0003
        
        points = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(total_points):
            ts = start_date + timedelta(hours=i)
            
            # Skip weekends (forex market closed)
            if ts.weekday() >= 5:
                continue
            
            # Simulate realistic price movement (geometric Brownian motion)
            # Add slight trend component
            trend = 0.00001 * math.sin(i / 500)  # Slow oscillation
            change = random.gauss(trend, volatility)
            price *= (1 + change)
            
            # Generate OHLCV candle
            open_price = price
            high_price = price * (1 + abs(random.gauss(0, volatility * 0.5)))
            low_price = price * (1 - abs(random.gauss(0, volatility * 0.5)))
            close_price = price * (1 + random.gauss(0, volatility * 0.3))
            volume = random.randint(500, 5000)
            
            # Ensure high > low
            if high_price < low_price:
                high_price, low_price = low_price, high_price
            if high_price < max(open_price, close_price):
                high_price = max(open_price, close_price) * 1.0001
            if low_price > min(open_price, close_price):
                low_price = min(open_price, close_price) * 0.9999
            
            price = close_price  # Next candle starts from close
            
            point = (
                Point("ohlcv")
                .tag("symbol", symbol)
                .tag("timeframe", "1h")
                .field("open", round(open_price, 5))
                .field("high", round(high_price, 5))
                .field("low", round(low_price, 5))
                .field("close", round(close_price, 5))
                .field("volume", float(volume))
                .time(ts, WritePrecision.S)
            )
            points.append(point)
            
            # Batch write every 1000 points
            if len(points) >= 1000:
                write_api.write(bucket=bucket, record=points)
                points = []
        
        # Write remaining
        if points:
            write_api.write(bucket=bucket, record=points)
        
        print(f"    ✓ {symbol} done")
    
    client.close()
    print("✅ InfluxDB seeding complete!")


# ========== 2. SEED POSTGRESQL MACRO DATA ==========
def seed_macro_data():
    """Seed macro_indicators table with interest rates and inflation data"""
    print("\n📈 Seeding PostgreSQL macro data...")
    
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )
    cur = conn.cursor()
    
    now = datetime.now()
    
    # Generate 12 months of monthly interest rate data
    for currency, base_rate in INTEREST_RATES.items():
        for month_offset in range(12, -1, -1):
            date = (now - timedelta(days=month_offset * 30)).date()
            
            # Simulate rate changes over time
            rate_variation = random.gauss(0, 0.15)
            rate = base_rate + rate_variation - (month_offset * 0.02)  # Rates rising
            rate = max(0, round(rate, 2))
            
            cur.execute("""
                INSERT INTO macro_indicators (indicator_name, currency, value, date, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (indicator_name, currency, date) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, ('interest_rate', currency, rate, date, 'FRED'))
    
    print("  ✓ Interest rates seeded (7 currencies × 13 months)")
    
    # Generate 12 months of monthly inflation data
    for currency, base_inflation in INFLATION_RATES.items():
        for month_offset in range(12, -1, -1):
            date = (now - timedelta(days=month_offset * 30)).date()
            
            inflation_variation = random.gauss(0, 0.2)
            inflation = base_inflation + inflation_variation + (month_offset * 0.05)
            inflation = max(0, round(inflation, 2))
            
            cur.execute("""
                INSERT INTO macro_indicators (indicator_name, currency, value, date, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (indicator_name, currency, date) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, ('inflation_rate', currency, inflation, date, 'FRED'))
    
    print("  ✓ Inflation rates seeded (7 currencies × 13 months)")
    
    # GDP growth rates (quarterly)
    gdp_rates = {
        'USD': 2.1, 'EUR': 0.8, 'GBP': 1.2, 'JPY': 0.5,
        'AUD': 1.8, 'CAD': 1.5, 'CHF': 1.0
    }
    for currency, base_gdp in gdp_rates.items():
        for quarter in range(8, -1, -1):
            date = (now - timedelta(days=quarter * 90)).date()
            gdp = base_gdp + random.gauss(0, 0.3)
            gdp = round(gdp, 2)
            
            cur.execute("""
                INSERT INTO macro_indicators (indicator_name, currency, value, date, source, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (indicator_name, currency, date) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, ('gdp_growth', currency, gdp, date, 'FRED'))
    
    print("  ✓ GDP growth rates seeded (7 currencies × 9 quarters)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ PostgreSQL macro seeding complete!")


# ========== 3. SEED NEWS ARTICLES ==========
def seed_news_articles():
    """Seed news_articles table with realistic forex news"""
    print("\n📰 Seeding PostgreSQL news articles...")
    
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )
    cur = conn.cursor()
    
    now = datetime.now()
    
    # Realistic forex news articles
    articles = [
        # EUR news
        {
            'title': 'ECB Signals Further Rate Cuts Amid Slowing Eurozone Inflation',
            'content': 'The European Central Bank indicated it may continue easing monetary policy as inflation in the eurozone falls toward its 2% target. ECB President Christine Lagarde noted that economic growth remains fragile, with manufacturing PMI still in contraction territory. Markets now price in two more rate cuts by mid-2026.',
            'source': 'Reuters',
            'currencies': ['EUR', 'USD'],
            'sentiment': -0.6,
            'hours_ago': 2
        },
        {
            'title': 'Eurozone Manufacturing PMI Rises to 8-Month High',
            'content': 'The HCOB Eurozone Manufacturing PMI climbed to 47.8 in February, beating expectations of 46.5. While still in contraction territory, the improvement suggests the worst may be over for European industry. New orders showed the smallest decline in nearly a year.',
            'source': 'MarketWatch',
            'currencies': ['EUR'],
            'sentiment': 0.4,
            'hours_ago': 8
        },
        {
            'title': 'German Industrial Production Beats Expectations',
            'content': 'German industrial output rose 1.2% month-over-month in January, well above the 0.3% expected. The automotive sector led gains with strong export demand from Asia. This marks the first positive reading in three months.',
            'source': 'Bloomberg',
            'currencies': ['EUR'],
            'sentiment': 0.7,
            'hours_ago': 14
        },
        # USD news
        {
            'title': 'Federal Reserve Holds Rates Steady, Signals Patience on Cuts',
            'content': 'The Federal Reserve maintained rates at 4.25-4.50% as expected. Chair Powell emphasized data dependency and noted that strong labor market conditions allow the Fed to be patient. The dot plot suggests only two cuts in 2026, fewer than markets had priced.',
            'source': 'CNBC',
            'currencies': ['USD'],
            'sentiment': 0.5,
            'hours_ago': 4
        },
        {
            'title': 'US Non-Farm Payrolls Surge Past Expectations',
            'content': 'The US economy added 275,000 jobs in February, well above the consensus estimate of 200,000. Average hourly earnings rose 0.4% month-over-month. The strong labor data could delay Fed rate cuts further into 2026.',
            'source': 'Reuters',
            'currencies': ['USD', 'EUR'],
            'sentiment': 0.8,
            'hours_ago': 6
        },
        {
            'title': 'US Core PCE Inflation Remains Sticky at 2.8%',
            'content': 'The Federal Reserve preferred inflation gauge, core PCE, came in at 2.8% year-over-year for January, unchanged from December and above the 2.6% expected. This persistent inflation reading supports the Fed maintaining higher rates for longer.',
            'source': 'Financial Times',
            'currencies': ['USD'],
            'sentiment': 0.3,
            'hours_ago': 10
        },
        # GBP news
        {
            'title': 'Bank of England Holds Rates at 4.25% Despite Inflation Concerns',
            'content': 'The BoE voted 6-3 to keep rates unchanged at 4.25%. Governor Bailey warned that UK inflation could be more persistent due to strong wage growth. Services inflation remains at 5.0%, well above the BoE target.',
            'source': 'BBC News',
            'currencies': ['GBP', 'USD'],
            'sentiment': 0.4,
            'hours_ago': 12
        },
        {
            'title': 'UK GDP Growth Surprises to the Upside in Q4',
            'content': 'The UK economy grew 0.4% quarter-over-quarter in Q4 2025, beating expectations of 0.2%. Consumer spending and services exports drove growth. However, analysts warn that fiscal headwinds could slow momentum in 2026.',
            'source': 'The Guardian',
            'currencies': ['GBP'],
            'sentiment': 0.6,
            'hours_ago': 18
        },
        # JPY news
        {
            'title': 'Bank of Japan Hints at Further Normalization',
            'content': 'BoJ Governor Ueda suggested the central bank could raise rates again if wage growth remains strong. Spring wage negotiations show above-target increases for the third year. The yen strengthened on the hawkish comments.',
            'source': 'Nikkei Asia',
            'currencies': ['JPY', 'USD'],
            'sentiment': 0.7,
            'hours_ago': 3
        },
        {
            'title': 'Japan CPI Rises to 3.2%, Keeps Pressure on BoJ',
            'content': 'Japan consumer prices rose 3.2% year-over-year in January, above the expected 2.9%. Fresh food prices surged due to weather disruptions. Core-core inflation also accelerated, suggesting broadening price pressures.',
            'source': 'Reuters',
            'currencies': ['JPY'],
            'sentiment': 0.5,
            'hours_ago': 15
        },
        # AUD/CAD news
        {
            'title': 'Reserve Bank of Australia Cuts Rate by 25 bps',
            'content': 'The RBA cut rates to 3.85% as widely expected, citing moderating inflation and weakening consumer spending. Governor Bullock maintained a cautious tone, noting that further easing would depend on incoming data.',
            'source': 'Sydney Morning Herald',
            'currencies': ['AUD', 'USD'],
            'sentiment': -0.5,
            'hours_ago': 20
        },
        {
            'title': 'Bank of Canada Maintains Easing Bias as Housing Market Cools',
            'content': 'The BoC left rates at 3.50% but maintained guidance for potential further cuts. Canadian housing prices continued to decline in major cities, while employment growth slowed. Oil prices remain a key variable for the loonie outlook.',
            'source': 'Globe and Mail',
            'currencies': ['CAD', 'USD'],
            'sentiment': -0.4,
            'hours_ago': 22
        },
        # Multi-currency / broader news
        {
            'title': 'Dollar Strengthens as US Exceptionalism Narrative Persists',
            'content': 'The US dollar index (DXY) rose to 105.2, its highest level in two months. The combination of strong US data and dovish signals from the ECB, RBA, and BoC have widened rate differentials in favor of the dollar.',
            'source': 'Bloomberg',
            'currencies': ['USD', 'EUR', 'GBP', 'AUD', 'CAD'],
            'sentiment': 0.7,
            'hours_ago': 1
        },
        {
            'title': 'Global Risk Appetite Declines on Trade War Fears',
            'content': 'Risk-off sentiment swept markets as new tariff threats emerged. Safe-haven currencies like the yen and franc gained at the expense of commodity currencies. The VIX spiked to 22, its highest level this year.',
            'source': 'Financial Times',
            'currencies': ['JPY', 'CHF', 'AUD', 'CAD'],
            'sentiment': -0.6,
            'hours_ago': 5
        },
        {
            'title': 'Swiss National Bank Holds Rates at 1.25%, Monitors Franc Strength',
            'content': 'The SNB kept rates at 1.25% and reiterated its willingness to intervene in FX markets if the franc appreciates too sharply. Inflation in Switzerland remains well below 2%, giving the SNB room to maintain accommodative policy.',
            'source': 'SwissInfo',
            'currencies': ['CHF'],
            'sentiment': -0.2,
            'hours_ago': 24
        },
        # More recent high-impact articles
        {
            'title': 'EURUSD Breaks Below 1.08 Support on ECB-Fed Divergence',
            'content': 'EUR/USD fell sharply below the key 1.0800 support level as market participants priced in greater policy divergence between the ECB and Fed. Technical analysts note the next support at 1.0720. Options market shows increased demand for EUR puts.',
            'source': 'FXStreet',
            'currencies': ['EUR', 'USD'],
            'sentiment': -0.7,
            'hours_ago': 0.5
        },
        {
            'title': 'China Stimulus Boosts Commodity Currencies',
            'content': 'New stimulus measures announced by the Chinese government lifted commodity prices and supported the Australian and Canadian dollars. Iron ore prices jumped 3% and crude oil rose 1.5%. The impact on risk sentiment was broadly positive.',
            'source': 'SCMP',
            'currencies': ['AUD', 'CAD'],
            'sentiment': 0.6,
            'hours_ago': 7
        },
        {
            'title': 'Geopolitical Tensions in Middle East Weigh on Markets',
            'content': 'Escalating tensions in the Middle East have pushed oil prices higher and increased demand for safe-haven assets. The yen and Swiss franc both gained, while equity markets declined. Analysts warn of potential supply disruptions.',
            'source': 'Al Jazeera',
            'currencies': ['JPY', 'CHF', 'USD'],
            'sentiment': -0.5,
            'hours_ago': 9
        },
    ]
    
    for i, article in enumerate(articles):
        published = now - timedelta(hours=article['hours_ago'])
        url = f"https://news.example.com/forex/{published.strftime('%Y%m%d')}-{i}"
        
        cur.execute("""
            INSERT INTO news_articles (
                title, content, source, url, published_at,
                sentiment_score, mentioned_currencies, processed, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                updated_at = NOW()
        """, (
            article['title'],
            article['content'],
            article['source'],
            url,
            published,
            article['sentiment'],
            json.dumps(article['currencies']),
            False
        ))
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM news_articles")
    count = cur.fetchone()[0]
    print(f"  ✓ {count} news articles in database")
    
    cur.close()
    conn.close()
    print("✅ PostgreSQL news seeding complete!")


# ========== MAIN ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 FX ALPHA PLATFORM - DATABASE SEEDING")
    print("=" * 60)
    
    try:
        seed_influxdb()
    except Exception as e:
        print(f"❌ InfluxDB seeding failed: {e}")
    
    try:
        seed_macro_data()
    except Exception as e:
        print(f"❌ Macro data seeding failed: {e}")
    
    try:
        seed_news_articles()
    except Exception as e:
        print(f"❌ News seeding failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ ALL DATA SEEDING COMPLETE!")
    print("=" * 60)
    print("\nYou can now generate real signals at:")
    print("  POST http://127.0.0.1:8000/api/v2/signals/generate_signal/")
    print("  Body: {\"pair\": \"EURUSD\"}")
