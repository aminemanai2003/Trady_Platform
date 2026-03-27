"use client";

import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Key,
    Bot,
    Bell,
    Shield,
    Database,
    Globe,
    Save,
    CheckCircle2,
    AlertTriangle,
    Sliders,
    Clock,
} from "lucide-react";

const apiKeys = [
    { name: "FRED API Key", key: "FRED_API_KEY", status: "configured", masked: "********3f2a" },
    { name: "MetaTrader 5", key: "MT5_LOGIN", status: "configured", masked: "******5421" },
    { name: "InfluxDB Token", key: "INFLUXDB_TOKEN", status: "configured", masked: "********kx7q" },
    { name: "PostgreSQL", key: "POSTGRES_PASSWORD", status: "configured", masked: "********" },
    { name: "OpenAI API Key", key: "OPENAI_API_KEY", status: "not_set", masked: "Not configured" },
    { name: "Anthropic API Key", key: "ANTHROPIC_API_KEY", status: "not_set", masked: "Not configured" },
    { name: "LangFuse Secret", key: "LANGFUSE_SECRET_KEY", status: "not_set", masked: "Not configured" },
];

const agentConfig = [
    { agent: "Macro Agent", model: "GPT-4", maxTokens: 3000, temperature: 0.3, enabled: true, cronSchedule: "*/5 * * * *" },
    { agent: "Technical Agent", model: "Local (rules-based)", maxTokens: 0, temperature: 0, enabled: true, cronSchedule: "*/5 * * * *" },
    { agent: "Sentiment Agent", model: "Claude 3 Sonnet", maxTokens: 4000, temperature: 0.2, enabled: true, cronSchedule: "*/10 * * * *" },
    { agent: "Orchestrator", model: "GPT-4", maxTokens: 1000, temperature: 0.1, enabled: true, cronSchedule: "*/5 * * * *" },
];

const notificationSettings = [
    { label: "New Alpha Signal", description: "When orchestrator generates BUY/SELL", enabled: true },
    { label: "High Confidence Signal (>80%)", description: "Only strong conviction signals", enabled: true },
    { label: "Agent Offline Alert", description: "When any agent goes offline", enabled: true },
    { label: "Drawdown Warning (>10%)", description: "Portfolio risk exceeds threshold", enabled: true },
    { label: "Daily Performance Summary", description: "End-of-day P&L and KPI report", enabled: false },
    { label: "Economic Calendar Reminders", description: "30 min before HIGH impact events", enabled: true },
];

export default function SettingsPage() {
    return (
        <div className="flex flex-col h-full">
            <header className="flex h-14 shrink-0 items-center gap-2 border-b px-6">
                <SidebarTrigger className="-ml-1" />
                <Separator orientation="vertical" className="mr-2 h-4" />
                <h1 className="text-lg font-semibold">Settings</h1>
            </header>

            <div className="flex-1 overflow-auto p-6 space-y-6">
                <Tabs defaultValue="api" className="space-y-4">
                    <TabsList className="bg-muted/50">
                        <TabsTrigger value="api">API Keys</TabsTrigger>
                        <TabsTrigger value="agents">Agent Config</TabsTrigger>
                        <TabsTrigger value="notifications">Notifications</TabsTrigger>
                        <TabsTrigger value="risk">Risk Management</TabsTrigger>
                    </TabsList>

                    {/* API Keys Tab */}
                    <TabsContent value="api" className="space-y-4">
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Key className="size-4" /> API Keys & Connections
                                </CardTitle>
                                <CardDescription>Manage external service credentials (stored in .env)</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {apiKeys.map((api) => (
                                    <div key={api.key} className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                        <div className="flex items-center gap-3">
                                            {api.status === "configured" ?
                                                <CheckCircle2 className="size-4 text-emerald-400" /> :
                                                <AlertTriangle className="size-4 text-amber-400" />
                                            }
                                            <div>
                                                <div className="text-sm font-medium">{api.name}</div>
                                                <div className="text-xs text-muted-foreground font-mono">{api.key}</div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-mono text-muted-foreground">{api.masked}</span>
                                            <Badge variant="outline" className={api.status === "configured" ?
                                                "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                                                "bg-amber-500/20 text-amber-400 border-amber-500/30"
                                            }>
                                                {api.status === "configured" ? "Active" : "Not Set"}
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Agent Config Tab */}
                    <TabsContent value="agents" className="space-y-4">
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Bot className="size-4" /> Agent Configuration
                                </CardTitle>
                                <CardDescription>LLM models, parameters, and scheduling</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {agentConfig.map((agent) => (
                                    <div key={agent.agent} className="p-4 rounded-lg bg-muted/20 border border-border/30 space-y-3">
                                        <div className="flex items-center justify-between">
                                            <div className="font-medium text-sm">{agent.agent}</div>
                                            <Badge variant="outline" className={agent.enabled ?
                                                "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                                                "bg-slate-500/20 text-slate-400 border-slate-500/30"
                                            }>
                                                {agent.enabled ? "Enabled" : "Disabled"}
                                            </Badge>
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                            <div className="p-2 rounded bg-muted/30">
                                                <span className="text-muted-foreground">Model</span>
                                                <div className="font-medium mt-1">{agent.model}</div>
                                            </div>
                                            <div className="p-2 rounded bg-muted/30">
                                                <span className="text-muted-foreground">Max Tokens</span>
                                                <div className="font-mono font-medium mt-1">{agent.maxTokens || "N/A"}</div>
                                            </div>
                                            <div className="p-2 rounded bg-muted/30">
                                                <span className="text-muted-foreground">Temperature</span>
                                                <div className="font-mono font-medium mt-1">{agent.temperature}</div>
                                            </div>
                                            <div className="p-2 rounded bg-muted/30">
                                                <span className="text-muted-foreground">Schedule</span>
                                                <div className="font-mono font-medium mt-1">{agent.cronSchedule}</div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Notifications Tab */}
                    <TabsContent value="notifications" className="space-y-4">
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Bell className="size-4" /> Notification Preferences
                                </CardTitle>
                                <CardDescription>Configure alerts for trading events</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {notificationSettings.map((n) => (
                                    <div key={n.label} className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                        <div>
                                            <div className="text-sm font-medium">{n.label}</div>
                                            <div className="text-xs text-muted-foreground">{n.description}</div>
                                        </div>
                                        <div className={`w-10 h-5 rounded-full flex items-center px-0.5 cursor-pointer transition-colors ${n.enabled ? "bg-emerald-600 justify-end" : "bg-muted justify-start"}`}>
                                            <div className="w-4 h-4 rounded-full bg-white shadow" />
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Risk Management Tab */}
                    <TabsContent value="risk" className="space-y-4">
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Shield className="size-4" /> Risk Management Rules
                                </CardTitle>
                                <CardDescription>Position sizing, limits, and safety rules</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {[
                                    { label: "Max Position Size", value: "0.5 lots", desc: "Maximum lot size per trade" },
                                    { label: "Max Daily Loss", value: "$500", desc: "Auto-stop if daily loss exceeds" },
                                    { label: "Max Drawdown", value: "15%", desc: "Halt trading if drawdown exceeds" },
                                    { label: "Max Open Positions", value: "4", desc: "One per currency pair" },
                                    { label: "Min Consensus", value: "2/3 agents", desc: "4-eyes principle - at least 2 agents agree" },
                                    { label: "Min Confidence", value: "60%", desc: "Signal below threshold -> NEUTRAL" },
                                    { label: "Default Stop Loss", value: "40 pips", desc: "Auto SL on all positions" },
                                    { label: "Default Take Profit", value: "80 pips", desc: "Risk/Reward target: 1:2" },
                                    { label: "Trailing Stop", value: "Disabled", desc: "Enable once profitable >20 pips" },
                                    { label: "Trading Hours", value: "08:00-22:00 UTC", desc: "No trades outside session" },
                                ].map((rule) => (
                                    <div key={rule.label} className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                        <div>
                                            <div className="text-sm font-medium">{rule.label}</div>
                                            <div className="text-xs text-muted-foreground">{rule.desc}</div>
                                        </div>
                                        <span className="text-sm font-mono font-medium">{rule.value}</span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    );
}


