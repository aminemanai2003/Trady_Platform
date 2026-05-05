"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
    Clock, TrendingUp, AlertCircle, CheckCircle2, AlertTriangle, Eye,
    Newspaper, Brain, BarChart2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { FreshnessHealthV2 } from "@/types";
import { AnimatedCounter } from "@/components/animations";

interface FreshnessHealthCardProps {
    refreshInterval?: number; // in seconds
    className?: string;
}

export function FreshnessHealthCard({
    refreshInterval = 300,
    className = "",
}: FreshnessHealthCardProps) {
    const [freshness, setFreshness] = useState<FreshnessHealthV2 | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [offline, setOffline] = useState(false);

    const loadFreshness = async () => {
        try {
            setError(null);
            const data = await api.v2.freshnessHealth();
            setFreshness(data);
            setOffline(false);
        } catch (err) {
            const isNetworkErr =
                err instanceof TypeError &&
                (err.message.toLowerCase().includes("fetch") ||
                    err.message.toLowerCase().includes("network"));
            // AbortError = 15s timeout (backend still starting)
            const isAbort = err instanceof DOMException && err.name === "AbortError";
            // ApiRequestError 5xx = backend starting up
            const isServerErr =
                err instanceof Error &&
                err.message.startsWith("API error: 5");
            if (isNetworkErr || isAbort || isServerErr) {
                setOffline(true);
                setError("Backend connecting…");
            } else {
                setOffline(false);
                setError(err instanceof Error ? err.message : "Failed to load freshness data");
                console.error("[FreshnessHealthCard]", err);
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void loadFreshness();
        // Retry every 15 s when backend is offline, otherwise use the normal interval
        const delay = offline ? 15 : refreshInterval;
        const interval = setInterval(() => void loadFreshness(), delay * 1000);
        return () => clearInterval(interval);
    }, [refreshInterval, offline]);

    const data = freshness?.freshness;
    const dataTypes = data?.data_types;

    // Status colors and icons
    const statusConfig = {
        PASS: {
            icon: CheckCircle2,
            bg: "bg-emerald-500/10",
            border: "border-emerald-500/20",
            badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
            text: "text-emerald-400",
            label: "Fresh Data",
        },
        WARN: {
            icon: AlertTriangle,
            bg: "bg-amber-500/10",
            border: "border-amber-500/20",
            badge: "bg-amber-500/20 text-amber-400 border-amber-500/30",
            text: "text-amber-400",
            label: "Aging Data",
        },
        NO_DATA: {
            icon: AlertCircle,
            bg: "bg-rose-500/10",
            border: "border-rose-500/20",
            badge: "bg-rose-500/20 text-rose-400 border-rose-500/30",
            text: "text-rose-400",
            label: "No Data",
        },
    };

    const config = statusConfig[data?.status || "NO_DATA"];
    const StatusIcon = config.icon;

    const freshnessFill = Math.max(0, Math.min(data?.freshness_score ?? 0, 100));

    const typeLabels: Record<string, string> = {
        news: "News",
        macro: "Macro",
        ohlcv: "OHLCV",
    };

    const dataTypeEntries = dataTypes
        ? Object.entries(dataTypes).map(([key, value]) => ({
              key,
              label: typeLabels[key] || key.toUpperCase(),
              value,
          }))
        : [];

    const sourceIcons: Record<string, React.ElementType> = {
        news: Newspaper,
        macro: Brain,
        ohlcv: BarChart2,
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className={className}
        >
            <Card className="border border-white/5 bg-white/[0.03] backdrop-blur-sm">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="p-2 rounded-lg bg-slate-800 border border-white/5">
                                <Eye className="size-4 text-slate-400" />
                            </div>
                            <div>
                                <CardTitle className="text-sm font-semibold text-white">Data Freshness</CardTitle>
                                <p className="text-[10px] text-slate-500">Live data pipeline monitoring — DSO3.1</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            {loading && <Spinner className="size-4" />}
                            {data && (
                                <>
                                    <div className="text-right">
                                        <div className={`text-xl font-bold ${config.text}`}>
                                            <AnimatedCounter to={data.freshness_score} duration={1} suffix="/100" decimals={1} />
                                        </div>
                                        <div className="text-[10px] text-slate-500">Overall Score</div>
                                    </div>
                                    <Badge className={config.badge}>{config.label}</Badge>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Progress bar */}
                    {data && (
                        <div className="mt-3 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${freshnessFill}%` }}
                                transition={{ duration: 0.8, ease: "easeOut" }}
                                className={`h-full rounded-full ${
                                    data.status === "PASS"
                                        ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                                        : data.status === "WARN"
                                          ? "bg-gradient-to-r from-amber-500 to-orange-400"
                                          : "bg-gradient-to-r from-rose-500 to-red-400"
                                }`}
                            />
                        </div>
                    )}
                </CardHeader>

                <CardContent className="space-y-4">
                    {error && (
                        <div className={`text-xs rounded p-2 ${
                            offline
                                ? "text-slate-400 bg-slate-800/60 border border-slate-700/40"
                                : "text-rose-400 bg-rose-500/10 border border-rose-500/20"
                        }`}>
                            {error}
                        </div>
                    )}

                    {data && (
                        <>
                            {/* 3-column source cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                {dataTypeEntries.map(({ key, label, value }) => {
                                    const valueConfig = statusConfig[value.status || "NO_DATA"];
                                    const ValueIcon = sourceIcons[key] ?? Eye;
                                    const lastTs = "last_news_timestamp" in value
                                        ? value.last_news_timestamp
                                        : value.last_timestamp;
                                    const scoreFill = Math.max(0, Math.min(value.freshness_score ?? 0, 100));
                                    return (
                                        <div
                                            key={key}
                                            className={`rounded-xl border ${valueConfig.border} ${valueConfig.bg} p-4 space-y-3`}
                                        >
                                            {/* Header */}
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div className={`p-1.5 rounded-lg ${valueConfig.bg} border ${valueConfig.border}`}>
                                                        <ValueIcon className={`size-3.5 ${valueConfig.text}`} />
                                                    </div>
                                                    <span className="text-sm font-semibold text-white">{label}</span>
                                                </div>
                                                <Badge className={`${valueConfig.badge} text-[10px] px-1.5 py-0`}>{value.status}</Badge>
                                            </div>

                                            {/* Score bar */}
                                            <div className="space-y-1">
                                                <div className="flex justify-between text-[11px]">
                                                    <span className="text-slate-400">Freshness score</span>
                                                    <span className={`font-bold ${valueConfig.text}`}>{value.freshness_score}/100</span>
                                                </div>
                                                <div className="h-1.5 rounded-full bg-slate-700/60 overflow-hidden">
                                                    <motion.div
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${scoreFill}%` }}
                                                        transition={{ duration: 0.8, ease: "easeOut" }}
                                                        className={`h-full rounded-full ${
                                                            value.status === "PASS"
                                                                ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                                                                : value.status === "WARN"
                                                                  ? "bg-gradient-to-r from-amber-500 to-orange-400"
                                                                  : "bg-gradient-to-r from-rose-500 to-red-400"
                                                        }`}
                                                    />
                                                </div>
                                            </div>

                                            {/* Stats */}
                                            <div className="grid grid-cols-2 gap-2 text-[11px]">
                                                <div className="bg-slate-900/40 rounded-lg p-2">
                                                    <div className="text-slate-500 flex items-center gap-1 mb-0.5">
                                                        <Clock className="size-3" /> Age
                                                    </div>
                                                    <div className="text-slate-100 font-semibold">
                                                        {value.age_minutes !== null
                                                            ? value.age_minutes > 1440
                                                                ? `${(value.age_minutes / 60).toFixed(0)}h`
                                                                : `${value.age_minutes}m`
                                                            : "-"}
                                                    </div>
                                                    <div className="text-slate-600">max {value.target_max_age_minutes >= 1440 ? `${value.target_max_age_minutes / 1440}d` : `${value.target_max_age_minutes}m`}</div>
                                                </div>
                                                <div className="bg-slate-900/40 rounded-lg p-2">
                                                    <div className="text-slate-500 flex items-center gap-1 mb-0.5">
                                                        <TrendingUp className="size-3" /> Last update
                                                    </div>
                                                    <div className="text-slate-100 font-semibold">
                                                        {lastTs ? new Date(lastTs).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Never"}
                                                    </div>
                                                    <div className="text-slate-600">
                                                        {lastTs ? new Date(lastTs).toLocaleDateString([], { month: "short", day: "numeric" }) : ""}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Latency */}
                                            {"latency" in value && value.latency && (
                                                <div className="rounded-lg border border-slate-700/40 bg-slate-900/30 p-2 text-[10px] space-y-1">
                                                    <div className="text-slate-500 uppercase tracking-wide font-medium">Latency</div>
                                                    <div className="flex justify-between">
                                                        <span className="text-slate-500">Source lag</span>
                                                        <span className="text-slate-300">
                                                            {value.latency.source_access_lag_minutes !== null
                                                                ? `${value.latency.source_access_lag_minutes > 60 ? (value.latency.source_access_lag_minutes / 60).toFixed(1) + "h" : value.latency.source_access_lag_minutes + "m"}`
                                                                : "-"}
                                                        </span>
                                                    </div>
                                                    <div className="flex justify-between">
                                                        <span className="text-slate-500">Transfer</span>
                                                        <span className="text-slate-300">{value.latency.extraction_transfer_minutes}m</span>
                                                    </div>
                                                    <div className="flex justify-between font-medium">
                                                        <span className="text-slate-400">Total</span>
                                                        <span className="text-slate-200">
                                                            {value.latency.total_latency_minutes !== null
                                                                ? `${value.latency.total_latency_minutes > 60 ? (value.latency.total_latency_minutes / 60).toFixed(1) + "h" : value.latency.total_latency_minutes + "m"}`
                                                                : "-"}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}

                                            {/* News flow */}
                                            {key === "news" && "articles_last_24h" in value && (
                                                <div className="flex gap-2 text-[10px]">
                                                    <div className="flex-1 bg-slate-900/40 rounded p-1.5 text-center">
                                                        <div className="text-slate-100 font-bold">{value.articles_last_1h}</div>
                                                        <div className="text-slate-500">/ 1h</div>
                                                    </div>
                                                    <div className="flex-1 bg-slate-900/40 rounded p-1.5 text-center">
                                                        <div className="text-slate-100 font-bold">{value.articles_last_24h}</div>
                                                        <div className="text-slate-500">/ 24h</div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Recommended Actions */}
                            {data.recommended_actions.length > 0 && (
                                <div className="space-y-1.5">
                                    <div className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">Recommended Actions</div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                        {data.recommended_actions.map((item, idx) => (
                                            <div
                                                key={`${item.data_type}-${idx}`}
                                                className="text-[11px] rounded-lg border border-amber-500/20 bg-amber-500/5 p-2.5"
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-semibold text-amber-300">{item.data_type.toUpperCase()}</span>
                                                    <Badge className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/30">{item.severity}</Badge>
                                                </div>
                                                <div className="text-slate-400">{item.reason}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Footer */}
                            <div className="flex justify-between items-center text-[10px] text-slate-600 pt-1 border-t border-white/5">
                                <span>Last check</span>
                                <span>{freshness?.timestamp ? new Date(freshness.timestamp).toLocaleTimeString() : "-"}</span>
                            </div>
                        </>
                    )}

                    {loading && !data && (
                        <div className="flex items-center justify-center py-8">
                            <Spinner />
                        </div>
                    )}
                </CardContent>
            </Card>
        </motion.div>
    );
}

