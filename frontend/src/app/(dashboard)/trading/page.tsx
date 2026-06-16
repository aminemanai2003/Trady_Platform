"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
    AlertTriangle,
    BrainCircuit,
    Camera,
    Check,
    Clock3,
    Download,
    LoaderCircle,
    LockKeyhole,
    RefreshCw,
    ShieldCheck,
    Sparkles,
    TrendingDown,
    TrendingUp,
    X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { RBContent, RBHeader } from "@/components/reactbits";
import {
    LiveMarketChart,
    type LiveMarketChartHandle,
    type MarketCandle,
} from "@/components/live-market-chart";

type Pair = "EURUSD" | "GBPUSD" | "USDJPY" | "USDCHF";
type Timeframe = "1h" | "4h" | "1d";

type MarketData = {
    pair: Pair;
    timeframe: Timeframe;
    candles: MarketCandle[];
    latest_candle_at: string;
    latest_price: number;
    quote: { bid: number; ask: number; spread: number; timestamp: string } | null;
    data_source: string;
    data_status: "live" | "delayed" | "market_closed" | "stale" | "unavailable";
    market_open: boolean;
    bar_count: number;
};

type Analysis = {
    analysisId: string;
    pair: Pair;
    timeframe: Timeframe;
    horizon: string;
    action: "BUY" | "SELL" | "HOLD";
    approved_for_paper_trade: boolean;
    market_timestamp: string;
    latest_price: number;
    data_status: string;
    data_source: string;
    explanation: string;
    visual_observations: string | null;
    blockers: string[];
    warnings: string[];
    indicators: Record<string, number | null>;
    levels: {
        support: number | null;
        resistance: number | null;
        suggested_stop: number | null;
        suggested_target: number | null;
    };
    forecast: {
        available: boolean;
        validated: boolean;
        direction?: string;
        model_probability?: number;
        balanced_accuracy?: number;
        majority_baseline?: number;
        validation_samples?: number;
        reason?: string;
    };
    agent_consensus: {
        direction: string;
        confidence: number | null;
        evidence_coverage: number;
        conflicts_detected: boolean;
        market_regime: string;
    };
    usage: { count: number; limit: number; period: string };
    captureUsed: boolean;
};

type PlanStatus = {
    plan: string;
    planLabel: string;
    pairs: Pair[];
    usage: { count: number; limit: number; period: string };
};

type Position = {
    id: number;
    pair: Pair;
    side: "BUY" | "SELL";
    size: number;
    entryPrice: number;
    currentPrice: number;
    stopLoss: number | null;
    takeProfit: number | null;
    pnl: number;
    openedAt: string;
};

const allPairs: Pair[] = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"];
const timeframes: Array<{ value: Timeframe; label: string; horizon: string }> = [
    { value: "1h", label: "1H", horizon: "4 hours" },
    { value: "4h", label: "4H", horizon: "16 hours" },
    { value: "1d", label: "1D", horizon: "3 trading days" },
];

function formatPrice(value: number | null | undefined, pair: Pair) {
    if (value == null) return "-";
    return value.toFixed(pair === "USDJPY" ? 3 : 5);
}

function statusCopy(status?: MarketData["data_status"]) {
    if (status === "live") return { label: "Live MT5", tone: "text-emerald-600 dark:text-emerald-400" };
    if (status === "market_closed") return { label: "Market closed", tone: "text-amber-600 dark:text-amber-400" };
    if (status === "delayed") return { label: "Delayed", tone: "text-amber-600 dark:text-amber-400" };
    if (status === "stale") return { label: "Stale", tone: "text-rose-600 dark:text-rose-400" };
    return { label: "Unavailable", tone: "text-muted-foreground" };
}

export default function TradingPage() {
    const chartRef = useRef<LiveMarketChartHandle>(null);
    const [pair, setPair] = useState<Pair>("EURUSD");
    const [timeframe, setTimeframe] = useState<Timeframe>("1h");
    const [market, setMarket] = useState<MarketData | null>(null);
    const [plan, setPlan] = useState<PlanStatus | null>(null);
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [positions, setPositions] = useState<Position[]>([]);
    const [chartLoading, setChartLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [capturing, setCapturing] = useState(false);
    const [capturedPreview, setCapturedPreview] = useState<string | null>(null);
    const [error, setError] = useState("");
    const [confirmTrade, setConfirmTrade] = useState(false);
    const [size, setSize] = useState("0.10");
    const [opening, setOpening] = useState(false);

    const loadPlan = useCallback(async () => {
        const response = await fetch("/api/market-intelligence/analyze", { cache: "no-store" });
        if (response.ok) setPlan(await response.json());
    }, []);

    const loadPositions = useCallback(async () => {
        const response = await fetch("/api/positions", { cache: "no-store" });
        if (response.ok) setPositions(await response.json());
    }, []);

    const loadMarket = useCallback(async () => {
        setChartLoading(true);
        setError("");
        try {
            const response = await fetch(
                `/api/market-intelligence/candles?pair=${pair}&timeframe=${timeframe}`,
                { cache: "no-store" },
            );
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Unable to load market data");
            setMarket(payload);
        } catch (reason) {
            setMarket(null);
            setError(reason instanceof Error ? reason.message : "Unable to load market data");
        } finally {
            setChartLoading(false);
        }
    }, [pair, timeframe]);

    useEffect(() => {
        void Promise.all([loadPlan(), loadPositions()]);
    }, [loadPlan, loadPositions]);

    useEffect(() => {
        setAnalysis(null);
        setCapturedPreview(null);
        setConfirmTrade(false);
        void loadMarket();
    }, [loadMarket]);

    async function analyze(useCapture: boolean) {
        setAnalyzing(true);
        setCapturing(useCapture);
        setError("");
        try {
            const screenshot = useCapture ? chartRef.current?.capture() ?? null : null;
            if (useCapture && !screenshot) {
                throw new Error("Could not capture the chart. Try refreshing.");
            }
            const response = await fetch("/api/market-intelligence/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pair, timeframe, screenshot }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Analysis failed");
            setAnalysis(payload);
            setCapturedPreview(useCapture ? screenshot : null);
            setPlan((current) => current ? { ...current, usage: payload.usage } : current);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Analysis failed");
        } finally {
            setAnalyzing(false);
            setCapturing(false);
        }
    }

    async function openPaperTrade() {
        if (!analysis) return;
        setOpening(true);
        setError("");
        try {
            const response = await fetch("/api/positions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    analysisId: analysis.analysisId,
                    size: Number(size),
                    stopLoss: analysis.levels.suggested_stop,
                    takeProfit: analysis.levels.suggested_target,
                }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Could not open paper trade");
            setConfirmTrade(false);
            await loadPositions();
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : "Could not open paper trade");
        } finally {
            setOpening(false);
        }
    }

    async function closePosition(position: Position) {
        const response = await fetch("/api/positions", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: position.id }),
        });
        if (response.ok) await loadPositions();
    }

    const sourceStatus = statusCopy(market?.data_status);
    const lockedPairs = allPairs.filter((item) => plan && !plan.pairs.includes(item));
    const marketReady = Boolean(market?.candles.length);
    const captureBlocked =
        !marketReady ||
        market?.data_status === "stale" ||
        market?.data_status === "unavailable" ||
        chartLoading;
    const captureBlockedReason = !marketReady
        ? "Wait for chart data to load"
        : chartLoading
            ? "Refreshing chart…"
            : market?.data_status === "stale"
                ? "Market data is stale — a vision read would waste your quota"
                : market?.data_status === "unavailable"
                    ? "Market data unavailable"
                    : null;
    const quotaExhausted = plan ? plan.usage.count >= plan.usage.limit : false;

    return (
        <TooltipProvider delayDuration={150}>
        <div className="flex min-h-full flex-col bg-background">
            <RBHeader
                title="Live Market Intelligence"
                subtitle="Real market charts with evidence-based decision support"
                right={
                    <div className="flex items-center gap-2 text-xs">
                        <span className={sourceStatus.tone}>{sourceStatus.label}</span>
                        <span className="text-muted-foreground">
                            {market?.latest_candle_at
                                ? new Date(market.latest_candle_at).toLocaleString()
                                : "No market timestamp"}
                        </span>
                    </div>
                }
            />

            <RBContent className="space-y-4">
                <div className="flex flex-col gap-3 border-b border-border pb-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex flex-wrap gap-1.5">
                        {allPairs.map((item) => {
                            const locked = lockedPairs.includes(item);
                            return (
                                <Button
                                    key={item}
                                    size="sm"
                                    variant={pair === item ? "default" : "outline"}
                                    disabled={locked}
                                    onClick={() => setPair(item)}
                                    className="min-w-24"
                                    title={locked ? "Upgrade your plan to unlock this pair" : undefined}
                                >
                                    {locked && <LockKeyhole className="mr-1 size-3" />}
                                    {item.slice(0, 3)}/{item.slice(3)}
                                </Button>
                            );
                        })}
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="flex rounded-md border border-border p-1">
                            {timeframes.map((item) => (
                                <button
                                    key={item.value}
                                    onClick={() => setTimeframe(item.value)}
                                    title={`Decision horizon: ${item.horizon}`}
                                    className={`h-8 min-w-12 px-3 text-xs font-semibold transition-colors ${
                                        timeframe === item.value
                                            ? "bg-primary text-primary-foreground"
                                            : "text-muted-foreground hover:text-foreground"
                                    }`}
                                >
                                    {item.label}
                                </button>
                            ))}
                        </div>
                        <Button variant="outline" size="icon" onClick={() => void loadMarket()} title="Refresh chart">
                            <RefreshCw className={`size-4 ${chartLoading ? "animate-spin" : ""}`} />
                        </Button>
                    </div>
                </div>

                {error && (
                    <div className="flex items-center gap-2 border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
                        <AlertTriangle className="size-4 shrink-0" />
                        {error}
                    </div>
                )}

                <div className="grid min-h-[590px] grid-cols-1 overflow-hidden border border-border bg-card xl:grid-cols-[minmax(0,1fr)_390px]">
                    <section className="min-w-0 border-b border-border xl:border-b-0 xl:border-r">
                        <div className="flex h-14 items-center justify-between border-b border-border px-4">
                            <div>
                                <div className="flex items-center gap-2">
                                    <strong className="text-sm">{pair.slice(0, 3)}/{pair.slice(3)}</strong>
                                    <span className="font-mono text-sm">{formatPrice(market?.latest_price, pair)}</span>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {timeframe.toUpperCase()} candles · EMA 21 · EMA 55
                                </p>
                            </div>
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    title="Download chart PNG"
                                    disabled={!market?.candles.length}
                                    onClick={() => chartRef.current?.download(`${pair}-${timeframe}.png`)}
                                >
                                    <Download className="size-4" />
                                </Button>
                            </div>
                        </div>
                        <div className="relative min-h-[520px]">
                            {chartLoading ? (
                                <div className="absolute inset-0 grid place-items-center">
                                    <LoaderCircle className="size-6 animate-spin text-primary" />
                                </div>
                            ) : market?.candles.length ? (
                                <LiveMarketChart ref={chartRef} candles={market.candles} height={520} />
                            ) : (
                                <div className="absolute inset-0 grid place-items-center text-sm text-muted-foreground">
                                    No real market candles available.
                                </div>
                            )}
                        </div>
                    </section>

                    <aside className="flex min-h-[590px] flex-col">
                        <div className="flex h-14 items-center justify-between border-b border-border px-4">
                            <div className="flex items-center gap-2">
                                <BrainCircuit className="size-4 text-primary" />
                                <strong className="text-sm">Intelligence</strong>
                            </div>
                            {plan && (
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Badge
                                            variant={quotaExhausted ? "destructive" : "outline"}
                                            className="cursor-help"
                                        >
                                            {plan.usage.count}/{plan.usage.limit} this month
                                        </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent side="bottom" className="max-w-[240px]">
                                        Each Analyze or Capture counts as one toward your monthly
                                        limit. Resets on the 1st.
                                    </TooltipContent>
                                </Tooltip>
                            )}
                        </div>

                        <div className="flex-1 space-y-4 overflow-y-auto p-4">
                            {!analysis && !analyzing && (
                                <div className="flex min-h-[360px] flex-col items-center justify-center text-center">
                                    <div className="mb-4 grid size-12 place-items-center rounded-full bg-primary/10 text-primary">
                                        <Sparkles className="size-5" />
                                    </div>
                                    <h2 className="text-base font-semibold">Analyze the current market</h2>
                                    <p className="mt-2 max-w-[290px] text-sm leading-6 text-muted-foreground">
                                        Trady evaluates exact prices, technical structure, market context,
                                        agent agreement, and held-out historical performance.
                                    </p>
                                </div>
                            )}

                            {analyzing && (
                                <div className="flex min-h-[360px] flex-col items-center justify-center text-center">
                                    <div className="mb-5 flex items-center gap-1">
                                        {[0, 1, 2].map((dot) => (
                                            <span
                                                key={dot}
                                                className="size-2 animate-bounce rounded-full bg-primary"
                                                style={{ animationDelay: `${dot * 140}ms` }}
                                            />
                                        ))}
                                    </div>
                                    <h2 className="text-sm font-semibold">
                                        {capturing ? "Reading chart and market evidence" : "Evaluating market evidence"}
                                    </h2>
                                    <p className="mt-2 text-xs text-muted-foreground">
                                        {capturing
                                            ? "Running vision model — this is slower than a plain analyze."
                                            : "This can take a moment on local models."}
                                    </p>
                                </div>
                            )}

                            {analysis && !analyzing && (
                                <>
                                    <div className={`border-l-4 p-4 ${
                                        analysis.action === "BUY"
                                            ? "border-emerald-500 bg-emerald-500/8"
                                            : analysis.action === "SELL"
                                                ? "border-rose-500 bg-rose-500/8"
                                                : "border-amber-500 bg-amber-500/8"
                                    }`}>
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-xs uppercase text-muted-foreground">Guidance</p>
                                                <div className="mt-1 flex items-center gap-2">
                                                    {analysis.action === "BUY" ? (
                                                        <TrendingUp className="size-5 text-emerald-500" />
                                                    ) : analysis.action === "SELL" ? (
                                                        <TrendingDown className="size-5 text-rose-500" />
                                                    ) : (
                                                        <Clock3 className="size-5 text-amber-500" />
                                                    )}
                                                    <strong className="text-2xl">{analysis.action}</strong>
                                                </div>
                                            </div>
                                            <div className="flex flex-col items-end gap-1">
                                                <Badge variant="outline">{analysis.horizon}</Badge>
                                                {analysis.captureUsed && (
                                                    <Badge variant="secondary" className="gap-1 text-[10px]">
                                                        <Camera className="size-3" />
                                                        +vision
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                        <p className="mt-3 text-sm leading-6">{analysis.explanation}</p>
                                    </div>

                                    <div className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border text-xs">
                                        {[
                                            ["Evidence", `${Math.round(analysis.agent_consensus.evidence_coverage * 100)}%`],
                                            ["Agent view", analysis.agent_consensus.direction],
                                            ["RSI 14", analysis.indicators.rsi_14?.toFixed(1) ?? "-"],
                                            ["ADX", analysis.indicators.adx?.toFixed(1) ?? "-"],
                                            ["Support", formatPrice(analysis.levels.support, pair)],
                                            ["Resistance", formatPrice(analysis.levels.resistance, pair)],
                                        ].map(([label, value]) => (
                                            <div key={label} className="bg-card p-3">
                                                <p className="text-muted-foreground">{label}</p>
                                                <p className="mt-1 font-mono font-semibold">{value}</p>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="border border-border p-3">
                                        <div className="flex items-center justify-between">
                                            <strong className="text-xs">Historical model check</strong>
                                            {analysis.forecast.available && (
                                                <Badge variant={analysis.forecast.validated ? "default" : "outline"}>
                                                    {analysis.forecast.validated ? "Passed" : "Not strong enough"}
                                                </Badge>
                                            )}
                                        </div>
                                        {analysis.forecast.available ? (
                                            <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                                                <p>
                                                    Direction: <span className="text-foreground">{analysis.forecast.direction}</span>
                                                </p>
                                                <p>
                                                    Held-out balanced accuracy:{" "}
                                                    <span className="text-foreground">
                                                        {Math.round((analysis.forecast.balanced_accuracy || 0) * 100)}%
                                                    </span>
                                                </p>
                                                <p>
                                                    Majority baseline:{" "}
                                                    {Math.round((analysis.forecast.majority_baseline || 0) * 100)}%
                                                </p>
                                            </div>
                                        ) : (
                                            <p className="mt-2 text-xs text-muted-foreground">
                                                Unavailable: {analysis.forecast.reason}
                                            </p>
                                        )}
                                    </div>

                                    {analysis.visual_observations && (
                                        <div className="border border-border p-3">
                                            <div className="flex items-center gap-2">
                                                <Camera className="size-3 text-primary" />
                                                <strong className="text-xs">Capture observations</strong>
                                            </div>
                                            {capturedPreview && (
                                                <img
                                                    src={capturedPreview}
                                                    alt="Captured chart sent to the vision model"
                                                    className="mt-2 w-full rounded border border-border"
                                                />
                                            )}
                                            <p className="mt-2 text-xs leading-5 text-muted-foreground">
                                                {analysis.visual_observations}
                                            </p>
                                        </div>
                                    )}

                                    {analysis.blockers.length > 0 && (
                                        <div className="space-y-2">
                                            {analysis.blockers.map((blocker) => (
                                                <div key={blocker} className="flex gap-2 text-xs text-amber-700 dark:text-amber-300">
                                                    <AlertTriangle className="mt-0.5 size-3 shrink-0" />
                                                    {blocker}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {(analysis.warnings ?? []).map((warning) => (
                                        <div key={warning} className="flex gap-2 text-xs text-amber-700 dark:text-amber-300">
                                            <Clock3 className="mt-0.5 size-3 shrink-0" />
                                            {warning}
                                        </div>
                                    ))}

                                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                                        <ShieldCheck className="size-3" />
                                        {analysis.data_source} · {new Date(analysis.market_timestamp).toLocaleString()}
                                    </div>
                                </>
                            )}
                        </div>

                        <div className="space-y-2 border-t border-border p-4">
                            {analysis?.approved_for_paper_trade && (
                                <Button className="w-full" onClick={() => setConfirmTrade(true)}>
                                    <Check className="mr-2 size-4" />
                                    Review paper trade
                                </Button>
                            )}
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <span className="block">
                                        <Button
                                            className="w-full"
                                            disabled={analyzing || !marketReady || quotaExhausted}
                                            onClick={() => void analyze(false)}
                                        >
                                            {analyzing && !capturing ? (
                                                <LoaderCircle className="mr-2 size-4 animate-spin" />
                                            ) : (
                                                <Sparkles className="mr-2 size-4" />
                                            )}
                                            Analyze
                                        </Button>
                                    </span>
                                </TooltipTrigger>
                                <TooltipContent side="top" className="max-w-[260px]">
                                    {quotaExhausted
                                        ? "Monthly limit reached — resets on the 1st."
                                        : "Numeric analysis on price, indicators, agents, and the held-out model. Fast and cheap. Costs 1 of your monthly quota."}
                                </TooltipContent>
                            </Tooltip>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <span className="block">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full text-xs"
                                            disabled={analyzing || captureBlocked || quotaExhausted}
                                            onClick={() => void analyze(true)}
                                        >
                                            {analyzing && capturing ? (
                                                <LoaderCircle className="mr-2 size-3.5 animate-spin" />
                                            ) : (
                                                <Camera className="mr-2 size-3.5" />
                                            )}
                                            Analyze with chart vision
                                        </Button>
                                    </span>
                                </TooltipTrigger>
                                <TooltipContent side="bottom" className="max-w-[260px]">
                                    {quotaExhausted
                                        ? "Monthly limit reached — resets on the 1st."
                                        : captureBlockedReason ??
                                            "Same analysis plus a vision-model read of the rendered chart (patterns, structure). Slower. Still costs 1 of your monthly quota."}
                                </TooltipContent>
                            </Tooltip>
                            <p className="text-center text-[10px] text-muted-foreground">
                                Educational decision support. Paper trades only.
                            </p>
                        </div>
                    </aside>
                </div>

                <section className="border border-border bg-card">
                    <div className="flex items-center justify-between border-b border-border px-4 py-3">
                        <div>
                            <h2 className="text-sm font-semibold">Open paper positions</h2>
                            <p className="text-xs text-muted-foreground">User-owned simulations created from approved analyses</p>
                        </div>
                        <Badge variant="outline">{positions.length} open</Badge>
                    </div>
                    {positions.length === 0 ? (
                        <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                            No open paper positions.
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[760px] text-left text-xs">
                                <thead className="text-muted-foreground">
                                    <tr className="border-b border-border">
                                        {["Pair", "Side", "Size", "Entry", "Current", "Stop", "Target", "Opened", ""].map((head) => (
                                            <th key={head} className="px-4 py-3 font-medium">{head}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {positions.map((position) => (
                                        <tr key={position.id} className="border-b border-border last:border-0">
                                            <td className="px-4 py-3 font-semibold">{position.pair}</td>
                                            <td className={`px-4 py-3 font-semibold ${position.side === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>
                                                {position.side}
                                            </td>
                                            <td className="px-4 py-3 font-mono">{position.size.toFixed(2)}</td>
                                            <td className="px-4 py-3 font-mono">{formatPrice(position.entryPrice, position.pair)}</td>
                                            <td className="px-4 py-3 font-mono">{formatPrice(market?.pair === position.pair ? market.latest_price : position.currentPrice, position.pair)}</td>
                                            <td className="px-4 py-3 font-mono">{formatPrice(position.stopLoss, position.pair)}</td>
                                            <td className="px-4 py-3 font-mono">{formatPrice(position.takeProfit, position.pair)}</td>
                                            <td className="px-4 py-3 text-muted-foreground">{new Date(position.openedAt).toLocaleString()}</td>
                                            <td className="px-4 py-3 text-right">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    title="Close position at current stored price"
                                                    disabled={market?.pair !== position.pair}
                                                    onClick={() => void closePosition(position)}
                                                >
                                                    <X className="size-4" />
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            </RBContent>

            {confirmTrade && analysis && (
                <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onMouseDown={() => setConfirmTrade(false)}>
                    <div
                        className="w-full max-w-md border border-border bg-background p-5 shadow-2xl"
                        onMouseDown={(event) => event.stopPropagation()}
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <h2 className="text-base font-semibold">Confirm paper trade</h2>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    No real order or money will be used.
                                </p>
                            </div>
                            <Button variant="ghost" size="icon" onClick={() => setConfirmTrade(false)}>
                                <X className="size-4" />
                            </Button>
                        </div>
                        <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                            <div className="border border-border p-3">
                                <p className="text-xs text-muted-foreground">Action</p>
                                <p className="mt-1 font-semibold">{analysis.action} {analysis.pair}</p>
                            </div>
                            <div className="border border-border p-3">
                                <p className="text-xs text-muted-foreground">Entry</p>
                                <p className="mt-1 font-mono font-semibold">{formatPrice(analysis.latest_price, pair)}</p>
                            </div>
                        </div>
                        <div className="mt-4 space-y-2">
                            <label htmlFor="paper-size" className="text-sm font-medium">
                                Position size (lots)
                            </label>
                            <Input
                                id="paper-size"
                                type="number"
                                min="0.01"
                                max="10"
                                step="0.01"
                                value={size}
                                onChange={(event) => setSize(event.target.value)}
                            />
                        </div>
                        <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                            <div>
                                <p className="text-muted-foreground">Suggested stop</p>
                                <p className="mt-1 font-mono">{formatPrice(analysis.levels.suggested_stop, pair)}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground">Suggested target</p>
                                <p className="mt-1 font-mono">{formatPrice(analysis.levels.suggested_target, pair)}</p>
                            </div>
                        </div>
                        <Button className="mt-5 w-full" disabled={opening || Number(size) <= 0} onClick={() => void openPaperTrade()}>
                            {opening ? <LoaderCircle className="mr-2 size-4 animate-spin" /> : <Check className="mr-2 size-4" />}
                            Open paper position
                        </Button>
                    </div>
                </div>
            )}
        </div>
        </TooltipProvider>
    );
}
