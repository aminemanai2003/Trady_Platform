/* Domain types for the Trady Platform. */

// â”€â”€â”€ Currency Pairs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export type PairSymbol = "EURUSD" | "USDJPY" | "USDCHF" | "GBPUSD";

export interface CurrencyPair {
    symbol: PairSymbol;
    displayName: string;
    base: string;
    quote: string;
    pipSize: number;
    decimals: number;
}

export const PAIRS: CurrencyPair[] = [
    { symbol: "EURUSD", displayName: "EUR/USD", base: "EUR", quote: "USD", pipSize: 0.0001, decimals: 4 },
    { symbol: "USDJPY", displayName: "USD/JPY", base: "USD", quote: "JPY", pipSize: 0.01, decimals: 2 },
    { symbol: "USDCHF", displayName: "USD/CHF", base: "USD", quote: "CHF", pipSize: 0.0001, decimals: 4 },
    { symbol: "GBPUSD", displayName: "GBP/USD", base: "GBP", quote: "USD", pipSize: 0.0001, decimals: 4 },
];

// â”€â”€â”€ OHLCV â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export type Timeframe = "1H" | "4H" | "1D" | "W1" | "M1";

export interface CandleData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    symbol: string;
    timeframe: string;
}

// â”€â”€â”€ Signals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export type SignalDirection = "BUY" | "SELL" | "NEUTRAL";

export interface TradingSignal {
    id: number;
    pair: PairSymbol;
    direction: SignalDirection;
    confidence: number;
    macro_score: number;
    technical_score: number;
    sentiment_score: number;
    consensus_count: number;
    rationale: string;
    entry_price: number | null;
    stop_loss: number | null;
    take_profit: number | null;
    is_active: boolean;
    created_at: string;
    pnl: number | null;
}

// â”€â”€â”€ Agents â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export type AgentType = "MACRO" | "TECHNICAL" | "SENTIMENT" | "ORCHESTRATOR";
export type AgentStatus = "ONLINE" | "PROCESSING" | "OFFLINE" | "ERROR";

export interface AgentInfo {
    type: AgentType;
    name: string;
    description: string;
    status: AgentStatus;
    last_run: string;
    last_decision: SignalDirection;
    confidence: number;
    tokens_used: number;
    latency_ms: number;
    accuracy_30d: number;
}

export interface AgentStatusResponse {
    agents: AgentInfo[];
    consensus_rate: number;
}

// â”€â”€â”€ KPIs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface KpiValue {
    value: number;
    target: number;
    status: "on_track" | "warning" | "critical";
}

export interface KpiScorecard {
    sharpe_ratio: KpiValue;
    win_rate: KpiValue;
    max_drawdown: KpiValue;
    profit_factor: KpiValue;
    signal_accuracy: KpiValue;
    f1_score: KpiValue;
    agent_consensus: KpiValue;
    signal_latency_ms: KpiValue;
    system_uptime: KpiValue;
    llm_cost_per_signal: KpiValue;
}

// â”€â”€â”€ Technical Indicators â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface TechnicalIndicators {
    rsi: number;
    macd: number;
    macd_signal: number;
    bb_upper: number;
    bb_lower: number;
    bb_middle: number;
    sma_50: number;
    sma_200: number;
    atr: number;
    close: number;
}

export interface TechnicalAnalysis {
    pair: string;
    signal: SignalDirection;
    confidence: number;
    score: number;
    reasoning: string;
    indicators: TechnicalIndicators;
}

// â”€â”€â”€ Economic Calendar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface EconomicEvent {
    date: string;
    currency: string;
    event: string;
    importance: "HIGH" | "MEDIUM" | "LOW";
    forecast: string | null;
    previous: string | null;
    actual?: string | null;
}

// â”€â”€â”€ Performance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface DailyPerformance {
    date: string;
    daily_pnl: number;
    cumulative_pnl: number;
    win_rate: number;
    sharpe: number;
    trades: number;
}

export interface ReportHistoryRow {
    id: number;
    agent_name: string;
    pair: string;
    direction: "BUY" | "SELL" | "NEUTRAL";
    confidence: number;
    outcome: "WIN" | "LOSS";
    pnl: number;
    time: string;
}

export interface ReportSummaryResponse {
    kpis: {
        total_pnl: number;
        win_rate: number;
        sharpe: number;
        signals: number;
        confluence: number;
    };
    curve: Array<{
        date: string;
        daily_pnl: number;
        cumulative_pnl: number;
        win_rate: number;
        trades: number;
    }>;
    history: ReportHistoryRow[];
    days: number;
    pair: string;
}

// â”€â”€â”€ Trading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT" | "STOP";
export type PositionStatus = "OPEN" | "CLOSED";

export interface Position {
    id: number;
    pair: PairSymbol;
    side: OrderSide;
    size: number;
    entry_price: number;
    current_price: number;
    stop_loss: number | null;
    take_profit: number | null;
    pnl: number;
    pnl_pct: number;
    opened_at: string;
    status: PositionStatus;
}

export interface Order {
    pair: PairSymbol;
    side: OrderSide;
    type: OrderType;
    size: number;
    price?: number;
    stop_loss?: number;
    take_profit?: number;
}

// â”€â”€â”€ V2 Architecture Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export interface AgentPerformanceV2 {
    agent_type: string;
    total_signals: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
    avg_confidence: number;
    last_30d_accuracy: number;
    total_pnl: number;
}

export interface SignalResponseV2 {
    success: boolean;
    signal: {
        direction: SignalDirection;
        confidence: number;
        weighted_score: number;
        reasoning: string;
        agent_votes: {
            technical: { signal: SignalDirection; confidence: number; reasoning: string };
            macro: { signal: SignalDirection; confidence: number; reasoning: string };
            sentiment: { signal: SignalDirection; confidence: number; reasoning: string };
        };
        weights: {
            technical: number;
            macro: number;
            sentiment: number;
        };
        market_regime: string;
        conflicts: string[];
        timestamp: string;
    };
    metadata: {
        execution_time_ms: number;
        data_timestamps: {
            ohlcv: string;
            macro: string;
            news: string;
        };
    };
}

export interface HealthCheckV2 {
    status: string;
    timestamp: string;
    agent_performances: Record<string, AgentPerformanceV2>;
    monitoring: {
        performance_tracker: { status: string; agents_tracked: number };
        drift_detector: { status: string; last_check: string };
        safety_monitor: { status: string; cooldown_active: boolean };
        news_freshness?: {
            status: string;
            age_minutes: number | null;
            articles_last_1h: number;
            articles_last_24h: number;
            freshness_score: number;
        };
    };
    system: {
        uptime_seconds: number;
        memory_usage_mb: number;
    };
}

export interface FreshnessHealthV2 {
    timestamp: string;
    freshness: {
        status: "PASS" | "WARN" | "NO_DATA";
        freshness_score: number;
        data_types: {
            news: {
                status: "PASS" | "WARN" | "NO_DATA";
                last_news_timestamp: string | null;
                age_minutes: number | null;
                latency: {
                    source_access_lag_minutes: number | null;
                    extraction_transfer_minutes: number;
                    total_latency_minutes: number | null;
                };
                articles_last_1h: number;
                articles_last_24h: number;
                freshness_score: number;
                target_max_age_minutes: number;
            };
            macro: {
                status: "PASS" | "WARN" | "NO_DATA";
                last_timestamp: string | null;
                age_minutes: number | null;
                latency: {
                    source_access_lag_minutes: number | null;
                    extraction_transfer_minutes: number;
                    total_latency_minutes: number | null;
                };
                freshness_score: number;
                target_max_age_minutes: number;
            };
            ohlcv: {
                status: "PASS" | "WARN" | "NO_DATA";
                last_timestamp: string | null;
                age_minutes: number | null;
                latency: {
                    source_access_lag_minutes: number | null;
                    extraction_transfer_minutes: number;
                    total_latency_minutes: number | null;
                };
                freshness_score: number;
                target_max_age_minutes: number;
            };
        };
        recommended_actions: Array<{
            data_type: "news" | "macro" | "ohlcv";
            severity: "medium" | "high";
            reason: string;
            action: string;
        }>;
    };
}

export interface DriftDetectionV2 {
    sentiment_drift: {
        detected: boolean;
        ks_statistic: number;
        p_value: number;
        severity: string;
    };
    volatility_drift: {
        current_regime: string;
        regime_confidence: number;
        trend: string;
    };
    timestamp: string;
}

// ─── Master Signal (unified pipeline response) ──────────────────────────────

export interface AgentVote {
    signal: SignalDirection;
    signal_value: -1 | 0 | 1;
    confidence: number;
    weight: number;
    contribution: number;
    key_features: string[];
    reasoning: string;
    influence_rank: number | null;
    // Geopolitical-specific extras
    key_events?: string[];
    impacted_currencies?: string[];
}

export interface XaiAgentBreakdown {
    TechnicalV2?: AgentVote;
    MacroV2?: AgentVote;
    SentimentV2?: AgentVote;
    GeopoliticalV2?: AgentVote;
    [key: string]: AgentVote | undefined;
}

export interface MasterSignalResponse {
    success: boolean;
    decision: "APPROVED" | "APPROVED_MODIFIED" | "REJECTED" | "BLOCKED";
    pair: string;
    signal: {
        direction: SignalDirection;
        signal_value: -1 | 0 | 1;
        confidence: number;
    };
    coordinator: {
        weighted_score: number;
        market_regime: string;
        conflicts_detected: boolean;
        conflict_description: string;
    };
    judge: {
        verdict: "APPROVE" | "REJECT" | "MODIFY";
        reasoning: string;
        latency_ms: number;
        from_cache: boolean;
    };
    actuarial: {
        expected_value_pips: number;
        probability_win: number;
        probability_loss: number;
        risk_reward_ratio: number;
        kelly_fraction: number;
        verdict: string;
    };
    execution_plan?: {
        entry_price: number;
        position_size: number;
        stop_loss: number | null;
        take_profit: number | null;
        stop_loss_pips: number;
        take_profit_pips: number;
        risk_pct: number;
    };
    rejection?: {
        stage: string | null;
        reason: string | null;
    };
    xai: {
        agent_breakdown: XaiAgentBreakdown;
        human_explanation: Record<string, unknown>;
        rejection_stage: string | null;
        rejection_reason: string | null;
    };
    geopolitical_events: string[];
    timestamp: string;
}

// ─── Paper Trading ──────────────────────────────────────────────────────────

export interface PaperPosition {
    id: number;
    pair: PairSymbol;
    side: "BUY" | "SELL";
    size: number;
    entry_price: number;
    current_price: number;
    stop_loss: number | null;
    take_profit: number | null;
    pnl: number;
    pnl_pct: number;
    status: "OPEN" | "CLOSED";
    opened_at: string;
    closed_at: string | null;
}

export interface PortfolioStats {
    total_pnl: number;
    total_trades: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
    open_positions: number;
    total_exposure: number;
}

// ─── WebSocket price tick ────────────────────────────────────────────────────

export interface PriceTick {
    pair: string;
    price: number;
    bid: number;
    ask: number;
    timestamp: string;
}

