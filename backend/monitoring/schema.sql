"""
Database schema for monitoring tables
"""

-- Agent performance log
CREATE TABLE IF NOT EXISTS agent_performance_log (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    signal INTEGER NOT NULL,  -- -1, 0, 1
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8) NOT NULL,
    pnl DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    INDEX idx_agent_time (agent_name, timestamp),
    INDEX idx_timestamp (timestamp)
);

-- Trading signals log
CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal INTEGER NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    final_signal INTEGER NOT NULL,
    weights JSONB,
    agent_signals JSONB,
    market_regime VARCHAR(20),
    conflicts_detected BOOLEAN,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    INDEX idx_symbol_time (symbol, timestamp)
);

-- News sentiment processed
CREATE TABLE IF NOT EXISTS news_sentiment_processed (
    id SERIAL PRIMARY KEY,
    news_id INTEGER NOT NULL,
    sentiment_score DECIMAL(5, 4) NOT NULL,  -- -1 to 1
    relevance DECIMAL(5, 4) NOT NULL,  -- 0 to 1
    explained TEXT,
    currencies VARCHAR(10)[],
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    INDEX idx_timestamp (timestamp)
);

-- System health metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10, 6) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    INDEX idx_metric_time (metric_name, timestamp)
);

-- Agent status (enabled/disabled)
CREATE TABLE IF NOT EXISTS agent_status (
    agent_name VARCHAR(50) PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    reason TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
