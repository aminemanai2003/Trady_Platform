"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RBContent, RBHeader } from "@/components/reactbits";
import {
    TrendingUp,
    Activity,
    Bot,
    Zap,
    LineChart,
    ArrowRight,
    Shield,
    Target,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { HealthCheckV2 } from "@/types";

const pairs = [
    { symbol: "EURUSD", name: "EUR/USD", description: "Euro vs US Dollar" },
    { symbol: "USDJPY", name: "USD/JPY", description: "US Dollar vs Japanese Yen" },
    { symbol: "GBPUSD", name: "GBP/USD", description: "British Pound vs US Dollar" },
    { symbol: "USDCHF", name: "USD/CHF", description: "US Dollar vs Swiss Franc" },
];

export default function DashboardPage() {
    const router = useRouter();
    const [health, setHealth] = useState<HealthCheckV2 | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadHealth = async () => {
            try {
                const data = await api.v2.healthCheck() as HealthCheckV2;
                setHealth(data);
            } catch (error) {
                console.error("Failed to load health:", error);
            }
            setLoading(false);
        };
        loadHealth();
        const interval = setInterval(loadHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const avgWinRate = health
        ? (
              (Object.values(health.agent_performances).reduce((sum, p) => sum + p.win_rate, 0) /
                  Object.values(health.agent_performances).length) *
              100
          ).toFixed(1)
        : 0;

    const totalSignals = health
        ? Object.values(health.agent_performances).reduce((sum, p) => sum + p.total_signals, 0)
        : 0;

    return (
        <div className="flex flex-col h-full bg-slate-950 text-slate-100">
            <RBHeader
                title="FX Alpha Platform"
                subtitle="Institutional Multi-Agent Trading System"
            />

            <RBContent className="space-y-6 lg:p-8">
                {/* Hero Section */}
                <Card className="border-2 border-violet-500/20 bg-gradient-to-br from-violet-500/5 to-transparent">
                    <CardContent className="p-8 lg:p-10">
                        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
                            <div className="flex-1">
                                <Badge className="mb-3 bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20">
                                    Production Ready
                                </Badge>
                                <h2 className="text-3xl lg:text-4xl font-bold mb-3">
                                    Advanced Multi-Agent System
                                </h2>
                                <p className="text-muted-foreground text-lg mb-6 max-w-2xl">
                                    Combine technical analysis, macroeconomic data, and sentiment analysis
                                    with AI-powered agents for institutional-grade FX trading signals.
                                </p>
                                <div className="flex flex-wrap gap-3">
                                    <Button
                                        onClick={() => router.push("/agents")}
                                        size="lg"
                                        className="bg-violet-500 hover:bg-violet-600 text-white"
                                    >
                                        <Bot className="size-4 mr-2" />
                                        View Agents
                                        <ArrowRight className="size-4 ml-2" />
                                    </Button>
                                    <Button
                                        onClick={() => router.push("/monitoring")}
                                        size="lg"
                                        variant="outline"
                                    >
                                        <Activity className="size-4 mr-2" />
                                        Monitoring Dashboard
                                    </Button>
                                </div>
                            </div>
                            <div className="hidden lg:flex items-center justify-center p-8 rounded-2xl bg-gradient-to-br from-violet-500/10 to-violet-500/5 border border-violet-500/20">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-violet-500/20 blur-3xl rounded-full"></div>
                                    <Bot className="size-24 text-violet-500 relative z-10" />
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* System Performance KPIs */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-emerald-500/10">
                                    <Activity className="size-5 text-emerald-500" />
                                </div>
                                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Status
                                </div>
                            </div>
                            <div className="text-2xl font-bold">
                                {health?.status === "operational" ? "OPERATIONAL" : "OFFLINE"}
                            </div>
                            <div className="mt-1 flex items-center gap-1">
                                <div className="size-2 rounded-full bg-emerald-500 animate-pulse"></div>
                                <span className="text-xs text-emerald-500">All Systems Online</span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-blue-500/10">
                                    <Bot className="size-5 text-blue-500" />
                                </div>
                                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Active Agents
                                </div>
                            </div>
                            <div className="text-2xl font-bold">
                                {health ? Object.keys(health.agent_performances).length : 0}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                                Technical - Macro - Sentiment
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-violet-500/10">
                                    <Zap className="size-5 text-violet-500" />
                                </div>
                                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Signals Generated
                                </div>
                            </div>
                            <div className="text-2xl font-bold">{totalSignals}</div>
                            <div className="text-xs text-muted-foreground mt-1">Last 30 days</div>
                        </CardContent>
                    </Card>

                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="p-2.5 rounded-lg bg-amber-500/10">
                                    <Target className="size-5 text-amber-500" />
                                </div>
                                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                    Avg Win Rate
                                </div>
                            </div>
                            <div className="text-2xl font-bold">{avgWinRate}%</div>
                            <div className="text-xs text-muted-foreground mt-1">
                                Across all agents
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Major Currency Pairs */}
                <Card className="border-border/50 bg-card/80 backdrop-blur">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <LineChart className="size-5" />
                            Major Currency Pairs
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {pairs.map((pair) => (
                                <div
                                    key={pair.symbol}
                                    className="group p-5 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/40 hover:border-violet-500/30 transition-all cursor-pointer"
                                    onClick={() => router.push(`/agents?pair=${pair.symbol}`)}
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <div>
                                            <div className="text-lg font-bold">{pair.name}</div>
                                            <div className="text-sm text-muted-foreground">
                                                {pair.description}
                                            </div>
                                        </div>
                                        <ArrowRight className="size-5 text-muted-foreground group-hover:text-violet-500 group-hover:translate-x-1 transition-all" />
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="w-full group-hover:bg-violet-500 group-hover:text-white group-hover:border-violet-500 transition-all"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            router.push(`/agents?pair=${pair.symbol}`);
                                        }}
                                    >
                                        <Zap className="size-3 mr-2" />
                                        Generate Signal
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Agent Performance Overview */}
                {health && (
                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardHeader>
                            <div className="flex items-center justify-between">
                                <CardTitle className="flex items-center gap-2">
                                    <Activity className="size-5" />
                                    Agent Performance Overview
                                </CardTitle>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => router.push("/agents")}
                                >
                                    View Details
                                    <ArrowRight className="size-3 ml-2" />
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {Object.entries(health.agent_performances).map(([type, perf]) => (
                                    <div
                                        key={type}
                                        className="p-4 rounded-lg border border-border/50 bg-muted/20"
                                    >
                                        <div className="flex items-center justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 rounded-lg bg-primary/10">
                                                    <Bot className="size-4 text-primary" />
                                                </div>
                                                <div>
                                                    <div className="font-semibold capitalize">
                                                        {type} Agent
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">
                                                        {perf.total_signals} signals generated
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-4 gap-4 text-sm">
                                            <div className="text-center p-3 rounded-lg bg-background/50">
                                                <div className="text-muted-foreground text-xs mb-1">
                                                    Win Rate
                                                </div>
                                                <div className="font-bold text-emerald-500">
                                                    {(perf.win_rate * 100).toFixed(1)}%
                                                </div>
                                            </div>
                                            <div className="text-center p-3 rounded-lg bg-background/50">
                                                <div className="text-muted-foreground text-xs mb-1">
                                                    Sharpe Ratio
                                                </div>
                                                <div className="font-bold">
                                                    {perf.sharpe_ratio.toFixed(2)}
                                                </div>
                                            </div>
                                            <div className="text-center p-3 rounded-lg bg-background/50">
                                                <div className="text-muted-foreground text-xs mb-1">
                                                    Max Drawdown
                                                </div>
                                                <div className="font-bold text-rose-500">
                                                    {(perf.max_drawdown * 100).toFixed(1)}%
                                                </div>
                                            </div>
                                            <div className="text-center p-3 rounded-lg bg-background/50">
                                                <div className="text-muted-foreground text-xs mb-1">
                                                    Total PnL
                                                </div>
                                                <div
                                                    className={`font-bold ${
                                                        perf.total_pnl >= 0
                                                            ? "text-emerald-500"
                                                            : "text-rose-500"
                                                    }`}
                                                >
                                                    {perf.total_pnl >= 0 ? "+" : ""}
                                                    {perf.total_pnl.toFixed(2)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Feature Highlights */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-6">
                            <div className="p-3 rounded-lg bg-violet-500/10 w-fit mb-4">
                                <Bot className="size-6 text-violet-500" />
                            </div>
                            <h3 className="font-bold text-lg mb-2">Multi-Agent System</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                Three specialized agents (Technical, Macro, Sentiment) collaborate to
                                generate high-confidence trading signals with coordinated decision-making.
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-6">
                            <div className="p-3 rounded-lg bg-blue-500/10 w-fit mb-4">
                                <Shield className="size-6 text-blue-500" />
                            </div>
                            <h3 className="font-bold text-lg mb-2">Production Architecture</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                100% deterministic trading logic with LLM used only for classification.
                                Includes drift detection, safety monitors, and performance tracking.
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-6">
                            <div className="p-3 rounded-lg bg-emerald-500/10 w-fit mb-4">
                                <Activity className="size-6 text-emerald-500" />
                            </div>
                            <h3 className="font-bold text-lg mb-2">Real-Time Monitoring</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                Track agent performance, detect distribution drift, and enforce safety
                                rules with comprehensive monitoring and alerting capabilities.
                            </p>
                        </CardContent>
                    </Card>
                </div>
            </RBContent>
        </div>
    );
}


