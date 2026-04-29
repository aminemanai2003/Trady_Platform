"use client";

import { motion } from "framer-motion";
import {
    RadarChart, PolarGrid, PolarAngleAxis, Radar,
    ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, Cell,
} from "recharts";
import { Brain, TrendingUp, Newspaper, Globe, Layers } from "lucide-react";
import type { XaiAgentBreakdown } from "@/types";

interface Props {
    agentBreakdown: XaiAgentBreakdown;
    explanation?: Record<string, unknown>;
    pair?: string;
}

const AGENT_META: Record<string, { label: string; icon: React.ElementType; color: string; hex: string }> = {
    TechnicalV2:    { label: "Technical",    icon: TrendingUp, color: "text-emerald-400", hex: "#10b981" },
    MacroV2:        { label: "Macro",        icon: Brain,      color: "text-blue-400",    hex: "#3b82f6" },
    SentimentV2:    { label: "Sentiment",    icon: Newspaper,  color: "text-amber-400",   hex: "#f59e0b" },
    GeopoliticalV2: { label: "Geopolitical", icon: Globe,      color: "text-violet-400",  hex: "#8b5cf6" },
};

const SIGNAL_STYLE: Record<string, string> = {
    BUY:     "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    SELL:    "bg-rose-500/15 text-rose-400 border-rose-500/30",
    NEUTRAL: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

export function XaiBreakdown({ agentBreakdown, pair }: Props) {
    const agents = Object.entries(agentBreakdown).filter(([, v]) => v !== undefined);

    // Radar data: contribution strength per agent
    const radarData = agents.map(([key, v]) => ({
        agent: AGENT_META[key]?.label ?? key,
        confidence: Math.round((v!.confidence ?? 0) * 100),
        weight: Math.round((v!.weight ?? 0) * 100),
        influence: Math.round(Math.abs(v!.contribution ?? 0) * 100),
    }));

    // Bar data: contribution direction (positive = BUY direction)
    const barData = agents
        .map(([key, v]) => ({
            name: AGENT_META[key]?.label ?? key,
            value: Number(((v!.contribution ?? 0) * 100).toFixed(1)),
            hex: AGENT_META[key]?.hex ?? "#64748b",
        }))
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    // Rank by influence
    const ranked = [...agents].sort(
        (a, b) => (a[1]!.influence_rank ?? 99) - (b[1]!.influence_rank ?? 99)
    );

    return (
        <div className="space-y-5" data-tour="xai-breakdown">
            {/* Header */}
            <div className="flex items-center gap-2">
                <Layers className="size-4 text-violet-400" />
                <span className="text-sm font-bold text-white">XAI Agent Breakdown</span>
                {pair && (
                    <span className="text-[10px] font-mono border border-violet-500/30 bg-violet-500/10 text-violet-400 px-1.5 py-0.5 rounded">
                        {pair}
                    </span>
                )}
            </div>

            {/* Radar + Bar side-by-side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Radar — agent influence */}
                <div className="p-4 rounded-xl border border-white/5 bg-white/[0.03]">
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Agent Contributions</p>
                    <ResponsiveContainer width="100%" height={200}>
                        <RadarChart data={radarData}>
                            <PolarGrid stroke="#334155" />
                            <PolarAngleAxis dataKey="agent" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                            <Radar name="Confidence" dataKey="confidence" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.15} />
                            <Radar name="Influence"  dataKey="influence"  stroke="#10b981" fill="#10b981" fillOpacity={0.1}  />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>

                {/* Bar — directional contribution */}
                <div className="p-4 rounded-xl border border-white/5 bg-white/[0.03]">
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Directional Contribution (%)</p>
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={barData} layout="vertical">
                            <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
                            <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} tickLine={false} axisLine={false} width={80} />
                            <RechartsTooltip
                                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
                                formatter={(v: number) => [`${v > 0 ? "+" : ""}${v}%`, "Contribution"]}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                                {barData.map((entry, i) => (
                                    <Cell key={i} fill={entry.value >= 0 ? "#10b981" : "#f43f5e"} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Agent cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {ranked.map(([key, agent], i) => {
                    if (!agent) return null;
                    const meta = AGENT_META[key] ?? { label: key, icon: Layers, color: "text-slate-400", hex: "#64748b" };
                    const Icon = meta.icon;
                    const signalClass = SIGNAL_STYLE[agent.signal] ?? SIGNAL_STYLE.NEUTRAL;

                    return (
                        <motion.div
                            key={key}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.07 }}
                            className="p-4 rounded-xl border border-white/5 bg-white/[0.03] space-y-2.5"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Icon className={`size-4 ${meta.color}`} />
                                    <span className="text-sm font-semibold text-white">{meta.label}</span>
                                    {agent.influence_rank === 1 && (
                                        <span className="text-[9px] bg-violet-500/20 text-violet-400 border border-violet-500/30 px-1.5 py-0.5 rounded-full font-bold">
                                            Most Influential
                                        </span>
                                    )}
                                </div>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${signalClass}`}>
                                    {agent.signal}
                                </span>
                            </div>

                            {/* Confidence bar */}
                            <div>
                                <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                                    <span>Confidence</span>
                                    <span className={meta.color}>{Math.round((agent.confidence ?? 0) * 100)}%</span>
                                </div>
                                <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${(agent.confidence ?? 0) * 100}%` }}
                                        transition={{ duration: 0.6, delay: i * 0.07 + 0.2 }}
                                        className="h-full rounded-full"
                                        style={{ background: meta.hex }}
                                    />
                                </div>
                            </div>

                            {/* Key features */}
                            {agent.key_features?.length > 0 && (
                                <ul className="space-y-0.5">
                                    {agent.key_features.map((f, fi) => (
                                        <li key={fi} className="text-[10px] text-slate-400 flex items-start gap-1">
                                            <span className="text-slate-600 mt-0.5">·</span>
                                            {f}
                                        </li>
                                    ))}
                                </ul>
                            )}

                            {/* Geopolitical events */}
                            {key === "GeopoliticalV2" && agent.key_events?.length ? (
                                <div className="pt-1.5 border-t border-white/5">
                                    <p className="text-[10px] text-violet-400 font-semibold mb-1">Key Events</p>
                                    {agent.key_events.map((ev, ei) => (
                                        <p key={ei} className="text-[10px] text-slate-500 truncate">{ev}</p>
                                    ))}
                                </div>
                            ) : null}

                            {/* Reasoning snippet */}
                            {agent.reasoning && (
                                <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">{agent.reasoning}</p>
                            )}
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
