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

    const freshnessFill = {
        PASS: 100,
        WARN: 66,
        NO_DATA: 0,
    }[data?.status || "NO_DATA"];

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
                                    <span className="text-slate-400">Freshness Score</span>
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

                            {/* Metrics Grid */}
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                {/* Age */}
                                <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
                                    <div className="flex items-center gap-1 text-slate-400 mb-1">
                                        <Clock className="size-3" />
                                        <span>Age</span>
                                    </div>
                                    <div className="font-semibold text-slate-100">
                                        {data.age_minutes !== null ? (
                                            <>
                                                <AnimatedCounter
                                                    to={data.age_minutes}
                                                    duration={1}
                                                    decimals={1}
                                                />{" "}
                                                min
                                            </>
                                        ) : (
                                            "-"
                                        )}
                                    </div>
                                    <div className="text-slate-500 mt-0.5">
                                        Target: {data.target_max_age_minutes}min
                                    </div>
                                </div>

                                {/* 24h Articles */}
                                <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
                                    <div className="flex items-center gap-1 text-slate-400 mb-1">
                                        <TrendingUp className="size-3" />
                                        <span>Articles/24h</span>
                                    </div>
                                    <div className="font-semibold text-slate-100">
                                        <AnimatedCounter to={data.articles_last_24h} duration={1} />
                                    </div>
                                    <div className="text-slate-500 mt-0.5">
                                        Last 1h: {data.articles_last_1h}
                                    </div>
                                </div>
                            </div>

                            {/* Last Update */}
                            <div className="pt-2 border-t border-slate-700/30">
                                <div className="flex justify-between items-center text-[11px] text-slate-500">
                                    <span>Last Update</span>
                                    <span>
                                        {data.last_news_timestamp
                                            ? new Date(data.last_news_timestamp).toLocaleTimeString()
                                            : "Never"}
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

