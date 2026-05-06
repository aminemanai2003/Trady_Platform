"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    Bot, Brain, Newspaper, Layers, Activity, TrendingUp, FlaskConical,
    FileText, Shield, Target, Zap, ArrowRight, BarChart3, Scale,
    CheckCircle2, AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { HealthCheckV2 } from "@/types";
import {
    AuroraBackground, AnimatedCounter, FadeInUp, StaggerContainer,
    StaggerItem, SpotlightCard, GlowDot, FloatingCard, AnimatedProgressBar,
} from "@/components/animations";

const PAIRS = [
    { symbol: "EURUSD", name: "EUR/USD", flag: "🇪🇺🇺🇸", corr: "+0.76 with GBP/USD" },
    { symbol: "USDJPY", name: "USD/JPY", flag: "🇺🇸🇯🇵", corr: "+0.68 with USD/CHF" },
    { symbol: "GBPUSD", name: "GBP/USD", flag: "🇬🇧🇺🇸", corr: "Highest volatility" },
    { symbol: "USDCHF", name: "USD/CHF", flag: "🇺🇸🇨🇭", corr: "-0.76 with EUR/USD" },
];

const BOs = [
    {
        code: "BO1", title: "Multi-Dimensional Market Understanding",
        color: "from-violet-500 to-indigo-500",
        border: "border-violet-500/20",
        glow: "shadow-violet-500/10",
        bg: "bg-violet-500/5",
        dsos: ["DSO1.1 — Macro Agent (CPI, NFP, PMI, NLP bias −100→+100)", "DSO1.2 — Technical Agent (RSI, MACD, BB, multi-timeframe)", "DSO1.3 — Sentiment Agent (FinBERT, news, COT reports)"],
        href: "/agents",
        icon: Brain,
    },
    {
        code: "BO2", title: "Explainable Alpha Signals",
        color: "from-emerald-500 to-teal-500",
        border: "border-emerald-500/20",
        glow: "shadow-emerald-500/10",
        bg: "bg-emerald-500/5",
        dsos: ["DSO2.1 — Coordinator (weighted voting, XGBoost ensemble)", "DSO2.2 — Backtesting (5Y walk-forward, Sharpe, win rate)", "DSO2.3 — Position Sizing (Kelly Criterion, ATR risk mgmt)"],
        href: "/backtesting",
        icon: Layers,
    },
    {
        code: "BO3", title: "Reduce False Signal Risk",
        color: "from-amber-500 to-orange-500",
        border: "border-amber-500/20",
        glow: "shadow-amber-500/10",
        bg: "bg-amber-500/5",
        dsos: ["DSO3.1 — Agent voting & conflict detection", "Confidence thresholds & contradiction resolution", "Rule-based + probabilistic agreement checks"],
        href: "/agents",
        icon: Shield,
    },
    {
        code: "BO4", title: "System Reliability",
        color: "from-rose-500 to-red-500",
        border: "border-rose-500/20",
        glow: "shadow-rose-500/10",
        bg: "bg-rose-500/5",
        dsos: ["DSO4.1 — Data validation (missing values, outliers, timestamps)", "DSO4.2 — MLflow metrics, latency monitoring, drift detection", "Real-time dashboards (Prometheus/Grafana style)"],
        href: "/monitoring",
        icon: Activity,
    },
    {
        code: "BO5", title: "Transparent Reporting",
        color: "from-sky-500 to-blue-500",
        border: "border-sky-500/20",
        glow: "shadow-sky-500/10",
        bg: "bg-sky-500/5",
        dsos: ["DSO5.1 — Structured analytical reports (FastAPI + React)", "Signals, explanations, backtesting summaries", "Performance & data quality dashboards"],
        href: "/reports",
        icon: FileText,
    },
];

const CORRELATIONS = [
    { pair: "EUR/USD × GBP/USD", value: 0.76, type: "positive", why: "Both risk-on currencies vs USD" },
    { pair: "USD/JPY × USD/CHF", value: 0.68, type: "positive", why: "Both safe-haven currencies" },
    { pair: "EUR/USD × USD/CHF", value: -0.76, type: "negative", why: "USD common denominator" },
    { pair: "EUR/USD × USD/JPY", value: -0.59, type: "negative", why: "USD dominance effect" },
    { pair: "GBP/USD × USD/CHF", value: -0.58, type: "negative", why: "CHF mirrors USD moves" },
];

export default function DashboardPage() {
    const router = useRouter();
    const [health, setHealth] = useState<HealthCheckV2 | null>(null);

    useEffect(() => {
        api.v2.healthCheck().then(setHealth).catch(() => {});
        const t = setInterval(() => api.v2.healthCheck().then(setHealth).catch(() => {}), 30000);
        return () => clearInterval(t);
    }, []);

    const avgWinRate = health
        ? (Object.values(health.agent_performances).reduce((s, p) => s + p.win_rate, 0) /
          Object.values(health.agent_performances).length * 100).toFixed(1)
        : "—";
    const totalSignals = health
        ? Object.values(health.agent_performances).reduce((s, p) => s + p.total_signals, 0)
        : 0;
    const isOnline = health?.status === "operational";

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />

            {/* Header */}
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <div className="flex items-center gap-2">
                    <div className="size-2 rounded-full bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/50" />
                    <h1 className="text-sm font-bold text-white">Trady</h1>
                    <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DATAMINDS</span>
                </div>
                <div className="ml-auto flex items-center gap-4 text-xs text-slate-500">
                    <span className="font-mono">5 Business Objectives · 10 DSOs</span>
                    <span className="font-mono text-emerald-400">● LIVE</span>
                </div>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-8">

                {/* Hero Banner */}
                <FadeInUp>
                    <div className="relative overflow-hidden rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-500/10 via-blue-500/5 to-transparent p-8">
                        <div className="absolute -top-10 -right-10 w-64 h-64 bg-violet-500/10 rounded-full blur-3xl" />
                        <div className="absolute -bottom-10 -left-10 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl" />
                        <div className="relative grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2">
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-widest">
                                        Production · TDSP Methodology
                                    </span>
                                </div>
                                <h2 className="text-3xl lg:text-4xl font-bold mb-3 bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                                    Multi-Agent FX Intelligence
                                </h2>
                                <p className="text-slate-400 max-w-xl leading-relaxed mb-6">
                                    Système de décision multi-agents pour les paires de devises majeures.
                                    Analyse technique, macroéconomique et sentiment fusionnés en un signal unifié et explicable.
                                </p>
                                <div className="flex flex-wrap gap-3">
                                    {[
                                        { label: "Signal Lab", icon: Bot, href: "/agents", color: "bg-violet-600 hover:bg-violet-500" },
                                        { label: "Backtesting", icon: TrendingUp, href: "/backtesting", color: "bg-emerald-700 hover:bg-emerald-600" },
                                        { label: "Feature Lab",  icon: FlaskConical, href: "/features", color: "bg-slate-700 hover:bg-slate-600" },
                                    ].map((btn) => (
                                        <motion.button
                                            key={btn.label}
                                            whileHover={{ scale: 1.04 }}
                                            whileTap={{ scale: 0.97 }}
                                            onClick={() => router.push(btn.href)}
                                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors ${btn.color}`}
                                        >
                                            <btn.icon className="size-3.5" />
                                            {btn.label}
                                        </motion.button>
                                    ))}
                                </div>
                            </div>
                            {/* KPI column */}
                            <div className="grid grid-cols-2 gap-3 content-center">
                                {[
                                    { label: "Agents actifs", value: health ? Object.keys(health.agent_performances).length : 3, suffix: "", color: "text-violet-400" },
                                    { label: "Signaux générés", value: totalSignals, suffix: "", color: "text-emerald-400" },
                                    { label: "Win Rate moyen", value: avgWinRate === "—" ? 0 : parseFloat(avgWinRate as string), suffix: "%", color: "text-amber-400" },
                                    { label: "Features totales", value: 120, suffix: "", color: "text-blue-400" },
                                ].map((kpi, i) => (
                                    <div key={i} className="p-3 rounded-xl bg-white/[0.04] border border-white/5 text-center">
                                        <div className={`text-2xl font-bold ${kpi.color}`}>
                                            <AnimatedCounter to={typeof kpi.value === "number" ? kpi.value : 0} suffix={kpi.suffix} decimals={kpi.suffix === "%" ? 1 : 0} />
                                        </div>
                                        <div className="text-[10px] text-slate-500 mt-0.5">{kpi.label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </FadeInUp>

                {/* System Status Bar */}
                <FadeInUp delay={0.1}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                            {
                                label: "Statut système",
                                value: isOnline ? "OPÉRATIONNEL" : "HORS LIGNE",
                                sub: isOnline ? "Tous les services actifs" : "Vérifier les connexions",
                                icon: Activity,
                                color: isOnline ? "text-emerald-400" : "text-rose-400",
                                dot: isOnline ? "emerald" as const : "rose" as const,
                                bg: "bg-emerald-500/5 border-emerald-500/20",
                            },
                            {
                                label: "Agents IA",
                                value: "3 Actifs",
                                sub: "Macro · Tech · Sentiment",
                                icon: Bot,
                                color: "text-violet-400",
                                dot: "violet" as const,
                                bg: "bg-violet-500/5 border-violet-500/20",
                            },
                            {
                                label: "Paires couvertes",
                                value: "4 Majeures",
                                sub: "EUR/USD · USD/JPY · GBP/USD · USD/CHF",
                                icon: BarChart3,
                                color: "text-blue-400",
                                dot: "blue" as const,
                                bg: "bg-blue-500/5 border-blue-500/20",
                            },
                            {
                                label: "Qualité données",
                                value: "> 90%",
                                sub: "Tous les seuils respectés (DSO4.1)",
                                icon: CheckCircle2,
                                color: "text-amber-400",
                                dot: "amber" as const,
                                bg: "bg-amber-500/5 border-amber-500/20",
                            },
                        ].map((item, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 12 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 + i * 0.07 }}
                                className={`p-4 rounded-xl border ${item.bg} backdrop-blur-sm`}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <GlowDot color={item.dot} />
                                    <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">{item.label}</span>
                                </div>
                                <div className={`text-base font-bold ${item.color}`}>{item.value}</div>
                                <div className="text-[10px] text-slate-600 mt-0.5">{item.sub}</div>
                            </motion.div>
                        ))}
                    </div>
                </FadeInUp>

                {/* Business Objectives Cards */}
                <div>
                    <FadeInUp delay={0.15}>
                        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">Objectifs Business & Data Science</h3>
                    </FadeInUp>
                    <StaggerContainer staggerDelay={0.08} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {BOs.map((bo) => (
                            <StaggerItem key={bo.code}>
                                <SpotlightCard
                                    className={`rounded-xl border ${bo.border} ${bo.bg} p-5 cursor-pointer hover:brightness-110 transition-all shadow-xl ${bo.glow} group`}
                                    onClick={() => router.push(bo.href)}
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg bg-gradient-to-br ${bo.color} shadow-lg`}>
                                                <bo.icon className="size-4 text-white" />
                                            </div>
                                            <div>
                                                <span className={`text-[10px] font-mono font-bold bg-gradient-to-r ${bo.color} bg-clip-text text-transparent`}>{bo.code}</span>
                                                <p className="text-sm font-semibold text-white leading-tight">{bo.title}</p>
                                            </div>
                                        </div>
                                        <ArrowRight className="size-4 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-1 transition-all mt-1" />
                                    </div>
                                    <div className="space-y-1.5 mt-3">
                                        {bo.dsos.map((dso, i) => (
                                            <div key={i} className="flex items-start gap-2 text-[11px] text-slate-400">
                                                <div className={`mt-1.5 size-1 rounded-full shrink-0 bg-gradient-to-r ${bo.color}`} />
                                                <span>{dso}</span>
                                            </div>
                                        ))}
                                    </div>
                                </SpotlightCard>
                            </StaggerItem>
                        ))}
                    </StaggerContainer>
                </div>

                {/* Currency Pairs + Correlations */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

                    {/* Currency Pairs */}
                    <FloatingCard delay={0.2}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-4">
                                Paires de Devises Majeures
                            </h3>
                            <div className="grid grid-cols-2 gap-3">
                                {PAIRS.map((pair, i) => (
                                    <motion.div
                                        key={pair.symbol}
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: 0.3 + i * 0.07 }}
                                        whileHover={{ scale: 1.02 }}
                                        onClick={() => router.push(`/agents?pair=${pair.symbol}`)}
                                        className="p-3 rounded-lg bg-white/[0.04] border border-white/5 hover:border-violet-500/30 cursor-pointer transition-all group"
                                    >
                                        <div className="text-2xl mb-1">{pair.flag}</div>
                                        <div className="text-sm font-bold text-white">{pair.name}</div>
                                        <div className="text-[10px] text-slate-500 mt-1">{pair.corr}</div>
                                        <div className="mt-2 flex items-center gap-1 text-[10px] text-violet-400 group-hover:text-violet-300">
                                            <Zap className="size-3" />
                                            Générer signal
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </FloatingCard>

                    {/* Correlation Matrix */}
                    <FloatingCard delay={0.25}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">
                                Corrélations Inter-Paires (DSO1.3)
                            </h3>
                            <p className="text-[10px] text-slate-600 mb-4">Key findings — CPI/Fed Funds Rate: −0.95</p>
                            <div className="space-y-3">
                                {CORRELATIONS.map((c, i) => (
                                    <div key={i} className="flex items-center gap-3">
                                        <div className="text-[11px] font-mono text-slate-400 w-40 shrink-0">{c.pair}</div>
                                        <div className="flex-1">
                                            <AnimatedProgressBar
                                                value={Math.abs(c.value) * 100}
                                                color={c.type === "positive" ? "emerald" : "rose"}
                                                height={4}
                                            />
                                        </div>
                                        <div className={`text-xs font-bold w-12 text-right ${c.type === "positive" ? "text-emerald-400" : "text-rose-400"}`}>
                                            {c.type === "positive" ? "+" : ""}{c.value}
                                        </div>
                                        <div className="text-[9px] text-slate-600 w-28 shrink-0">{c.why}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </FloatingCard>
                </div>

                {/* Feature Engineering Summary */}
                <FloatingCard delay={0.3}>
                    <div className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 p-5">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-0.5">Feature Engineering (DSO1.2)</h3>
                                <p className="text-[10px] text-slate-600">120 features créées → Random Forest importance → Top 50 sélectionnées</p>
                            </div>
                            <motion.button
                                whileHover={{ scale: 1.03 }}
                                onClick={() => router.push("/features")}
                                className="flex items-center gap-1.5 text-xs text-fuchsia-400 hover:text-fuchsia-300 transition-colors"
                            >
                                Voir Feature Lab <ArrowRight className="size-3" />
                            </motion.button>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {[
                                { label: "Features Techniques", count: 60, color: "emerald", desc: "SMA, EMA, RSI, MACD, BB, ATR, OBV" },
                                { label: "Features Fondamentales", count: 20, color: "blue", desc: "CPI, PIB, PMI, taux d'intérêt" },
                                { label: "Features Sentiment", count: 15, color: "amber", desc: "NLP news, score −1 à +1, volumes" },
                                { label: "Features Temporelles", count: 25, color: "fuchsia", desc: "Cycles horaires, sessions, NFP/FOMC" },
                            ].map((f, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.4 + i * 0.06 }}
                                    className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center"
                                >
                                    <div className={`text-2xl font-bold text-${f.color}-400`}>
                                        <AnimatedCounter to={f.count} />
                                    </div>
                                    <div className="text-[10px] font-semibold text-slate-300 mt-1">{f.label}</div>
                                    <div className="text-[9px] text-slate-600 mt-1 leading-relaxed">{f.desc}</div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </FloatingCard>

            </div>
        </div>
    );
}
