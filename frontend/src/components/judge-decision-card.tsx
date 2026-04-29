"use client";

import { motion } from "framer-motion";
import { Scale, CheckCircle2, XCircle, AlertTriangle, Clock } from "lucide-react";

type Verdict = "APPROVE" | "REJECT" | "MODIFY" | string;

interface Props {
    verdict: Verdict;
    reasoning: string;
    latencyMs?: number;
    fromCache?: boolean;
    confidence?: number;
}

const VERDICT_CONFIG: Record<string, { label: string; icon: React.ElementType; bg: string; border: string; text: string; dot: string }> = {
    APPROVE: {
        label: "APPROVED",
        icon: CheckCircle2,
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/30",
        text: "text-emerald-400",
        dot: "#10b981",
    },
    REJECT: {
        label: "REJECTED",
        icon: XCircle,
        bg: "bg-rose-500/10",
        border: "border-rose-500/30",
        text: "text-rose-400",
        dot: "#f43f5e",
    },
    MODIFY: {
        label: "MODIFIED",
        icon: AlertTriangle,
        bg: "bg-amber-500/10",
        border: "border-amber-500/30",
        text: "text-amber-400",
        dot: "#f59e0b",
    },
};

export function JudgeDecisionCard({ verdict, reasoning, latencyMs, fromCache, confidence }: Props) {
    const cfg = VERDICT_CONFIG[verdict] ?? VERDICT_CONFIG.REJECT;
    const Icon = cfg.icon;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`rounded-xl border p-4 space-y-3 ${cfg.bg} ${cfg.border}`}
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Scale className="size-4 text-slate-400" />
                    <span className="text-sm font-bold text-white">LLM Judge</span>
                    <span className="text-[10px] text-slate-500 font-mono border border-slate-700 rounded px-1.5">Ollama · llama3.2:3b</span>
                </div>
                <div className="flex items-center gap-2">
                    {fromCache && (
                        <span className="text-[9px] text-slate-500 border border-slate-700 rounded px-1.5 py-0.5 font-mono">
                            cached
                        </span>
                    )}
                    {latencyMs != null && (
                        <span className="flex items-center gap-1 text-[10px] text-slate-500">
                            <Clock className="size-3" />
                            {latencyMs}ms
                        </span>
                    )}
                </div>
            </div>

            {/* Verdict badge */}
            <div className="flex items-center gap-3">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${cfg.bg} ${cfg.border}`}>
                    <Icon className={`size-4 ${cfg.text}`} />
                    <span className={`text-sm font-bold ${cfg.text}`}>{cfg.label}</span>
                </div>
                {confidence != null && (
                    <div className="text-sm text-slate-400">
                        <span className="text-white font-bold">{Math.round(confidence * 100)}%</span>
                        <span className="text-slate-500 text-xs ml-1">confidence</span>
                    </div>
                )}
            </div>

            {/* Reasoning */}
            {reasoning && (
                <div className="p-3 rounded-lg bg-black/20 border border-white/5">
                    <p className="text-[11px] text-slate-500 mb-1 uppercase tracking-wider font-semibold">Reasoning</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{reasoning}</p>
                </div>
            )}
        </motion.div>
    );
}
