"""
News Data Acquisition Script
Scrapes forex-related news articles from multiple sources and stores in PostgreSQL
Enhanced version with fallback sources
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import time
import feedparser

load_dotenv()

POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

# Keywords to search for
KEYWORDS = ['forex', 'EUR', 'USD', 'JPY', 'GBP', 'CHF', 'Federal Reserve', 'ECB', 'currency', 'exchange rate']

# Multiple RSS sources for redundancy
RSS_SOURCES = [
    {
        'name': 'Investing.com Forex',
        'url': 'https://www.investing.com/rss/news_14.rss',
        'parser': 'feedparser'
    },
    {
        'name': 'FXStreet',
        'url': 'https://www.fxstreet.com/feeds/news',
        'parser': 'feedparser'
    },
    {
        'name': 'DailyFX',
        'url': 'https://www.dailyfx.com/feeds/market-news',
        'parser': 'feedparser'
    },
    {
        'name': 'ForexLive',
        'url': 'https://www.forexlive.com/feed/news',
        'parser': 'feedparser'
    },
    {
        'name': 'Reuters Business',
        'url': 'https://www.reuters.com/rssFeed/businessNews',
        'parser': 'xml'
    }
]

def scrape_with_feedparser(source_name, feed_url):
    """Scrape RSS feed using feedparser library"""
    articles = []
    
    try:
        print(f"   Trying {source_name}...")
        feed = feedparser.parse(feed_url)
        
        if feed.entries:
            print(f"   ✓ Found {len(feed.entries)} articles from {source_name}")
            
            for entry in feed.entries:
                title = entry.get('title', '')
                link = entry.get('link', '')
                description = entry.get('summary', '') or entry.get('description', '')
                published = entry.get('published', '') or entry.get('updated', '')
                
                # Check if forex-related
                content = f"{title} {description}".lower()
                is_relevant = any(keyword.lower() in content for keyword in KEYWORDS)
                
                if is_relevant and link:
                    # Identify currencies mentioned
                    currencies = []
                    for curr in ['EUR', 'USD', 'JPY', 'GBP', 'CHF']:
                        if curr in content.upper():
                            currencies.append(curr)
                    
                    articles.append({
                        'url': link,
                        'title': title,
                        'content': description[:1000],  # Limit content length
                        'source': source_name,
                        'published_at': published or datetime.now().isoformat(),
                        'currencies': currencies,
                        'scraped_at': datetime.now()
                    })
            
            print(f"   ✅ {len(articles)} forex-related articles from {source_name}")
        else:
            print(f"   ⚠️  No entries found from {source_name}")
            
    except Exception as e:
        print(f"   ❌ Error with {source_name}: {e}")
    
    return articles

def scrape_with_xml(source_name, rss_url):
    """Scrape RSS feed using XML parser (fallback method)"""
    articles = []
    
    try:
        print(f"   Trying {source_name}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(rss_url, timeout=15, headers=headers)
        soup = BeautifulSoup(response.content, 'xml')
        
        items = soup.find_all('item')
        
        if items:
            print(f"   ✓ Found {len(items)} articles from {source_name}")
            
            for item in items:
                title = item.find('title').text if item.find('title') else ''
                link = item.find('link').text if item.find('link') else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') else ''
                description = item.find('description').text if item.find('description') else ''
                
                # Check if forex-related
                content = f"{title} {description}".lower()
                is_relevant = any(keyword.lower() in content for keyword in KEYWORDS)
                
                if is_relevant and link:
                    # Identify currencies mentioned
                    currencies = []
                    for curr in ['EUR', 'USD', 'JPY', 'GBP', 'CHF']:
                        if curr in content.upper():
                            currencies.append(curr)
                    
                    articles.append({
                        'url': link,
                        'title': title,
                        'content': description[:1000],
                        'source': source_name,
                        'published_at': pub_date or datetime.now().isoformat(),
                        'currencies': currencies,
                        'scraped_at': datetime.now()
                    })
            
            print(f"   ✅ {len(articles)} forex-related articles from {source_name}")
        else:
            print(f"   ⚠️  No items found from {source_name}")
            
    except Exception as e:
        print(f"   ❌ Error with {source_name}: {e}")
    
    return articles

def scrape_all_sources():
    """Scrape news from all available sources"""
    print("=" * 60)
    print("NEWS DATA ACQUISITION - MULTI-SOURCE")
    print("=" * 60)
    
    all_articles = []
    successful_sources = 0
    
    print(f"\n📰 Fetching news from {len(RSS_SOURCES)} sources...")
    
    for source in RSS_SOURCES:
        try:
            if source['parser'] == 'feedparser':
                articles = scrape_with_feedparser(source['name'], source['url'])
            else:
                articles = scrape_with_xml(source['name'], source['url'])
            
            if articles:
                all_articles.extend(articles)
                successful_sources += 1
                
            time.sleep(1)  # Be polite to servers
            
        except Exception as e:
            print(f"   ❌ Failed to process {source['name']}: {e}")
    
    # Remove duplicates based on URL
    unique_articles = {}
    for article in all_articles:
        url = article['url']
        if url not in unique_articles:
            unique_articles[url] = article
    
    final_articles = list(unique_articles.values())
    
    print(f"\n📊 Summary:")
    print(f"   • Sources queried: {len(RSS_SOURCES)}")
    print(f"   • Successful sources: {successful_sources}")
    print(f"   • Total articles found: {len(all_articles)}")
    print(f"   • Unique articles: {len(final_articles)}")
    
    return final_articles

def write_articles_to_postgres(articles):
    """Write articles to PostgreSQL"""
    if not articles:
        print("\n⚠️  No articles to write")
        return
    
    print(f"\n💾 Writing {len(articles)} articles to PostgreSQL...")
    
    conn_string = f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    inserted = 0
    duplicates = 0
    
    try:
        # Detect the currency column used by current schema
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'news_articles'
              AND column_name IN ('mentioned_currencies', 'currencies')
            """
        )
        columns = {row[0] for row in cursor.fetchall()}
        currency_column = 'mentioned_currencies' if 'mentioned_currencies' in columns else 'currencies'

        if currency_column == 'mentioned_currencies':
            insert_sql = """
                INSERT INTO news_articles (url, title, content, source, published_at, mentioned_currencies, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (url) DO NOTHING
            """
        else:
            insert_sql = """
                INSERT INTO news_articles (url, title, content, source, published_at, currencies, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
            """

        for article in articles:
            try:
                cursor.execute("SAVEPOINT article_sp")

                if currency_column == 'mentioned_currencies':
                    cursor.execute(
                        insert_sql,
                        (
                            article['url'],
                            article['title'],
                            article['content'],
                            article['source'],
                            article['published_at'],
                            json.dumps(article['currencies']),
                        )
                    )
                else:
                    cursor.execute(
                        insert_sql,
                        (
                            article['url'],
                            article['title'],
                            article['content'],
                            article['source'],
                            article['published_at'],
                            article['currencies'],
                            article['scraped_at']
                        )
                    )

                cursor.execute("RELEASE SAVEPOINT article_sp")
                
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    duplicates += 1
                    
            except Exception as e:
                cursor.execute("ROLLBACK TO SAVEPOINT article_sp")
                print(f"   ⚠️  Error inserting article: {e}")
        
        conn.commit()
        print(f"   ✅ Inserted {inserted} new articles")
        if duplicates > 0:
            print(f"   ℹ️  Skipped {duplicates} duplicates")
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Write failed: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    # Scrape articles from all sources
    articles = scrape_all_sources()
    
    # Write to database
    write_articles_to_postgres(articles)
    
    print("\n" + "=" * 60)
    print("✅ NEWS DATA ACQUISITION COMPLETE")
    print("=" * 60)

# Alias for orchestrator / API calls
collect_news_data = main

if __name__ == "__main__":
    main()
