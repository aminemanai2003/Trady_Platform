"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
    Clock, TrendingUp, AlertCircle, CheckCircle2, AlertTriangle, Eye,
} from "lucide-react";
import { api } from "@/lib/api";
import type { FreshnessHealthV2 } from "@/types";
import { AnimatedCounter } from "@/components/animations";

interface FreshnessHealthCardProps {
    targetMinutes?: number;
    refreshInterval?: number; // in seconds
    className?: string;
}

export function FreshnessHealthCard({
    targetMinutes = 240,
    refreshInterval = 30,
    className = "",
}: FreshnessHealthCardProps) {
    const [freshness, setFreshness] = useState<FreshnessHealthV2 | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadFreshness = async () => {
        try {
            setError(null);
            const data = await api.v2.freshnessHealth(targetMinutes);
            setFreshness(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load freshness data");
            console.error("Freshness health error:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadFreshness();
        const interval = setInterval(loadFreshness, refreshInterval * 1000);
        return () => clearInterval(interval);
    }, [targetMinutes, refreshInterval]);

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

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className={className}
        >
            <Card className={`border-2 ${config.border} ${config.bg} backdrop-blur-sm`}>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className={`p-2 rounded-lg ${config.bg} border ${config.border}`}>
                                <Eye className={`size-4 ${config.text}`} />
                            </div>
                            <CardTitle className="text-sm font-semibold">Data Freshness</CardTitle>
                        </div>
                        {loading ? (
                            <Spinner className="size-4" />
                        ) : (
                            <Badge className={config.badge}>{config.label}</Badge>
                        )}
                    </div>
                </CardHeader>

                <CardContent className="space-y-4">
                    {error && (
                        <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded p-2">
                            {error}
                        </div>
                    )}

                    {data && (
                        <>
                            {/* Status Indicator Bar */}
                            <div className="space-y-2">
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-slate-400">Overall Freshness Score</span>
                                    <span className={`font-semibold ${config.text}`}>
                                        <AnimatedCounter
                                            to={data.freshness_score}
                                            duration={1}
                                            suffix="/100"
                                            decimals={1}
                                        />
                                    </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${freshnessFill}%` }}
                                        transition={{ duration: 0.8, ease: "easeOut" }}
                                        className={`h-full rounded-full ${
                                            data.status === "PASS"
                                                ? "bg-gradient-to-r from-emerald-500 to-teal-500"
                                                : data.status === "WARN"
                                                  ? "bg-gradient-to-r from-amber-500 to-orange-500"
                                                  : "bg-gradient-to-r from-rose-500 to-red-500"
                                        }`}
                                    />
                                </div>
                            </div>

                            {/* Data Types */}
                            <div className="space-y-2">
                                {dataTypeEntries.map(({ key, label, value }) => {
                                    const valueConfig = statusConfig[value.status || "NO_DATA"];
                                    const lastTs = "last_news_timestamp" in value
                                        ? value.last_news_timestamp
                                        : value.last_timestamp;
                                    return (
                                        <div
                                            key={key}
                                            className="bg-slate-800/50 rounded p-2 border border-slate-700/50 text-xs"
                                        >
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="text-slate-300 font-medium">{label}</span>
                                                <Badge className={`${valueConfig.badge} text-[10px] px-1.5 py-0`}>{value.status}</Badge>
                                            </div>
                                            <div className="grid grid-cols-2 gap-2">
                                                <div>
                                                    <div className="text-slate-400 flex items-center gap-1">
                                                        <Clock className="size-3" />
                                                        Age
                                                    </div>
                                                    <div className="text-slate-100 font-semibold">
                                                        {value.age_minutes !== null ? `${value.age_minutes} min` : "-"}
                                                    </div>
                                                    <div className="text-slate-500">Target: {value.target_max_age_minutes}min</div>
                                                </div>
                                                <div>
                                                    <div className="text-slate-400 flex items-center gap-1">
                                                        <TrendingUp className="size-3" />
                                                        Score
                                                    </div>
                                                    <div className="text-slate-100 font-semibold">{value.freshness_score}/100</div>
                                                    <div className="text-slate-500">
                                                        Last: {lastTs ? new Date(lastTs).toLocaleTimeString() : "Never"}
                                                    </div>
                                                </div>
                                            </div>
                                            {"latency" in value && value.latency && (
                                                <div className="mt-2 rounded border border-slate-700/60 bg-slate-900/40 p-2">
                                                    <div className="text-slate-400">Latency breakdown</div>
                                                    <div className="mt-1 grid grid-cols-3 gap-2 text-[11px]">
                                                        <div>
                                                            <div className="text-slate-500">Dephasing</div>
                                                            <div className="text-slate-200 font-medium">
                                                                {value.latency.source_access_lag_minutes !== null
                                                                    ? `${value.latency.source_access_lag_minutes} min`
                                                                    : "-"}
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <div className="text-slate-500">Extraction transfer</div>
                                                            <div className="text-slate-200 font-medium">
                                                                {value.latency.extraction_transfer_minutes} min
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <div className="text-slate-500">Total latency</div>
                                                            <div className="text-slate-100 font-semibold">
                                                                {value.latency.total_latency_minutes !== null
                                                                    ? `${value.latency.total_latency_minutes} min`
                                                                    : "-"}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                            {key === "news" && "articles_last_24h" in value && (
                                                <div className="text-slate-500 mt-1">
                                                    News flow: {value.articles_last_1h} /1h, {value.articles_last_24h} /24h
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {data.recommended_actions.length > 0 && (
                                <div className="space-y-1.5">
                                    <div className="text-[11px] uppercase tracking-wide text-slate-400">Recommended Actions</div>
                                    {data.recommended_actions.map((item, idx) => (
                                        <div
                                            key={`${item.data_type}-${idx}`}
                                            className="text-xs rounded border border-amber-500/20 bg-amber-500/10 p-2"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="font-medium text-amber-300">{item.data_type.toUpperCase()}</span>
                                                <Badge className="text-[10px] bg-amber-500/20 text-amber-300 border-amber-500/30">
                                                    {item.severity}
                                                </Badge>
                                            </div>
                                            <div className="text-slate-300 mt-1">{item.reason}</div>
                                            <div className="text-amber-200 mt-1">{item.action}</div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="pt-2 border-t border-slate-700/30">
                                <div className="flex justify-between items-center text-[11px] text-slate-500">
                                    <span>Last Check</span>
                                    <span>
                                        {freshness?.timestamp
                                            ? new Date(freshness.timestamp).toLocaleTimeString()
                                            : "-"}
                                    </span>
                                </div>
                            </div>
                        </>
                    )}

                    {loading && !data && (
                        <div className="flex items-center justify-center py-6">
                            <Spinner />
                        </div>
                    )}
                </CardContent>
            </Card>
        </motion.div>
    );
}

