-- Database schema for monitoring tables

-- Agent performance log
CREATE TABLE IF NOT EXISTS agent_performance_log (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    signal INTEGER NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8) NOT NULL,
    pnl DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_performance_agent_time ON agent_performance_log(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_performance_timestamp ON agent_performance_log(timestamp);

-- Trading signals log (note: this table also exists in Django signals app, we keep both for compatibility)
CREATE TABLE IF NOT EXISTS trading_signals_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal INTEGER NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    final_signal INTEGER NOT NULL,
    weights JSONB,
    agent_signals JSONB,
    market_regime VARCHAR(20),
    conflicts_detected BOOLEAN,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_signals_log_symbol_time ON trading_signals_log(symbol, timestamp);

-- News sent processed
CREATE TABLE IF NOT EXISTS news_sentiment_processed (
    id SERIAL PRIMARY KEY,
    news_id INTEGER NOT NULL,
    sentiment_score DECIMAL(5, 4) NOT NULL,
    relevance DECIMAL(5, 4) NOT NULL,
    explained TEXT,
    currencies VARCHAR(10)[],
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_sentiment_timestamp ON news_sentiment_processed(timestamp);

-- System health metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10, 6) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_time ON system_metrics(metric_name, timestamp);

-- Agent status (enabled/disabled)
CREATE TABLE IF NOT EXISTS agent_status (
    agent_name VARCHAR(50) PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    reason TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
