"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
    Brain, TrendingUp, Newspaper, Layers, Zap, Globe, Activity,
    RefreshCw, AlertCircle, CheckCircle2, Database,
    Loader2, CheckCheck, XCircle, ChevronDown,
} from "lucide-react";
import { api } from "@/lib/api";
import type { MasterSignalResponse, HealthCheckV2, DriftDetectionV2 } from "@/types";
import {
    FadeInUp, StaggerContainer, StaggerItem,
    SpotlightCard, GlowDot, AnimatedProgressBar, FloatingCard,
} from "@/components/animations";
import { FreshnessHealthCard } from "@/components/freshness-health-card";
import { RBContent, RBHeader } from "@/components/reactbits";
import { XaiBreakdown } from "@/components/xai-breakdown";
import { JudgeDecisionCard } from "@/components/judge-decision-card";
import { ActuarialMetrics } from "@/components/actuarial-metrics";

// Agent configs — keys must match backend xai.agent_breakdown keys
const AGENTS = {
    TechnicalV2: {
        icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10",
        border: "border-emerald-500/20", gradient: "from-emerald-500 to-teal-500",
        name: "Technical Agent", dso: "Price evidence",
        description: "RSI - MACD - Bollinger Bands - moving averages - 1H/4H/1D confluence",
        weight: 35,
        bio: "Builds aligned 1-hour, 4-hour, and daily views from the same OHLC history, then combines deterministic momentum and trend rules.",
        colorKey: "emerald" as const,
    },
    MacroV2: {
        icon: Brain, color: "text-blue-400", bg: "bg-blue-500/10",
        border: "border-blue-500/20", gradient: "from-blue-500 to-indigo-500",
        name: "Macro Agent", dso: "Economic evidence",
        description: "Policy-rate differential - inflation differential - rate momentum - carry",
        weight: 25,
        bio: "Compares the two currencies using available policy rates, inflation, rate momentum, and volatility-adjusted carry.",
        colorKey: "blue" as const,
    },
    SentimentV2: {
        icon: Newspaper, color: "text-amber-400", bg: "bg-amber-500/10",
        border: "border-amber-500/20", gradient: "from-amber-500 to-orange-500",
        name: "Sentiment Agent", dso: "News evidence",
        description: "Recent financial news - relevance weighting - time decay - agreement",
        weight: 20,
        bio: "Aggregates recent currency-relevant financial news with recency and relevance weighting. It does not currently use social feeds or COT positioning.",
        colorKey: "amber" as const,
    },
    GeopoliticalV2: {
        icon: Globe, color: "text-violet-400", bg: "bg-violet-500/10",
        border: "border-violet-500/20", gradient: "from-violet-500 to-purple-500",
        name: "Geopolitical Agent", dso: "Event-risk evidence",
        description: "Global headlines - stored news fallback - risk-off / risk-on scoring",
        weight: 20,
        bio: "Maps global headline risk language to safe-haven and risk-currency pressure using transparent keyword rules and source fallbacks.",
        colorKey: "violet" as const,
    },
};

const PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF"];

type SourceState = "idle" | "running" | "done" | "error";

type IngestMethod = "refreshNews" | "refreshOhlcv" | "refreshMacro" | "refreshMt5" | "refreshGeopolitical";
type SourceKey = "news" | "ohlcv" | "macro" | "mt5" | "geopolitical";

const INGEST_SOURCES: ReadonlyArray<{
    key: SourceKey;
    label: string;
    description: string;
    icon: typeof Newspaper;
    color: string;
    method: IngestMethod;
}> = [
    {
        key: "news",
        label: "News",
        description: "Forex headlines → Sentiment Agent",
        icon: Newspaper,
        color: "text-amber-400",
        method: "refreshNews",
    },
    {
        key: "ohlcv",
        label: "OHLCV (yfinance)",
        description: "Free hourly candles, no API key",
        icon: TrendingUp,
        color: "text-emerald-400",
        method: "refreshOhlcv",
    },
    {
        key: "mt5",
        label: "MT5 OHLCV",
        description: "Live broker bars → Live Intelligence",
        icon: Activity,
        color: "text-cyan-400",
        method: "refreshMt5",
    },
    {
        key: "macro",
        label: "Macro",
        description: "FRED rates, inflation, carry",
        icon: Brain,
        color: "text-blue-400",
        method: "refreshMacro",
    },
    {
        key: "geopolitical",
        label: "Geopolitical",
        description: "Risk-event headlines → Geo Agent",
        icon: Globe,
        color: "text-violet-400",
        method: "refreshGeopolitical",
    },
];

interface IngestDataButtonProps {
    /** Fires every time a source completes (success OR error). Useful to refresh dependent panels. */
    onSourceComplete?: (source: SourceKey, ok: boolean) => void;
}

function IngestDataButton({ onSourceComplete }: IngestDataButtonProps) {
    const [open, setOpen] = useState(false);
    const initial: Record<string, SourceState> = {};
    const initialMsg: Record<string, string> = {};
    INGEST_SOURCES.forEach((s) => { initial[s.key] = "idle"; initialMsg[s.key] = ""; });
    const [states, setStates] = useState<Record<string, SourceState>>(initial);
    const [messages, setMessages] = useState<Record<string, string>>(initialMsg);
    const panelRef = useRef<HTMLDivElement>(null);

    // Close on click-outside
    useEffect(() => {
        if (!open) return;
        function handleClick(e: MouseEvent) {
            if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, [open]);

    const triggerSource = async (key: SourceKey, method: IngestMethod) => {
        setStates((s) => ({ ...s, [key]: "running" }));
        setMessages((m) => ({ ...m, [key]: "Starting…" }));
        try {
            // Snapshot the current last_run BEFORE triggering so we can detect
            // when the backend records a NEW completion (vs a stale scheduler run).
            let previousLastRun: string | null = null;
            try {
                const pre = await api.dataIngest.status();
                previousLastRun = pre?.sources?.[key]?.last_run ?? null;
            } catch { /* ignore — worst case we skip the guard */ }

            const startRes = await api.dataIngest[method]();
            if (startRes?.status === "already_running") {
                setMessages((m) => ({ ...m, [key]: "Already running" }));
                // Still poll for completion instead of returning
            }

            // Poll the status endpoint until the job completes (max 120s — MT5
            // and geopolitical paths can be slower than the 90 s baseline).
            const deadline = Date.now() + 120_000;
            await new Promise((r) => setTimeout(r, 2000)); // initial 2s grace
            while (Date.now() < deadline) {
                try {
                    const statusData = await api.dataIngest.status();
                    const src = statusData?.sources?.[key];
                    // Job is done when: not running AND last_run changed from what it
                    // was before we triggered (guards against stale scheduler results).
                    const isNewRun = src?.last_run !== null && src?.last_run !== previousLastRun;
                    if (src && !src.running && isNewRun) {
                        const res = src.last_result as Record<string, unknown> | string | null;
                        // Parse result for display
                        let msg = "Done";
                        let finalState: SourceState = "done";
                        if (typeof res === "string" && res.startsWith("error:")) {
                            finalState = "error";
                            msg = res.replace("error:", "").trim().slice(0, 50);
                        } else if (res && typeof res === "object") {
                            const errors = (res.errors as string[] | undefined) ?? [];
                            const inserted = res.inserted as number | undefined;
                            const skipped = res.skipped as number | undefined;
                            if (errors.length > 0) {
                                finalState = inserted && inserted > 0 ? "done" : "error";
                                msg = (inserted && inserted > 0)
                                    ? `+${inserted} records · ${errors[0].slice(0, 40)}`
                                    : errors[0].slice(0, 60);
                            } else if (inserted !== undefined) {
                                msg = inserted > 0
                                    ? `+${inserted} records`
                                    : skipped ? `Up to date (${skipped} checked)` : "Up to date";
                            }
                        }
                        setStates((s) => ({ ...s, [key]: finalState }));
                        setMessages((m) => ({ ...m, [key]: msg }));
                        setTimeout(() => setStates((s) => ({ ...s, [key]: "idle" })), 8000);
                        // Notify parent so it can re-pull derived panels (Data Freshness, etc.)
                        try { onSourceComplete?.(key, finalState !== "error"); } catch { /* swallow */ }
                        return;
                    }
                    // Still running — update message with progress hint
                    if (src?.running) {
                        setMessages((m) => ({ ...m, [key]: "Fetching…" }));
                    }
                } catch { /* ignore transient poll errors */ }
                await new Promise((r) => setTimeout(r, 3000));
            }
            // Timeout — job still running after deadline
            setStates((s) => ({ ...s, [key]: "done" }));
            setMessages((m) => ({ ...m, [key]: "Running (long job)" }));
            setTimeout(() => setStates((s) => ({ ...s, [key]: "idle" })), 8000);
            try { onSourceComplete?.(key, true); } catch { /* swallow */ }
        } catch (err) {
            setStates((s) => ({ ...s, [key]: "error" }));
            setMessages((m) => ({ ...m, [key]: err instanceof Error ? err.message.slice(0, 50) : "Request failed" }));
            setTimeout(() => setStates((s) => ({ ...s, [key]: "idle" })), 8000);
            try { onSourceComplete?.(key, false); } catch { /* swallow */ }
        }
    };

    const refreshAll = () => {
        // Per-source triggers in parallel — each one snapshots its own
        // last_run, calls its endpoint, then polls until it completes. The
        // backend already runs each collector in its own daemon thread, so
        // there is no benefit to also batching them into a single HTTP call.
        INGEST_SOURCES.forEach(({ key, method }) => {
            if (states[key] !== "running") void triggerSource(key, method);
        });
    };

    const anyRunning = Object.values(states).some((s) => s === "running");

    const stateIcon = (s: SourceState) => {
        if (s === "running") return <Loader2 className="size-3.5 animate-spin text-slate-400" />;
        if (s === "done")    return <CheckCheck className="size-3.5 text-emerald-400" />;
        if (s === "error")   return <XCircle className="size-3.5 text-rose-400" />;
        return null;
    };

    return (
        <div className="relative" ref={panelRef}>
            <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setOpen((o) => !o)}
                data-testid="ingest-data-btn"
                className="flex items-center gap-2 px-3 py-2 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-300 text-sm font-semibold hover:bg-violet-500/20 transition-all"
            >
                {anyRunning ? <Loader2 className="size-4 animate-spin" /> : <Database className="size-4" />}
                Ingest Data
                <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
            </motion.button>

            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: -8, scale: 0.96 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -8, scale: 0.96 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 top-full mt-2 w-80 z-50 rounded-xl border border-white/10 bg-slate-900 shadow-2xl shadow-black/50 overflow-hidden"
                    >
                        <div className="p-3 border-b border-white/5">
                            <p className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Data Ingestion</p>
                            <p className="text-[10px] text-slate-600 mt-0.5">Each refresh feeds a specific panel of the site</p>
                        </div>

                        <div className="p-2 space-y-1">
                            {INGEST_SOURCES.map(({ key, label, description, icon: Icon, color, method }) => (
                                <div
                                    key={key}
                                    title={description}
                                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-white/[0.03]"
                                >
                                    <Icon className={`size-3.5 flex-shrink-0 ${color}`} />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-slate-300 truncate">{label}</span>
                                            {stateIcon(states[key])}
                                        </div>
                                        <div className="text-[10px] text-slate-600 truncate">
                                            {messages[key] || description}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => triggerSource(key, method)}
                                        disabled={states[key] === "running"}
                                        data-testid={`refresh-${key}-btn`}
                                        className="ml-1 px-2 py-1 rounded-md text-[10px] font-semibold border border-white/10 bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                    >
                                        Refresh
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="p-2 border-t border-white/5">
                            <button
                                onClick={refreshAll}
                                disabled={anyRunning}
                                data-testid="refresh-all-btn"
                                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 text-xs font-semibold hover:bg-violet-600/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                {anyRunning ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
                                Refresh All Sources
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function SignalLabContent() {
    const searchParams = useSearchParams();
    const [signal, setSignal] = useState<MasterSignalResponse | null>(null);
    const [health, setHealth] = useState<HealthCheckV2 | null>(null);
    const [drift, setDrift]   = useState<DriftDetectionV2 | null>(null);
    const [loading, setLoading] = useState(false);
    const [signalError, setSignalError] = useState<string | null>(null);
    const [pair, setPair] = useState(searchParams.get("pair") || "EURUSD");
    // Bumped every time an ingest source completes; forces the freshness card
    // and the system-status row to re-fetch immediately instead of waiting
    // for their respective intervals.
    const [freshnessKey, setFreshnessKey] = useState(0);

    const loadData = async () => {
        try {
            const [h, d] = await Promise.all([api.v2.healthCheck(), api.v2.driftDetection()]) as [HealthCheckV2, DriftDetectionV2];
            setHealth(h); setDrift(d);
        } catch {}
    };

    const generateSignal = async () => {
        setLoading(true);
        setSignalError(null);
        try {
            const s = await api.generateMaster(pair);
            setSignal(s);
            await loadData();
        } catch (error) {
            setSignalError(error instanceof Error ? error.message : "Signal generation timed out.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); const t = setInterval(loadData, 30000); return () => clearInterval(t); }, []);

    return (
        <div className="flex h-full flex-col bg-background text-foreground" data-tour="agents-lab">
            <RBHeader
                title="Signal Lab"
                subtitle="Evidence-weighted currency analysis with explicit safety gates"
                right={
                    <>
                        <div className="flex gap-1">
                            {PAIRS.map((p) => (
                                <button
                                    key={p}
                                    onClick={() => setPair(p)}
                                    data-testid={`pair-${p}`}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                                        pair === p
                                            ? "bg-brand-blue-600 text-white shadow-lg shadow-brand-blue-500/30"
                                            : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                                    }`}
                                >
                                    {p.slice(0,3)}/{p.slice(3)}
                                </button>
                            ))}
                        </div>
                        <IngestDataButton
                            onSourceComplete={() => {
                                setFreshnessKey((k) => k + 1);
                                void loadData();
                            }}
                        />
                        <motion.button
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            onClick={generateSignal}
                            disabled={loading}
                            data-testid="generate-signal-btn"
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-brand-blue-600 to-brand-blue-700 text-white text-sm font-semibold shadow-lg shadow-brand-blue-500/30 hover:shadow-brand-blue-500/50 transition-all disabled:opacity-60"
                        >
                            {loading
                                ? <><RefreshCw className="size-4 animate-spin" /> Analyzing...</>
                                : <><Zap className="size-4" /> Generate Signal</>
                            }
                        </motion.button>
                    </>
                }
            />

            <RBContent className="space-y-6">

                {signalError && (
                    <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <span>{signalError}</span>
                        <button
                            onClick={generateSignal}
                            disabled={loading}
                            data-testid="signal-retry-btn"
                            className="inline-flex items-center gap-2 rounded-md border border-rose-400/30 bg-rose-500/20 px-3 py-1.5 text-xs font-semibold text-rose-100 hover:bg-rose-500/30 disabled:opacity-50"
                        >
                            <RefreshCw className={`size-3 ${loading ? "animate-spin" : ""}`} />
                            Retry
                        </button>
                    </div>
                )}

                {/* System Status (DSO3.1) */}
                {health && (
                    <FadeInUp>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {[
                                { label: "Evidence health", value: health.status.toUpperCase(), dot: health.status === "operational" ? "emerald" as const : "amber" as const, sub: "Based on source freshness" },
                                { label: "Uptime", value: `${Math.round(health.system.uptime_seconds/60)}m`, dot: "blue" as const, sub: "Since this API process started" },
                                { label: "Configured agents", value: `${Object.keys(AGENTS).length}`, dot: "violet" as const, sub: "Readiness depends on current evidence" },
                                { label: "Drift detected", value: drift?.sentiment_drift?.detected ? "YES" : "NO", dot: drift?.sentiment_drift?.detected ? "amber" as const : "emerald" as const, sub: "Distribution detection" },
                            ].map((item, i) => (
                                <motion.div key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.06}}
                                    className="p-3 rounded-xl border border-white/5 bg-white/[0.03]">
                                    <div className="flex items-center gap-1.5 mb-1">
                                        <GlowDot color={item.dot} />
                                        <span className="text-[10px] text-slate-500 uppercase tracking-wider">{item.label}</span>
                                    </div>
                                    <div className="text-base font-bold text-white">{item.value}</div>
                                    <div className="text-[10px] text-slate-600">{item.sub}</div>
                                </motion.div>
                            ))}
                        </div>
                    </FadeInUp>
                )}

                {/* Agent Cards (DSO1.1 + DSO1.2 + DSO1.3) */}
                <div>
                    <FadeInUp delay={0.1}>
                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">
                            Evidence-weighted agent ensemble
                        </h3>
                    </FadeInUp>
                    <StaggerContainer staggerDelay={0.1} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {Object.entries(AGENTS).map(([key, agent]) => {
                            const perf = health?.agent_performances?.[key as keyof typeof health.agent_performances];
                            const vote = signal?.xai?.agent_breakdown?.[key];
                            const spotlightRgb = key === "TechnicalV2" ? "16,185,129" : key === "MacroV2" ? "59,130,246" : key === "SentimentV2" ? "245,158,11" : "139,92,246";
                            return (
                                <StaggerItem key={key}>
                                    <SpotlightCard
                                        className={`rounded-xl border ${agent.border} bg-white/[0.03] p-5 h-full`}
                                        spotlightColor={`rgba(${spotlightRgb},0.1)`}
                                    >
                                        <div className="flex items-center justify-between mb-3">
                                            <div className="flex items-center gap-2.5">
                                                <div className={`p-2 rounded-lg bg-gradient-to-br ${agent.gradient} shadow-lg`}>
                                                    <agent.icon className="size-4 text-white" />
                                                </div>
                                                <div>
                                                    <div className="text-sm font-bold text-white">{agent.name}</div>
                                                    <div className={`text-[10px] font-mono ${agent.color}`}>{agent.dso}</div>
                                                </div>
                                            </div>
                                            <div className={`text-xs font-bold ${agent.color}`}>{vote ? `${(vote.weight * 100).toFixed(0)}%` : `${agent.weight}%`}</div>
                                        </div>

                                        <p className="text-[11px] text-slate-500 leading-relaxed mb-3">{agent.bio}</p>

                                        <div className="mb-3">
                                            <div className="flex items-center justify-between text-[10px] text-slate-600 mb-1">
                                                <span>{vote ? "Effective weight" : "Prior weight"}</span>
                                                <span className={agent.color}>{vote ? `${(vote.weight * 100).toFixed(0)}%` : `${agent.weight}%`}</span>
                                            </div>
                                            <AnimatedProgressBar value={vote ? vote.weight * 100 : agent.weight} color={agent.colorKey} height={3} />
                                        </div>

                                        <div className="text-[10px] text-slate-600 font-mono">{agent.description}</div>

                                        {/* Vote result */}
                                        {vote && (
                                            <div className="mt-3 pt-3 border-t border-white/5">
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                                        vote.signal === "BUY" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                                        : vote.signal === "SELL" ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                                        : "bg-slate-500/15 text-slate-400 border-slate-500/30"
                                                    }`}>
                                                        {vote.signal}
                                                    </span>
                                                    <span className="text-xs font-bold text-white">{(vote.confidence * 100).toFixed(0)}%</span>
                                                </div>
                                                <AnimatedProgressBar value={vote.confidence * 100} color={agent.colorKey} height={3} />
                                                <p className="text-[10px] text-slate-500 mt-2 leading-relaxed line-clamp-3">{vote.reasoning}</p>
                                                <div className="mt-2 flex items-center justify-between text-[10px] text-slate-600">
                                                    <span>Evidence quality</span>
                                                    <span className={agent.color}>{Math.round((vote.data_quality ?? 0) * 100)}%</span>
                                                </div>
                                                {/* Geopolitical key events */}
                                                {vote.key_events && vote.key_events.length > 0 && (
                                                    <div className="mt-2 space-y-1">
                                                        {vote.key_events.slice(0, 2).map((e, i) => (
                                                            <div key={i} className="text-[10px] text-violet-400/80 truncate">• {e}</div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {/* Performance */}
                                        {perf && perf.total_signals > 0 ? (
                                            <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-3 gap-2 text-center text-[10px]">
                                                <div>
                                                    <div className="text-emerald-400 font-bold">{(perf.win_rate * 100).toFixed(1)}%</div>
                                                    <div className="text-slate-600">Win Rate</div>
                                                </div>
                                                <div>
                                                    <div className="text-white font-bold">{perf.sharpe_ratio.toFixed(2)}</div>
                                                    <div className="text-slate-600">Sharpe</div>
                                                </div>
                                                <div>
                                                    <div className="text-rose-400 font-bold">{(perf.max_drawdown * 100).toFixed(1)}%</div>
                                                    <div className="text-slate-600">Max DD</div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="mt-3 pt-3 border-t border-white/5 text-[10px] text-slate-600">
                                                Performance unavailable until a paper-trade outcome is settled.
                                            </div>
                                        )}
                                    </SpotlightCard>
                                </StaggerItem>
                            );
                        })}
                    </StaggerContainer>
                </div>

                {/* Data Freshness Monitoring (DSO3.1) */}
                <FadeInUp delay={0.2}>
                    <FreshnessHealthCard refreshInterval={300} refreshKey={freshnessKey} />
                </FadeInUp>

                {/* Final Signal — Pipeline Decision (DSO2.1 + DSO3.1) */}
                <AnimatePresence>
                    {signal?.success && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="space-y-4"
                        >
                            {/* Summary banner */}
                            <div className={`rounded-xl border p-5 ${
                                signal.signal.direction === "BUY"
                                    ? "border-emerald-500/30 bg-emerald-500/5"
                                    : signal.signal.direction === "SELL"
                                    ? "border-rose-500/30 bg-rose-500/5"
                                    : "border-slate-500/30 bg-white/[0.03]"
                            }`}>
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <Layers className="size-4 text-violet-400" />
                                            <h3 className="text-sm font-bold text-white">Pipeline Decision — {signal.pair}</h3>
                                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                                signal.decision === "APPROVED" || signal.decision === "APPROVED_MODIFIED"
                                                    ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                                                    : signal.decision === "REJECTED"
                                                    ? "border-rose-500/30 text-rose-400 bg-rose-500/10"
                                                    : "border-amber-500/30 text-amber-400 bg-amber-500/10"
                                            }`}>{signal.decision}</span>
                                        </div>
                                        <p className="text-[11px] text-slate-500">Evidence aggregation → expectancy check → validation → risk controls → explanation</p>
                                    </div>
                                    <span className={`px-5 py-2 rounded-xl text-2xl font-bold border ${
                                        signal.signal.direction === "BUY" ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                                        : signal.signal.direction === "SELL" ? "border-rose-500/30 text-rose-400 bg-rose-500/10"
                                        : "border-slate-500/30 text-slate-400"
                                    }`}>{signal.signal.direction}</span>
                                </div>

                                <div className="grid grid-cols-3 gap-3">
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Confidence</div>
                                        <div className="text-xl font-bold text-white">{(signal.signal.confidence * 100).toFixed(0)}%</div>
                                        <AnimatedProgressBar value={signal.signal.confidence * 100} color="violet" height={3} className="mt-2" />
                                    </div>
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Weighted Score</div>
                                        <div className="text-xl font-bold text-white">{signal.coordinator.weighted_score.toFixed(3)}</div>
                                        <div className="text-[10px] text-slate-600 mt-1">
                                            {signal.coordinator.weight_metadata
                                                ? `${Math.round(signal.coordinator.weight_metadata.evidence_coverage * 100)}% evidence coverage`
                                                : "Coordinator output"}
                                        </div>
                                    </div>
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Market Regime</div>
                                        <div className="text-base font-bold text-white capitalize">{signal.coordinator.market_regime}</div>
                                        <div className="text-[10px] text-slate-600 mt-1">Current context</div>
                                    </div>
                                </div>

                                {signal.coordinator.conflicts_detected && signal.coordinator.conflict_description && (
                                    <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                        <div className="flex items-center gap-2 mb-1">
                                            <AlertCircle className="size-3.5 text-amber-400" />
                                            <span className="text-[11px] font-bold text-amber-400">Inter-agent conflict detected</span>
                                        </div>
                                        <p className="text-[11px] text-amber-300/80">{signal.coordinator.conflict_description}</p>
                                    </div>
                                )}

                                {(signal.decision === "REJECTED" || signal.decision === "BLOCKED") && signal.rejection?.reason && (
                                    <div className="mt-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
                                        <div className="text-[10px] text-slate-500 mb-1">Rejection — stage: {signal.rejection.stage}</div>
                                        <p className="text-[11px] text-rose-300">{signal.rejection.reason}</p>
                                    </div>
                                )}

                                {signal.geopolitical_events && signal.geopolitical_events.length > 0 && (
                                    <div className="mt-3 p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
                                        <div className="text-[10px] font-bold text-violet-400 mb-2">🌍 Geopolitical Events</div>
                                        <ul className="space-y-1">
                                            {signal.geopolitical_events.slice(0, 4).map((e, i) => (
                                                <li key={i} className="text-[10px] text-violet-300/80 truncate">• {e}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            <JudgeDecisionCard
                                verdict={signal.judge.verdict}
                                reasoning={signal.judge.reasoning}
                                latencyMs={signal.judge.latency_ms}
                                fromCache={signal.judge.from_cache}
                                confidence={signal.signal.confidence}
                            />

                            <ActuarialMetrics
                                actuarial={signal.actuarial}
                                executionPlan={signal.execution_plan}
                            />

                            <XaiBreakdown
                                agentBreakdown={signal.xai.agent_breakdown}
                                explanation={typeof signal.xai.human_explanation === 'object' ? Object.values(signal.xai.human_explanation).join(' ') : undefined}
                                pair={signal.pair}
                            />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Empty state */}
                {!signal && !loading && (
                    <FloatingCard delay={0.2}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-12 text-center">
                            <div className="p-4 rounded-2xl bg-gradient-to-br from-violet-500/20 to-blue-500/10 w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                                <Layers className="size-10 text-violet-400" />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-2">Signal Lab Ready</h3>
                            <p className="text-sm text-slate-500 mb-6 max-w-md mx-auto">
                                Select a currency pair and click <strong className="text-violet-400">Generate Signal</strong> to run the multi-agent system.
                            </p>
                            <div className="flex flex-wrap gap-2 justify-center text-[11px] text-slate-600">
                                <span className="px-2 py-1 rounded border border-blue-500/20 bg-blue-500/5">Macro differentials</span>
                                <span className="px-2 py-1 rounded border border-emerald-500/20 bg-emerald-500/5">Multi-timeframe price rules</span>
                                <span className="px-2 py-1 rounded border border-amber-500/20 bg-amber-500/5">News sentiment</span>
                                <span className="px-2 py-1 rounded border border-violet-500/20 bg-violet-500/5">Event risk</span>
                                <span className="px-2 py-1 rounded border border-rose-500/20 bg-rose-500/5">Conflict and risk controls</span>
                            </div>
                        </div>
                    </FloatingCard>
                )}
            </RBContent>
        </div>
    );
}

export default function AgentsPage() {
    return (
        <Suspense fallback={<div className="flex h-full items-center justify-center bg-background text-muted-foreground">Loading...</div>}>
            <SignalLabContent />
        </Suspense>
    );
}


