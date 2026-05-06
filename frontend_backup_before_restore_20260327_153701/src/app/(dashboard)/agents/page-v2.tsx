"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    Bot,
    Brain,
    TrendingUp,
    Newspaper,
    Layers,
    Zap,
    Activity,
    RefreshCw,
    ChevronRight,
    AlertCircle,
    CheckCircle2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { SignalResponseV2, HealthCheckV2, DriftDetectionV2 } from "@/types";

const agentConfig = {
    technical: {
        icon: TrendingUp,
        color: "text-emerald-400",
        bgColor: "bg-emerald-500/10",
        name: "Technical Agent",
        description: "RSI, MACD, Bollinger Bands",
    },
    macro: {
        icon: Brain,
        color: "text-blue-400",
        bgColor: "bg-blue-500/10",
        name: "Macro Agent",
        description: "Interest rates, economic data",
    },
    sentiment: {
        icon: Newspaper,
        color: "text-amber-400",
        bgColor: "bg-amber-500/10",
        name: "Sentiment Agent",
        description: "News analysis, market sentiment",
    },
};

export default function AgentsPageV2() {
    const [signal, setSignal] = useState<SignalResponseV2 | null>(null);
    const [health, setHealth] = useState<HealthCheckV2 | null>(null);
    const [drift, setDrift] = useState<DriftDetectionV2 | null>(null);
    const [loading, setLoading] = useState(false);
    const [pair, setPair] = useState("EURUSD");

    const loadData = async () => {
        setLoading(true);
        try {
            const [healthData, driftData] = await Promise.all([
                api.v2.healthCheck(),
                api.v2.driftDetection(),
            ]);
            setHealth(healthData);
            setDrift(driftData);
        } catch (error) {
            console.error("Failed to load monitoring data:", error);
        }
        setLoading(false);
    };

    const generateSignal = async () => {
        setLoading(true);
        try {
            const signalData = await api.v2.generateSignal(pair);
            setSignal(signalData);
            await loadData(); // Refresh monitoring data
        } catch (error) {
            console.error("Failed to generate signal:", error);
        }
        setLoading(false);
    };

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const getSignalColor = (direction: string) => {
        switch (direction) {
            case "BUY":
                return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
            case "SELL":
                return "bg-rose-500/20 text-rose-400 border-rose-500/30";
            default:
                return "bg-slate-500/20 text-slate-400 border-slate-500/30";
        }
    };

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
            {/* Header */}
            <header className="flex h-16 shrink-0 items-center gap-4 border-b border-white/5 px-6 bg-black/20 backdrop-blur-xl">
                <SidebarTrigger className="-ml-1" />
                <Separator orientation="vertical" className="h-6 bg-white/10" />
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-violet-500/10">
                        <Layers className="size-5 text-violet-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white">Multi-Agent System V2</h1>
                        <p className="text-xs text-slate-400">Production Architecture</p>
                    </div>
                </div>
                <div className="ml-auto flex items-center gap-3">
                    <select
                        value={pair}
                        onChange={(e) => setPair(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-white"
                    >
                        <option value="EURUSD">EUR/USD</option>
                        <option value="USDJPY">USD/JPY</option>
                        <option value="GBPUSD">GBP/USD</option>
                        <option value="USDCHF">USD/CHF</option>
                    </select>
                    <Button
                        onClick={generateSignal}
                        disabled={loading}
                        className="bg-violet-500 hover:bg-violet-600 text-white"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="size-4 mr-2 animate-spin" />
                                Processing...
                            </>
                        ) : (
                            <>
                                <Zap className="size-4 mr-2" />
                                Generate Signal
                            </>
                        )}
                    </Button>
                </div>
            </header>

            <div className="flex-1 overflow-auto p-6 space-y-6">
                {/* System Status */}
                {health && (
                    <div className="grid grid-cols-4 gap-4">
                        <Card className="border-emerald-500/20 bg-emerald-500/5 backdrop-blur">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-emerald-500/10">
                                    <CheckCircle2 className="size-5 text-emerald-400" />
                                </div>
                                <div>
                                    <div className="text-2xl font-bold text-white">
                                        {health.status.toUpperCase()}
                                    </div>
                                    <div className="text-xs text-slate-400">System Status</div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-white/10 bg-white/5 backdrop-blur">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-blue-500/10">
                                    <Activity className="size-5 text-blue-400" />
                                </div>
                                <div>
                                    <div className="text-2xl font-bold text-white">
                                        {Math.round(health.system.uptime_seconds / 60)}m
                                    </div>
                                    <div className="text-xs text-slate-400">Uptime</div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-white/10 bg-white/5 backdrop-blur">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-violet-500/10">
                                    <Bot className="size-5 text-violet-400" />
                                </div>
                                <div>
                                    <div className="text-2xl font-bold text-white">
                                        {Object.keys(health.agent_performances).length}
                                    </div>
                                    <div className="text-xs text-slate-400">Active Agents</div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-white/10 bg-white/5 backdrop-blur">
                            <CardContent className="p-4 flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-amber-500/10">
                                    <AlertCircle className="size-5 text-amber-400" />
                                </div>
                                <div>
                                    <div className="text-2xl font-bold text-white">
                                        {drift?.sentiment_drift.detected ? "YES" : "NO"}
                                    </div>
                                    <div className="text-xs text-slate-400">Drift Detected</div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Latest Signal */}
                {signal && signal.success && (
                    <Card className="border-violet-500/20 bg-gradient-to-br from-violet-500/10 to-transparent backdrop-blur">
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-white flex items-center gap-2">
                                    <Zap className="size-5 text-violet-400" />
                                    Latest Signal - {pair}
                                </CardTitle>
                                <Badge
                                    variant="outline"
                                    className={getSignalColor(signal.signal.direction)}
                                >
                                    {signal.signal.direction}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-3 gap-4">
                                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-xs text-slate-400 mb-1">Confidence</div>
                                    <div className="text-2xl font-bold text-white">
                                        {(signal.signal.confidence * 100).toFixed(0)}%
                                    </div>
                                    <Progress
                                        value={signal.signal.confidence * 100}
                                        className="h-1 mt-2"
                                    />
                                </div>
                                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-xs text-slate-400 mb-1">Weighted Score</div>
                                    <div className="text-2xl font-bold text-white">
                                        {signal.signal.weighted_score.toFixed(3)}
                                    </div>
                                </div>
                                <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                    <div className="text-xs text-slate-400 mb-1">Market Regime</div>
                                    <div className="text-lg font-bold text-white capitalize">
                                        {signal.signal.market_regime}
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
                                <div className="text-xs text-slate-400 mb-2">Reasoning</div>
                                <p className="text-sm text-slate-200 leading-relaxed">
                                    {signal.signal.reasoning}
                                </p>
                            </div>

                            {signal.signal.conflicts.length > 0 && (
                                <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                                    <div className="flex items-center gap-2 mb-2">
                                        <AlertCircle className="size-4 text-amber-400" />
                                        <div className="text-xs font-semibold text-amber-400">
                                            Conflicts Detected
                                        </div>
                                    </div>
                                    <ul className="text-xs text-amber-200 space-y-1">
                                        {signal.signal.conflicts.map((conflict, i) => (
                                            <li key={i}>• {conflict}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Agent Votes */}
                {signal && signal.success && (
                    <div className="grid grid-cols-3 gap-4">
                        {Object.entries(signal.signal.agent_votes).map(([agentType, vote]) => {
                            const config = agentConfig[agentType as keyof typeof agentConfig];
                            if (!config) return null;

                            return (
                                <Card
                                    key={agentType}
                                    className="border-white/10 bg-white/5 backdrop-blur hover:bg-white/10 transition-all"
                                >
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${config.bgColor}`}>
                                                <config.icon className={`size-5 ${config.color}`} />
                                            </div>
                                            <div className="flex-1">
                                                <CardTitle className="text-sm text-white">
                                                    {config.name}
                                                </CardTitle>
                                                <p className="text-xs text-slate-400">
                                                    {config.description}
                                                </p>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <Badge
                                                variant="outline"
                                                className={getSignalColor(vote.signal)}
                                            >
                                                {vote.signal}
                                            </Badge>
                                            <span className="text-lg font-bold text-white">
                                                {(vote.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <Progress value={vote.confidence * 100} className="h-1.5" />
                                        <div className="p-3 rounded-lg bg-black/20 border border-white/5">
                                            <p className="text-xs text-slate-300 leading-relaxed">
                                                {vote.reasoning}
                                            </p>
                                        </div>
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-slate-400">Weight</span>
                                            <span className="font-semibold text-white">
                                                {(
                                                    signal.signal.weights[
                                                        agentType as keyof typeof signal.signal.weights
                                                    ] * 100
                                                ).toFixed(0)}
                                                %
                                            </span>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}

                {/* Agent Performance */}
                {health && (
                    <Card className="border-white/10 bg-white/5 backdrop-blur">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <Activity className="size-5 text-blue-400" />
                                Agent Performance (30 Days)
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {Object.entries(health.agent_performances).map(
                                    ([agentType, perf]) => {
                                        const config =
                                            agentConfig[
                                                agentType.toLowerCase() as keyof typeof agentConfig
                                            ];
                                        if (!config) return null;

                                        return (
                                            <div
                                                key={agentType}
                                                className="p-4 rounded-lg bg-black/20 border border-white/5"
                                            >
                                                <div className="flex items-center justify-between mb-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className={`p-2 rounded-lg ${config.bgColor}`}>
                                                            <config.icon
                                                                className={`size-4 ${config.color}`}
                                                            />
                                                        </div>
                                                        <span className="font-semibold text-white">
                                                            {config.name}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-4 text-sm">
                                                        <div>
                                                            <span className="text-slate-400">Win Rate: </span>
                                                            <span className="font-bold text-emerald-400">
                                                                {(perf.win_rate * 100).toFixed(1)}%
                                                            </span>
                                                        </div>
                                                        <div>
                                                            <span className="text-slate-400">Sharpe: </span>
                                                            <span className="font-bold text-white">
                                                                {perf.sharpe_ratio.toFixed(2)}
                                                            </span>
                                                        </div>
                                                        <div>
                                                            <span className="text-slate-400">Signals: </span>
                                                            <span className="font-bold text-white">
                                                                {perf.total_signals}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-4 gap-3 text-xs">
                                                    <div className="p-2 rounded bg-white/5 text-center">
                                                        <div className="text-slate-400">Accuracy</div>
                                                        <div className="font-bold text-white mt-1">
                                                            {(perf.last_30d_accuracy * 100).toFixed(1)}%
                                                        </div>
                                                    </div>
                                                    <div className="p-2 rounded bg-white/5 text-center">
                                                        <div className="text-slate-400">Max DD</div>
                                                        <div className="font-bold text-rose-400 mt-1">
                                                            {(perf.max_drawdown * 100).toFixed(1)}%
                                                        </div>
                                                    </div>
                                                    <div className="p-2 rounded bg-white/5 text-center">
                                                        <div className="text-slate-400">Avg Conf</div>
                                                        <div className="font-bold text-white mt-1">
                                                            {(perf.avg_confidence * 100).toFixed(0)}%
                                                        </div>
                                                    </div>
                                                    <div className="p-2 rounded bg-white/5 text-center">
                                                        <div className="text-slate-400">Total PnL</div>
                                                        <div
                                                            className={`font-bold mt-1 ${
                                                                perf.total_pnl >= 0
                                                                    ? "text-emerald-400"
                                                                    : "text-rose-400"
                                                            }`}
                                                        >
                                                            {perf.total_pnl >= 0 ? "+" : ""}
                                                            {perf.total_pnl.toFixed(2)}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    }
                                )}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Initial State */}
                {!signal && !loading && (
                    <Card className="border-white/10 bg-white/5 backdrop-blur">
                        <CardContent className="p-12 text-center">
                            <div className="p-4 rounded-full bg-violet-500/10 w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                                <Layers className="size-8 text-violet-400" />
                            </div>
                            <h3 className="text-xl font-bold text-white mb-2">
                                Ready to Generate Signal
                            </h3>
                            <p className="text-slate-400 mb-6">
                                Select a currency pair and click "Generate Signal" to see the multi-agent
                                system in action.
                            </p>
                            <Button
                                onClick={generateSignal}
                                className="bg-violet-500 hover:bg-violet-600 text-white"
                            >
                                <Zap className="size-4 mr-2" />
                                Generate First Signal
                            </Button>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
