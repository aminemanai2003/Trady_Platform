/* Domain types for the Trady Platform. */

// ─── Currency Pairs ───────────────────────────
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

// ─── OHLCV ────────────────────────────────────
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

// ─── Signals ──────────────────────────────────
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

// ─── Agents ───────────────────────────────────
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

// ─── KPIs ─────────────────────────────────────
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

// ─── Technical Indicators ─────────────────────
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

// ─── Economic Calendar ────────────────────────
export interface EconomicEvent {
    date: string;
    currency: string;
    event: string;
    importance: "HIGH" | "MEDIUM" | "LOW";
    forecast: string | null;
    previous: string | null;
    actual?: string | null;
}

// ─── Performance ──────────────────────────────
export interface DailyPerformance {
    date: string;
    daily_pnl: number;
    cumulative_pnl: number;
    win_rate: number;
    sharpe: number;
    trades: number;
}

// ─── Trading ──────────────────────────────────
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

// ─── V2 Architecture Types ────────────────────

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
    };
    system: {
        uptime_seconds: number;
        memory_usage_mb: number;
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
