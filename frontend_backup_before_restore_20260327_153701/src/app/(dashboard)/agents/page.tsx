"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Progress } from "@/components/ui/progress";
import {
    Bot, Brain, TrendingUp, Newspaper, Layers, Zap, Activity,
    RefreshCw, AlertCircle, CheckCircle2, ChevronRight, Scale, Shield,
} from "lucide-react";
import { api } from "@/lib/api";
import type { SignalResponseV2, HealthCheckV2, DriftDetectionV2 } from "@/types";
import {
    AuroraBackground, FadeInUp, StaggerContainer, StaggerItem,
    SpotlightCard, GlowDot, AnimatedProgressBar, FloatingCard,
} from "@/components/animations";

// ─── Agent configs (DSO1.1 / DSO1.2 / DSO1.3) ───────────────────────────────
const AGENTS = {
    technical: {
        icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10",
        border: "border-emerald-500/20", gradient: "from-emerald-500 to-teal-500",
        name: "Technical Agent", dso: "DSO1.2",
        description: "RSI · MACD · Bollinger Bands · SMA/EMA · ATR · multi-timeframe",
        weight: 40,
        bio: "Traite les données OHLC MT5 sur 3 horizons (1H-4H intraday, D1 swing, W1-M1 position) avec 60 features techniques dont indicateurs de tendance, momentum, volatilité et volume.",
    },
    macro: {
        icon: Brain, color: "text-blue-400", bg: "bg-blue-500/10",
        border: "border-blue-500/20", gradient: "from-blue-500 to-indigo-500",
        name: "Macro Agent", dso: "DSO1.1",
        description: "FRED API · CPI · NFP · PMI · Central bank rates · NLP/LLM",
        weight: 35,
        bio: "Ingère les indicateurs FRED (CPI, NFP, PMI) et analyse les communications FOMC/ECB/BoE via NLP/LLM pour générer un biais directionnel fondamental de -100 à +100.",
    },
    sentiment: {
        icon: Newspaper, color: "text-amber-400", bg: "bg-amber-500/10",
        border: "border-amber-500/20", gradient: "from-amber-500 to-orange-500",
        name: "Sentiment Agent", dso: "DSO1.3",
        description: "FinBERT · Reuters News · COT Reports · Social sentiment",
        weight: 25,
        bio: "Analyse les news financières, réseaux sociaux et rapports COT avec FinBERT pour quantifier le positionnement du marché et détecter les extrêmes de sentiment pour signaux contrarians.",
    },
};

const PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF"];

function SignalLabContent() {
    const searchParams = useSearchParams();
    const [signal, setSignal] = useState<SignalResponseV2 | null>(null);
    const [health, setHealth] = useState<HealthCheckV2 | null>(null);
    const [drift, setDrift]   = useState<DriftDetectionV2 | null>(null);
    const [loading, setLoading] = useState(false);
    const [pair, setPair] = useState(searchParams.get("pair") || "EURUSD");

    const loadData = async () => {
        try {
            const [h, d] = await Promise.all([api.v2.healthCheck(), api.v2.driftDetection()]);
            setHealth(h); setDrift(d);
        } catch {}
    };

    const generateSignal = async () => {
        setLoading(true);
        try {
            const s = await api.v2.generateSignal(pair);
            setSignal(s);
            await loadData();
        } catch {}
        setLoading(false);
    };

    useEffect(() => { loadData(); const t = setInterval(loadData, 30000); return () => clearInterval(t); }, []);

    const dirColor = (d: string) =>
        d === "BUY" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
        : d === "SELL" ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
        : "bg-slate-500/15 text-slate-400 border-slate-500/30";

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />

            {/* Header */}
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 shadow-lg shadow-emerald-500/30">
                        <Layers className="size-3.5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-sm font-bold text-white">Signal Lab</h1>
                        <p className="text-[10px] text-slate-500">DSO1.1 · DSO1.2 · DSO1.3 · DSO2.1 · DSO3.1</p>
                    </div>
                </div>
                <div className="ml-auto flex items-center gap-2">
                    <div className="flex gap-1">
                        {PAIRS.map((p) => (
                            <button
                                key={p}
                                onClick={() => setPair(p)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                                    pair === p
                                        ? "bg-violet-600 text-white shadow-lg shadow-violet-500/30"
                                        : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                                }`}
                            >
                                {p.slice(0,3)}/{p.slice(3)}
                            </button>
                        ))}
                    </div>
                    <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={generateSignal}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-sm font-semibold shadow-lg shadow-violet-500/30 hover:shadow-violet-500/50 transition-all disabled:opacity-60"
                    >
                        {loading
                            ? <><RefreshCw className="size-4 animate-spin" /> Analyse en cours...</>
                            : <><Zap className="size-4" /> Générer Signal</>
                        }
                    </motion.button>
                </div>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">

                {/* System Status (DSO3.1) */}
                {health && (
                    <FadeInUp>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {[
                                { label: "Statut", value: health.status.toUpperCase(), dot: "emerald" as const, sub: "Système opérationnel" },
                                { label: "Uptime", value: `${Math.round(health.system.uptime_seconds/60)}m`, dot: "blue" as const, sub: "Depuis dernier démarrage" },
                                { label: "Agents actifs", value: `${Object.keys(health.agent_performances).length}/3`, dot: "violet" as const, sub: "Macro · Tech · Sentiment" },
                                { label: "Drift détecté", value: (drift?.sentiment_drift?.detected || (drift as any)?.sentiment?.drift_detected) ? "OUI" : "NON", dot: drift?.sentiment_drift?.detected ? "amber" as const : "emerald" as const, sub: "Détection distribution" },
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
                            Architecture Multi-Agents — Pondération DSO2.1
                        </h3>
                    </FadeInUp>
                    <StaggerContainer staggerDelay={0.1} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {Object.entries(AGENTS).map(([key, agent]) => {
                            const perf = health?.agent_performances?.[key] || health?.agent_performances?.[key.toLowerCase()];
                            const vote = signal?.signal?.agent_votes?.[key];
                            return (
                                <StaggerItem key={key}>
                                    <SpotlightCard
                                        className={`rounded-xl border ${agent.border} bg-white/[0.03] p-5 h-full`}
                                        spotlightColor={`rgba(${key === "technical" ? "16,185,129" : key === "macro" ? "59,130,246" : "245,158,11"},0.1)`}
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
                                            <div className={`text-xs font-bold ${agent.color}`}>{agent.weight}%</div>
                                        </div>

                                        <p className="text-[11px] text-slate-500 leading-relaxed mb-3">{agent.bio}</p>

                                        <div className="mb-3">
                                            <div className="flex items-center justify-between text-[10px] text-slate-600 mb-1">
                                                <span>Poids dans le vote</span>
                                                <span className={agent.color}>{agent.weight}%</span>
                                            </div>
                                            <AnimatedProgressBar value={agent.weight} color={key === "technical" ? "emerald" : key === "macro" ? "blue" : "amber"} height={3} />
                                        </div>

                                        <div className="text-[10px] text-slate-600 font-mono">{agent.description}</div>

                                        {/* Vote result */}
                                        {vote && (
                                            <div className="mt-3 pt-3 border-t border-white/5">
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${vote.signal === "BUY" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : vote.signal === "SELL" ? "bg-rose-500/15 text-rose-400 border-rose-500/30" : "bg-slate-500/15 text-slate-400 border-slate-500/30"}`}>
                                                        {vote.signal}
                                                    </span>
                                                    <span className="text-xs font-bold text-white">{(vote.confidence * 100).toFixed(0)}%</span>
                                                </div>
                                                <AnimatedProgressBar value={vote.confidence * 100} color={key === "technical" ? "emerald" : key === "macro" ? "blue" : "amber"} height={3} />
                                                <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{vote.reasoning}</p>
                                            </div>
                                        )}

                                        {/* Performance */}
                                        {perf && (
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
                                        )}
                                    </SpotlightCard>
                                </StaggerItem>
                            );
                        })}
                    </StaggerContainer>
                </div>

                {/* Final Signal (DSO2.1 + DSO3.1) */}
                <AnimatePresence>
                    {signal?.success && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                        >
                            <div className={`rounded-xl border p-6 ${
                                signal.signal.direction === "BUY"
                                    ? "border-emerald-500/30 bg-emerald-500/5"
                                    : signal.signal.direction === "SELL"
                                    ? "border-rose-500/30 bg-rose-500/5"
                                    : "border-slate-500/30 bg-white/[0.03]"
                            }`}>
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <Layers className="size-4 text-violet-400" />
                                            <h3 className="text-sm font-bold text-white">Signal Final — {pair}</h3>
                                            <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5">DSO2.1 + DSO3.1</span>
                                        </div>
                                        <p className="text-[11px] text-slate-500">Aggrégation par vote pondéré · Seuils de confiance · Détection conflits</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className={`px-4 py-2 rounded-xl text-lg font-bold border ${dirColor(signal.signal.direction)}`}>
                                            {signal.signal.direction}
                                        </span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-4 mb-4">
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Confiance</div>
                                        <div className="text-xl font-bold text-white">{(signal.signal.confidence * 100).toFixed(0)}%</div>
                                        <AnimatedProgressBar value={signal.signal.confidence * 100} color="violet" height={3} className="mt-2" />
                                    </div>
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Score pondéré</div>
                                        <div className="text-xl font-bold text-white">{signal.signal.weighted_score.toFixed(3)}</div>
                                        <div className="text-[10px] text-slate-600 mt-1">Score composite</div>
                                    </div>
                                    <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 text-center">
                                        <div className="text-[10px] text-slate-500 mb-1">Régime marché</div>
                                        <div className="text-base font-bold text-white capitalize">{signal.signal.market_regime}</div>
                                        <div className="text-[10px] text-slate-600 mt-1">Contexte actuel</div>
                                    </div>
                                </div>

                                <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 mb-3">
                                    <div className="text-[10px] text-slate-500 mb-1.5">Raisonnement (LLM Explicabilité)</div>
                                    <p className="text-sm text-slate-300 leading-relaxed">{signal.signal.reasoning}</p>
                                </div>

                                {signal.signal.conflicts.length > 0 && (
                                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                        <div className="flex items-center gap-2 mb-2">
                                            <AlertCircle className="size-4 text-amber-400" />
                                            <span className="text-[11px] font-bold text-amber-400">Conflits détectés (DSO3.1)</span>
                                        </div>
                                        <ul className="space-y-0.5">
                                            {signal.signal.conflicts.map((c, i) => (
                                                <li key={i} className="text-[11px] text-amber-300/80">• {c}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
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
                            <h3 className="text-lg font-bold text-white mb-2">Signal Lab Prêt</h3>
                            <p className="text-sm text-slate-500 mb-6 max-w-md mx-auto">
                                Sélectionnez une paire de devises et cliquez sur <strong className="text-violet-400">Générer Signal</strong> pour activer le système multi-agents.
                            </p>
                            <div className="flex flex-wrap gap-2 justify-center text-[11px] text-slate-600">
                                <span className="px-2 py-1 rounded border border-violet-500/20 bg-violet-500/5">DSO1.1 Biais Macro</span>
                                <span className="px-2 py-1 rounded border border-emerald-500/20 bg-emerald-500/5">DSO1.2 Signaux Techniques</span>
                                <span className="px-2 py-1 rounded border border-amber-500/20 bg-amber-500/5">DSO1.3 Score Sentiment</span>
                                <span className="px-2 py-1 rounded border border-blue-500/20 bg-blue-500/5">DSO2.1 Vote Pondéré</span>
                                <span className="px-2 py-1 rounded border border-rose-500/20 bg-rose-500/5">DSO3.1 Validation Conflit</span>
                            </div>
                        </div>
                    </FloatingCard>
                )}
            </div>
        </div>
    );
}

export default function AgentsPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center h-full bg-[#080d18] text-slate-400">Chargement...</div>}>
            <SignalLabContent />
        </Suspense>
    );
}
