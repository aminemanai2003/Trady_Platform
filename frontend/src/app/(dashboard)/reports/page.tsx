"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
    Activity,
    AlertTriangle,
    Brain,
    CheckCircle2,
    Download,
    Filter,
    Layers,
    LineChart as LineChartIcon,
    Newspaper,
    ShieldX,
    TrendingDown,
    TrendingUp,
    Users,
    XCircle,
} from "lucide-react";
import {
    FadeInUp,
    StaggerContainer,
    StaggerItem,
    AnimatedCounter,
    AnimatedProgressBar,
    FloatingCard,
} from "@/components/animations";
import { RBContent, RBHeader } from "@/components/reactbits";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import type {
    ReportAgentStat,
    ReportHistoryRow,
    ReportSummaryResponse,
    SignalOutcome,
} from "@/types";

const PAIRS = ["All", "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF"];

// Color tokens for the decision donut and outcome badges. Keeping
// approve = emerald, reject = rose, block = amber, error = slate.
const DECISION_STYLES: Record<string, { badge: string; bar: string; label: string }> = {
    APPROVED: {
        badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
        bar: "bg-emerald-500",
        label: "Approved",
    },
    APPROVED_MODIFIED: {
        badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
        bar: "bg-emerald-400",
        label: "Approved (modified)",
    },
    REJECTED: {
        badge: "bg-rose-500/15 text-rose-400 border-rose-500/30",
        bar: "bg-rose-500",
        label: "Rejected",
    },
    BLOCKED: {
        badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
        bar: "bg-amber-500",
        label: "Blocked",
    },
    ERROR: {
        badge: "bg-slate-500/15 text-slate-400 border-slate-500/30",
        bar: "bg-slate-500",
        label: "Error",
    },
};

function outcomeBadge(outcome: SignalOutcome): string {
    if (outcome === "WIN" || outcome === "APPROVED" || outcome === "APPROVED_MODIFIED") {
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
    }
    if (outcome === "OPEN") {
        return "bg-blue-500/15 text-blue-400 border-blue-500/30";
    }
    if (outcome === "LOSS" || outcome === "REJECTED") {
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
    }
    if (outcome === "BLOCKED") {
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
    }
    return "bg-slate-500/15 text-slate-400 border-slate-500/30";
}

const AGENT_VISUALS: Record<string, { color: string; bg: string; icon: typeof Brain }> = {
    TechnicalV2: { color: "text-emerald-400", bg: "bg-emerald-500/10", icon: TrendingUp },
    MacroV2: { color: "text-blue-400", bg: "bg-blue-500/10", icon: Brain },
    SentimentV2: { color: "text-amber-400", bg: "bg-amber-500/10", icon: Newspaper },
    GeopoliticalV2: { color: "text-violet-400", bg: "bg-violet-500/10", icon: Activity },
};

function agentVisuals(name: string) {
    return AGENT_VISUALS[name] ?? { color: "text-slate-400", bg: "bg-slate-500/10", icon: Users };
}

export default function ReportsPage() {
    const [filter, setFilter] = useState("All");
    const [report, setReport] = useState<ReportSummaryResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const data = await api.reportsSummary(filter, 90);
                setReport(data);
            } catch (err) {
                console.error("Failed to load reports summary", err);
                setReport(null);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [filter]);

    const kpis = report?.kpis;
    const breakdown = report?.decision_breakdown;
    const rejectionReasons = report?.rejection_reasons ?? [];
    const agentStats = report?.agent_stats ?? [];
    const history: ReportHistoryRow[] = report?.history ?? [];
    const curve = report?.curve ?? [];

    const signalsTotal = kpis?.signals_total ?? 0;
    const approvalRate = kpis?.approval_rate ?? 0;
    const agreement = kpis?.agent_agreement ?? 0;
    const realizedPnl = kpis?.realized_pnl ?? 0;
    const unrealizedPnl = kpis?.unrealized_pnl ?? 0;
    const totalPnl = realizedPnl + unrealizedPnl;
    const winRate = kpis?.win_rate ?? 0;
    const settledCount = kpis?.settled_count ?? 0;
    const openCount = kpis?.open_count ?? 0;

    const decisionTotal = breakdown
        ? Object.values(breakdown).reduce((a, b) => a + b, 0)
        : 0;

    return (
        <div className="flex h-full flex-col bg-background text-foreground">
            <RBHeader
                title="Signal History & AI Evaluation"
                subtitle="Real signals, real decisions, real per-agent accuracy — no synthetic data"
                right={
                    <>
                        <Filter className="size-3.5 text-slate-500" />
                        <div className="flex gap-1">
                            {PAIRS.map((p) => (
                                <button
                                    key={p}
                                    onClick={() => setFilter(p)}
                                    data-testid={`reports-filter-${p.replace(/\//g, "").toLowerCase()}`}
                                    className={`px-2 py-1 rounded text-[10px] font-medium transition-all ${
                                        filter === p
                                            ? "bg-brand-blue-600 text-white"
                                            : "text-slate-500 hover:text-white border border-white/5 hover:border-white/10"
                                    }`}
                                >
                                    {p}
                                </button>
                            ))}
                        </div>
                        <a
                            href={api.reportsExportUrl(filter, 90)}
                            data-testid="reports-export-csv"
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/10 text-xs text-slate-300 hover:bg-white/[0.08] transition-all"
                        >
                            <Download className="size-3.5" /> Export CSV
                        </a>
                    </>
                }
            />

            <RBContent className="space-y-6">
                {/* ── KPI tiles ────────────────────────────────────────── */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <KpiTile
                            label="Signals generated"
                            value={signalsTotal}
                            suffix=""
                            decimals={0}
                            color="text-violet-400"
                            icon={Layers}
                            hint={`${openCount} open · ${settledCount} settled`}
                        />
                        <KpiTile
                            label="Approval rate"
                            value={approvalRate}
                            suffix="%"
                            decimals={1}
                            color={approvalRate >= 30 ? "text-emerald-400" : "text-amber-400"}
                            icon={CheckCircle2}
                            hint={signalsTotal === 0 ? "no signals yet" : `${Math.round(approvalRate * signalsTotal / 100)} of ${signalsTotal} approved`}
                        />
                        <KpiTile
                            label="Agent agreement"
                            value={agreement}
                            suffix="%"
                            decimals={1}
                            color={agreement >= 60 ? "text-emerald-400" : "text-amber-400"}
                            icon={Users}
                            hint="signals without inter-agent conflict"
                        />
                        <KpiTile
                            label="Realized P&L"
                            value={Math.abs(realizedPnl)}
                            prefix={realizedPnl >= 0 ? "+$" : "-$"}
                            decimals={2}
                            color={realizedPnl >= 0 ? "text-emerald-400" : "text-rose-400"}
                            icon={realizedPnl >= 0 ? TrendingUp : TrendingDown}
                            hint={`${settledCount === 0 ? "no closed trades" : `${winRate.toFixed(1)}% win rate · ${settledCount} settled`}`}
                        />
                    </div>
                </FadeInUp>

                {/* ── Decision breakdown + open exposure ───────────────── */}
                <FadeInUp delay={0.05}>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2 rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-sm font-bold text-white mb-1">Pipeline decisions</h3>
                            <p className="text-[11px] text-slate-500 mb-4">
                                How the multi-agent pipeline handled the {signalsTotal} signal{signalsTotal === 1 ? "" : "s"} you generated
                            </p>
                            {decisionTotal === 0 ? (
                                <EmptyHint
                                    message="No signals generated in the selected window."
                                    cta="Click Generate Signal on the Agents page to populate this view."
                                />
                            ) : (
                                <div className="space-y-2">
                                    {(["APPROVED", "APPROVED_MODIFIED", "REJECTED", "BLOCKED", "ERROR"] as const).map((key) => {
                                        const count = breakdown?.[key] ?? 0;
                                        const pct = decisionTotal === 0 ? 0 : (count / decisionTotal) * 100;
                                        const style = DECISION_STYLES[key];
                                        return (
                                            <div key={key} className="flex items-center gap-3">
                                                <div className="w-32 text-xs text-slate-400">{style.label}</div>
                                                <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                                                    <div
                                                        className={`h-full ${style.bar} transition-all`}
                                                        style={{ width: `${pct}%` }}
                                                    />
                                                </div>
                                                <div className="w-20 text-right text-xs text-slate-300 font-mono">
                                                    {count} <span className="text-slate-600">· {pct.toFixed(0)}%</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-sm font-bold text-white mb-1">Open exposure</h3>
                            <p className="text-[11px] text-slate-500 mb-4">Unrealized P&L of paper positions still open</p>
                            <div className="space-y-3 text-xs">
                                <div className="flex justify-between items-baseline">
                                    <span className="text-slate-500">Open positions</span>
                                    <span className="text-white font-semibold">{openCount}</span>
                                </div>
                                <div className="flex justify-between items-baseline">
                                    <span className="text-slate-500">Unrealized P&L</span>
                                    <span className={`font-mono font-bold ${unrealizedPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                        {unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)}
                                    </span>
                                </div>
                                <div className="border-t border-white/5 pt-3 flex justify-between items-baseline">
                                    <span className="text-slate-500">Total P&L</span>
                                    <span className={`font-mono font-bold ${totalPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                        {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </FadeInUp>

                {/* ── Top rejection reasons ────────────────────────────── */}
                <FadeInUp delay={0.1}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <div className="flex items-center gap-2 mb-1">
                            <ShieldX className="size-4 text-rose-400" />
                            <h3 className="text-sm font-bold text-white">Top rejection reasons</h3>
                        </div>
                        <p className="text-[11px] text-slate-500 mb-4">
                            What stopped the pipeline from approving signals — useful for learning the gates
                        </p>
                        {rejectionReasons.length === 0 ? (
                            <EmptyHint message="No rejected or blocked signals yet." />
                        ) : (
                            <div className="space-y-2">
                                {rejectionReasons.map((r, i) => (
                                    <div
                                        key={`${r.reason}-${i}`}
                                        className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/5"
                                    >
                                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold border bg-rose-500/15 text-rose-300 border-rose-500/30 flex-shrink-0">
                                            × {r.count}
                                        </span>
                                        <p className="text-[12px] text-slate-300 leading-relaxed">{r.reason}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </FadeInUp>

                {/* ── Per-agent stats ──────────────────────────────────── */}
                <FadeInUp delay={0.15}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <div className="flex items-center gap-2 mb-1">
                            <Users className="size-4 text-blue-400" />
                            <h3 className="text-sm font-bold text-white">Per-agent activity & accuracy</h3>
                        </div>
                        <p className="text-[11px] text-slate-500 mb-4">
                            Accuracy is real only when paper trades have closed — otherwise you see activity-level evidence (how often each agent contributed and its average confidence).
                        </p>
                        {agentStats.length === 0 ? (
                            <EmptyHint message="No agent activity in the selected window." />
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {agentStats.map((agent) => (
                                    <AgentStatCard key={agent.agent} stat={agent} />
                                ))}
                            </div>
                        )}
                    </div>
                </FadeInUp>

                {/* ── Realized P&L curve — only when there's something real ── */}
                {curve.length > 0 && (
                    <FloatingCard delay={0.2}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <div className="flex items-center gap-2 mb-1">
                                <LineChartIcon className="size-4 text-violet-400" />
                                <h3 className="text-sm font-bold text-white">Realized P&L curve</h3>
                            </div>
                            <p className="text-[11px] text-slate-500 mb-4">
                                Cumulative paper-trade P&L from closed positions
                            </p>
                            <ResponsiveContainer width="100%" height={200}>
                                <AreaChart data={curve}>
                                    <defs>
                                        <linearGradient id="pnl" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#475569" }} axisLine={false} tickLine={false} interval={4} />
                                    <YAxis tick={{ fontSize: 10, fill: "#475569" }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
                                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: 11 }} />
                                    <Area
                                        type="monotone"
                                        dataKey="cumulative_pnl"
                                        stroke="#6366f1"
                                        strokeWidth={2}
                                        fill="url(#pnl)"
                                        name="Cumulative P&L ($)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </FloatingCard>
                )}

                {/* ── Signal history table ─────────────────────────────── */}
                <FloatingCard delay={0.25}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <h3 className="text-sm font-bold text-white mb-1">Signal timeline</h3>
                        <p className="text-[11px] text-slate-500 mb-4">
                            Every Generate Signal call with the pipeline's decision and reason
                        </p>
                        {history.length === 0 && !loading ? (
                            <EmptyHint
                                message="No signals in this window."
                                cta="Open /agents and click Generate Signal to populate this list."
                            />
                        ) : (
                            <div className="space-y-3">
                                <StaggerContainer>
                                    {history.map((s) => (
                                        <StaggerItem key={s.id}>
                                            <HistoryRow row={s} />
                                        </StaggerItem>
                                    ))}
                                </StaggerContainer>
                            </div>
                        )}
                    </div>
                </FloatingCard>
            </RBContent>
        </div>
    );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

interface KpiTileProps {
    label: string;
    value: number;
    suffix?: string;
    prefix?: string;
    decimals: number;
    color: string;
    icon: typeof Brain;
    hint: string;
}

function KpiTile({ label, value, suffix = "", prefix = "", decimals, color, icon: Icon, hint }: KpiTileProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="p-4 rounded-xl border border-white/5 bg-white/[0.03]"
        >
            <div className="flex items-center justify-between mb-2">
                <Icon className={`size-4 ${color}`} />
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
            </div>
            <div className={`text-2xl font-bold ${color}`}>
                {prefix}
                <AnimatedCounter to={value} decimals={decimals} />
                {suffix}
            </div>
            <div className="text-[10px] text-slate-600 mt-1">{hint}</div>
        </motion.div>
    );
}

function AgentStatCard({ stat }: { stat: ReportAgentStat }) {
    const visuals = agentVisuals(stat.agent);
    const Icon = visuals.icon;
    const directionTotal = stat.directions.BUY + stat.directions.SELL + stat.directions.NEUTRAL;
    return (
        <div className={`p-4 rounded-xl border border-white/5 ${visuals.bg}`}>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Icon className={`size-4 ${visuals.color}`} />
                    <span className="text-sm font-semibold text-white">{stat.agent}</span>
                </div>
                {stat.accuracy !== null ? (
                    <span className={`text-xs font-bold ${stat.accuracy >= 50 ? "text-emerald-400" : "text-rose-400"}`}>
                        {stat.accuracy.toFixed(1)}%
                        <span className="text-[10px] text-slate-500 font-normal ml-1">accuracy</span>
                    </span>
                ) : (
                    <span className="text-[10px] text-slate-500 italic">accuracy pending</span>
                )}
            </div>
            <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Appearances</span>
                    <span className="text-slate-300 font-mono">{stat.appearances}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Avg confidence</span>
                    <span className={`font-mono ${visuals.color}`}>{stat.avg_confidence.toFixed(1)}%</span>
                </div>
                {stat.accuracy !== null && (
                    <div className="flex items-center justify-between text-[11px]">
                        <span className="text-slate-500">Settled outcomes</span>
                        <span className="text-slate-300 font-mono">{stat.correct}/{stat.settled} correct</span>
                    </div>
                )}
                {directionTotal > 0 && (
                    <div className="pt-2">
                        <div className="text-[10px] text-slate-500 mb-1">Direction mix</div>
                        <div className="flex gap-1 h-1.5 rounded-full overflow-hidden bg-slate-800">
                            <div className="bg-emerald-500" style={{ width: `${(stat.directions.BUY / directionTotal) * 100}%` }} title={`BUY ${stat.directions.BUY}`} />
                            <div className="bg-rose-500" style={{ width: `${(stat.directions.SELL / directionTotal) * 100}%` }} title={`SELL ${stat.directions.SELL}`} />
                            <div className="bg-slate-500" style={{ width: `${(stat.directions.NEUTRAL / directionTotal) * 100}%` }} title={`NEUTRAL ${stat.directions.NEUTRAL}`} />
                        </div>
                        <div className="flex gap-3 text-[9px] text-slate-600 mt-1">
                            <span className="text-emerald-500">● BUY {stat.directions.BUY}</span>
                            <span className="text-rose-500">● SELL {stat.directions.SELL}</span>
                            <span className="text-slate-400">● NEUTRAL {stat.directions.NEUTRAL}</span>
                        </div>
                    </div>
                )}
            </div>
            {stat.accuracy === null && stat.appearances > 0 && (
                <AnimatedProgressBar value={stat.avg_confidence} color="blue" height={2} className="mt-3" />
            )}
        </div>
    );
}

function HistoryRow({ row }: { row: ReportHistoryRow }) {
    const isApproved = row.outcome === "APPROVED" || row.outcome === "APPROVED_MODIFIED" || row.outcome === "OPEN" || row.outcome === "WIN";
    return (
        <div className="p-4 rounded-xl bg-white/[0.04] border border-white/5 hover:border-white/10 transition-colors">
            <div className="flex items-start gap-4">
                <div className="shrink-0">
                    <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                            row.direction === "BUY"
                                ? "bg-emerald-500/15 border border-emerald-500/30"
                                : row.direction === "SELL"
                                    ? "bg-rose-500/15 border border-rose-500/30"
                                    : "bg-slate-500/15 border border-slate-500/30"
                        }`}
                    >
                        {row.direction === "BUY" ? (
                            <TrendingUp className="size-5 text-emerald-400" />
                        ) : row.direction === "SELL" ? (
                            <TrendingDown className="size-5 text-rose-400" />
                        ) : (
                            <Activity className="size-5 text-slate-400" />
                        )}
                    </div>
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono text-slate-500">SIG-{row.id}</span>
                        <span className="font-bold text-white">{row.pair}</span>
                        <span
                            className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${
                                row.direction === "BUY"
                                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                    : row.direction === "SELL"
                                        ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                                        : "bg-slate-500/15 text-slate-400 border-slate-500/30"
                            }`}
                        >
                            {row.direction}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${outcomeBadge(row.outcome)}`}>
                            {row.outcome}
                        </span>
                        {row.market_regime && (
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-medium border border-slate-700 bg-slate-800 text-slate-400">
                                {row.market_regime}
                            </span>
                        )}
                        <span className="text-[10px] text-slate-500 ml-auto">
                            {new Date(row.time).toLocaleString()}
                        </span>
                    </div>
                    {row.rejection_reason && !isApproved && (
                        <div className="flex items-start gap-1.5 mt-2 text-[11px] text-rose-300/80">
                            <XCircle className="size-3 mt-0.5 flex-shrink-0" />
                            <span className="leading-relaxed">{row.rejection_reason}</span>
                        </div>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-[10px]">
                        <span className="text-slate-500">
                            Confidence: <span className="text-blue-400 font-bold">{row.confidence.toFixed(1)}%</span>
                        </span>
                        {row.paper_position_id && (
                            <span className="text-slate-500">
                                Paper position: <span className="text-blue-400 font-mono">#{row.paper_position_id}</span>
                            </span>
                        )}
                    </div>
                    <AnimatedProgressBar value={row.confidence} color="blue" height={2} className="mt-2" />
                </div>
            </div>
        </div>
    );
}

function EmptyHint({ message, cta }: { message: string; cta?: string }) {
    return (
        <div className="rounded-lg border border-dashed border-white/10 bg-white/[0.02] p-6 text-center">
            <AlertTriangle className="size-5 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400">{message}</p>
            {cta && <p className="text-[10px] text-slate-600 mt-1">{cta}</p>}
        </div>
    );
}
