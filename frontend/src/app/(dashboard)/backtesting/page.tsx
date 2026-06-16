"use client";

import { useEffect, useMemo, useState } from "react";
import {
    Activity,
    AlertCircle,
    BarChart3,
    Loader2,
    Play,
    RefreshCw,
    Scale,
    Shield,
    TrendingUp,
} from "lucide-react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { RBContent, RBHeader } from "@/components/reactbits";
import { api } from "@/lib/api";
import type { BacktestResult, PositionSizingResponse } from "@/types";

const PAIR_OPTIONS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF"];
const LOOKBACK_OPTIONS = [200, 500, 1000, 1500];

function formatPair(pair: string) {
    return pair.length === 6 ? `${pair.slice(0, 3)}/${pair.slice(3)}` : pair;
}

function formatNumber(value: number | null | undefined, digits = 2) {
    if (value == null || Number.isNaN(value)) return "N/A";
    return value.toLocaleString(undefined, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

function metricTone(value: number, goodWhenPositive = true) {
    if (value === 0) return "text-slate-300";
    const good = goodWhenPositive ? value > 0 : value < 0;
    return good ? "text-emerald-400" : "text-rose-400";
}

function StatusMessage({ error }: { error: string }) {
    return (
        <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-100">
            <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{error}</span>
            </div>
        </div>
    );
}

function EmptyState({ text }: { text: string }) {
    return (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-8 text-center text-sm text-slate-400">
            {text}
        </div>
    );
}

export default function BacktestingPage() {
    const [tab, setTab] = useState<"backtest" | "sizing">("backtest");
    const [pair, setPair] = useState("EURUSD");
    const [lookbackBars, setLookbackBars] = useState(500);
    const [capital, setCapital] = useState(10000);
    const [confidence, setConfidence] = useState(0.75);
    const [backtest, setBacktest] = useState<BacktestResult | null>(null);
    const [sizing, setSizing] = useState<PositionSizingResponse | null>(null);
    const [loadingBacktest, setLoadingBacktest] = useState(false);
    const [loadingSizing, setLoadingSizing] = useState(false);
    const [backtestError, setBacktestError] = useState("");
    const [sizingError, setSizingError] = useState("");

    async function runBacktest() {
        setLoadingBacktest(true);
        setBacktestError("");
        try {
            const response = await api.v2.runBacktest(pair, lookbackBars);
            if (!response.success || !response.backtest) {
                throw new Error(response.error || "The backend did not return a backtest result.");
            }
            setBacktest(response.backtest);
        } catch (error) {
            setBacktest(null);
            setBacktestError(error instanceof Error ? error.message : "Unable to run backtest.");
        } finally {
            setLoadingBacktest(false);
        }
    }

    async function runSizing() {
        setLoadingSizing(true);
        setSizingError("");
        try {
            const response = await api.v2.positionSizing(pair, capital, confidence);
            if (!response.success || !response.sizing) {
                throw new Error(response.error || "The backend did not return a position sizing result.");
            }
            setSizing(response);
        } catch (error) {
            setSizing(null);
            setSizingError(error instanceof Error ? error.message : "Unable to calculate position size.");
        } finally {
            setLoadingSizing(false);
        }
    }

    useEffect(() => {
        void runBacktest();
        void runSizing();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const metrics = backtest?.metrics;
    const equityCurve = useMemo(
        () => backtest?.equity_curve.map((point) => ({
            ...point,
            equityLabel: `$${formatNumber(point.equity, 2)}`,
        })) ?? [],
        [backtest]
    );

    const metricCards = metrics ? [
        {
            label: "Total return",
            value: `${formatNumber(metrics.total_return_pct, 2)}%`,
            icon: TrendingUp,
            tone: metricTone(metrics.total_return_pct),
        },
        {
            label: "Win rate",
            value: `${formatNumber(metrics.win_rate_pct, 1)}%`,
            icon: Activity,
            tone: metricTone(metrics.win_rate_pct),
        },
        {
            label: "Sharpe ratio",
            value: formatNumber(metrics.sharpe_ratio, 2),
            icon: Shield,
            tone: metricTone(metrics.sharpe_ratio),
        },
        {
            label: "Max drawdown",
            value: `${formatNumber(metrics.max_drawdown_pct, 2)}%`,
            icon: BarChart3,
            tone: "text-rose-400",
        },
        {
            label: "Trades",
            value: String(metrics.total_trades),
            icon: RefreshCw,
            tone: "text-blue-300",
        },
        {
            label: "Profit factor",
            value: formatNumber(metrics.profit_factor, 2),
            icon: Scale,
            tone: metricTone(metrics.profit_factor - 1),
        },
    ] : [];

    return (
        <div className="flex h-full flex-col bg-background text-foreground">
            <RBHeader
                title="Backtesting & Position Sizing"
                subtitle="Real backend calculations from loaded market data"
                right={
                    <div className="flex gap-1 rounded-lg border border-white/10 bg-white/[0.04] p-1">
                        {[
                            { id: "backtest", label: "Backtesting" },
                            { id: "sizing", label: "Position sizing" },
                        ].map((item) => (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => setTab(item.id as "backtest" | "sizing")}
                                data-testid={`backtest-tab-${item.id}`}
                                className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                                    tab === item.id
                                        ? "bg-brand-blue-600 text-white"
                                        : "text-slate-400 hover:bg-white/[0.05] hover:text-white"
                                }`}
                            >
                                {item.label}
                            </button>
                        ))}
                    </div>
                }
            />

            <RBContent className="space-y-5">
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                    <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                        <label className="space-y-1.5">
                            <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Pair</span>
                            <select
                                value={pair}
                                onChange={(event) => setPair(event.target.value)}
                                className="h-10 w-full rounded-lg border border-white/10 bg-slate-900 px-3 text-sm text-white outline-none focus:border-brand-blue-500"
                            >
                                {PAIR_OPTIONS.map((option) => (
                                    <option key={option} value={option}>{formatPair(option)}</option>
                                ))}
                            </select>
                        </label>

                        {tab === "backtest" ? (
                            <label className="space-y-1.5">
                                <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Lookback bars</span>
                                <select
                                    value={lookbackBars}
                                    onChange={(event) => setLookbackBars(Number(event.target.value))}
                                    className="h-10 w-full rounded-lg border border-white/10 bg-slate-900 px-3 text-sm text-white outline-none focus:border-brand-blue-500"
                                >
                                    {LOOKBACK_OPTIONS.map((option) => (
                                        <option key={option} value={option}>{option}</option>
                                    ))}
                                </select>
                            </label>
                        ) : (
                            <div className="grid gap-3 sm:grid-cols-2">
                                <label className="space-y-1.5">
                                    <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Capital</span>
                                    <input
                                        type="number"
                                        min={100}
                                        step={100}
                                        value={capital}
                                        onChange={(event) => setCapital(Number(event.target.value))}
                                        className="h-10 w-full rounded-lg border border-white/10 bg-slate-900 px-3 text-sm text-white outline-none focus:border-brand-blue-500"
                                    />
                                </label>
                                <label className="space-y-1.5">
                                    <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Confidence</span>
                                    <input
                                        type="number"
                                        min={0.1}
                                        max={1}
                                        step={0.05}
                                        value={confidence}
                                        onChange={(event) => setConfidence(Number(event.target.value))}
                                        className="h-10 w-full rounded-lg border border-white/10 bg-slate-900 px-3 text-sm text-white outline-none focus:border-brand-blue-500"
                                    />
                                </label>
                            </div>
                        )}

                        <button
                            type="button"
                            onClick={() => tab === "backtest" ? void runBacktest() : void runSizing()}
                            disabled={loadingBacktest || loadingSizing}
                            className="inline-flex h-10 items-center justify-center gap-2 self-end rounded-lg bg-brand-blue-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-brand-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loadingBacktest || loadingSizing ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
                            {tab === "backtest" ? "Run backtest" : "Calculate size"}
                        </button>
                    </div>
                </div>

                {tab === "backtest" && (
                    <div className="space-y-5">
                        {backtestError && <StatusMessage error={backtestError} />}
                        {loadingBacktest && !backtest && <EmptyState text="Running real backend backtest..." />}
                        {!loadingBacktest && !backtest && !backtestError && <EmptyState text="Run a backtest to load real values." />}

                        {backtest && metrics && (
                            <>
                                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                                    {metricCards.map((card) => (
                                        <div key={card.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                                            <div className="mb-3 flex items-center justify-between">
                                                <span className="text-[11px] font-medium text-slate-400">{card.label}</span>
                                                <card.icon className="size-4 text-slate-500" />
                                            </div>
                                            <div className={`text-2xl font-bold ${card.tone}`}>{card.value}</div>
                                        </div>
                                    ))}
                                </div>

                                <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
                                    <section className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                                        <div className="mb-4">
                                            <h3 className="text-sm font-bold text-white">Equity curve</h3>
                                            <p className="text-[11px] text-slate-500">
                                                {formatPair(backtest.symbol)} · initial ${formatNumber(backtest.initial_capital, 2)} · final ${formatNumber(backtest.final_capital, 2)}
                                            </p>
                                        </div>
                                        {equityCurve.length > 0 ? (
                                            <ResponsiveContainer width="100%" height={300}>
                                                <AreaChart data={equityCurve}>
                                                    <defs>
                                                        <linearGradient id="real-equity" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.35} />
                                                            <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                                                    <XAxis dataKey="bar" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                                                    <YAxis tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} width={72} />
                                                    <Tooltip
                                                        contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, fontSize: 12 }}
                                                        formatter={(value) => [`$${formatNumber(Number(value), 2)}`, "Equity"]}
                                                        labelFormatter={(value) => `Bar ${value}`}
                                                    />
                                                    <Area type="monotone" dataKey="equity" stroke="#38bdf8" strokeWidth={2} fill="url(#real-equity)" />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        ) : (
                                            <EmptyState text="The backend returned no equity curve for this run." />
                                        )}
                                    </section>

                                    <section className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                                        <h3 className="mb-4 text-sm font-bold text-white">Backtest details</h3>
                                        <div className="grid grid-cols-2 gap-3 text-sm">
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Train bars</p>
                                                <p className="mt-1 font-semibold text-white">{backtest.train_bars}</p>
                                            </div>
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Test bars</p>
                                                <p className="mt-1 font-semibold text-white">{backtest.test_bars}</p>
                                            </div>
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Winning trades</p>
                                                <p className="mt-1 font-semibold text-emerald-300">{metrics.winning_trades}</p>
                                            </div>
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Losing trades</p>
                                                <p className="mt-1 font-semibold text-rose-300">{metrics.losing_trades}</p>
                                            </div>
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Avg win</p>
                                                <p className="mt-1 font-semibold text-emerald-300">${formatNumber(metrics.avg_win, 2)}</p>
                                            </div>
                                            <div className="rounded-lg bg-white/[0.04] p-3">
                                                <p className="text-[10px] uppercase tracking-widest text-slate-500">Avg loss</p>
                                                <p className="mt-1 font-semibold text-rose-300">${formatNumber(metrics.avg_loss, 2)}</p>
                                            </div>
                                        </div>
                                    </section>
                                </div>

                                <section className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                                    <h3 className="mb-4 text-sm font-bold text-white">Simulated trades</h3>
                                    {backtest.trades.length > 0 ? (
                                        <div className="overflow-x-auto">
                                            <table className="w-full min-w-[680px] text-left text-sm">
                                                <thead className="text-[10px] uppercase tracking-widest text-slate-500">
                                                    <tr className="border-b border-white/10">
                                                        <th className="py-2">Side</th>
                                                        <th className="py-2">Entry</th>
                                                        <th className="py-2">Exit</th>
                                                        <th className="py-2">P&L</th>
                                                        <th className="py-2">Pips</th>
                                                        <th className="py-2">Confidence</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {backtest.trades.map((trade, index) => (
                                                        <tr key={`${trade.type}-${trade.entry_price}-${index}`} className="border-b border-white/[0.06] last:border-0">
                                                            <td className="py-3">
                                                                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                                                                    trade.type === "BUY" ? "bg-emerald-500/15 text-emerald-300" : "bg-rose-500/15 text-rose-300"
                                                                }`}>
                                                                    {trade.type}
                                                                </span>
                                                            </td>
                                                            <td className="py-3 text-slate-200">{formatNumber(trade.entry_price, 5)}</td>
                                                            <td className="py-3 text-slate-200">{formatNumber(trade.exit_price, 5)}</td>
                                                            <td className={`py-3 font-semibold ${metricTone(trade.pnl)}`}>${formatNumber(trade.pnl, 2)}</td>
                                                            <td className={`py-3 font-semibold ${metricTone(trade.pnl_pips)}`}>{formatNumber(trade.pnl_pips, 1)}</td>
                                                            <td className="py-3 text-slate-300">{formatNumber(trade.confidence * 100, 1)}%</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <EmptyState text="The backend returned no simulated trades for this run." />
                                    )}
                                </section>
                            </>
                        )}
                    </div>
                )}

                {tab === "sizing" && (
                    <div className="space-y-5">
                        {sizingError && <StatusMessage error={sizingError} />}
                        {loadingSizing && !sizing && <EmptyState text="Calculating position size from backend market data..." />}
                        {!loadingSizing && !sizing && !sizingError && <EmptyState text="Calculate size to load real risk values." />}

                        {sizing?.sizing && (
                            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                {[
                                    { label: "Lot size", value: `${formatNumber(sizing.sizing.lot_size, 2)} lots`, tone: "text-blue-300" },
                                    { label: "Risk amount", value: `$${formatNumber(sizing.sizing.risk_amount, 2)}`, tone: "text-amber-300" },
                                    { label: "Risk percent", value: `${formatNumber(sizing.sizing.risk_pct, 2)}%`, tone: "text-rose-300" },
                                    { label: "Kelly fraction", value: `${formatNumber(sizing.sizing.kelly_fraction * 100, 2)}%`, tone: "text-emerald-300" },
                                    { label: "ATR used", value: formatNumber(sizing.atr_used, 6), tone: "text-slate-200" },
                                    { label: "ATR size", value: `${formatNumber(sizing.sizing.atr_size, 2)} lots`, tone: "text-violet-300" },
                                    { label: "Stop loss", value: `${formatNumber(sizing.sizing.stop_loss_pips, 1)} pips`, tone: "text-rose-300" },
                                    { label: "Take profit", value: `${formatNumber(sizing.sizing.take_profit_pips, 1)} pips`, tone: "text-emerald-300" },
                                ].map((item) => (
                                    <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
                                        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{item.label}</p>
                                        <p className={`mt-3 text-2xl font-bold ${item.tone}`}>{item.value}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </RBContent>
        </div>
    );
}
