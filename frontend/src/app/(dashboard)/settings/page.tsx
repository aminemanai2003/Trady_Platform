"use client";

import { useEffect, useState } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RBButton, RBContent, RBHeader, RBInput, RBLabel } from "@/components/reactbits";
import FaceEnrollModal from "@/components/FaceEnrollModal";
import {
    Camera,
    Key,
    Lock,
    Bot,
    Bell,
    Shield,
    CheckCircle2,
    AlertTriangle,
    Loader2,
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
    const [twoFaEnabled,    setTwoFaEnabled]    = useState(false);
    const [twoFaMethod,     setTwoFaMethod]     = useState<"email" | "sms" | "face">("email");
    const [phoneNumber,     setPhoneNumber]     = useState("");
    const [showEnrollModal, setShowEnrollModal] = useState(false);
    const [saving,          setSaving]          = useState(false);
    const [saved,           setSaved]           = useState(false);
    const [saveError,       setSaveError]       = useState("");

    useEffect(() => {
        let active = true;

        async function load2FA() {
            try {
                const res = await fetch("/api/django-auth/2fa-setup", { cache: "no-store" });
                const data = await res.json().catch(() => ({}));

                if (!active) {
                    return;
                }

                if (!res.ok) {
                    setSaveError(data.message ?? "Unable to load current 2FA settings. Please sign in again if this persists.");
                    return;
                }

                setSaveError("");
                setTwoFaEnabled(Boolean(data.twofa_enabled));

                if (data.preferred_method === "email" || data.preferred_method === "sms" || data.preferred_method === "face") {
                    setTwoFaMethod(data.preferred_method);
                }

                setPhoneNumber(data.phone_number ?? "");
            } catch {
                if (active) {
                    setSaveError("Unable to load current 2FA settings. Please try again shortly.");
                }
            }
        }

        void load2FA();

        return () => {
            active = false;
        };
    }, []);

    async function save2FA() {
        if (twoFaEnabled && twoFaMethod === "sms" && !phoneNumber.trim()) {
            setSaveError("Phone number is required for SMS 2FA.");
            return;
        }

        setSaving(true);
        setSaved(false);
        setSaveError("");
        try {
            const res = await fetch("/api/django-auth/2fa-setup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    enabled: twoFaEnabled,
                    preferred_method: twoFaMethod,
                    phone_number: twoFaMethod === "sms" ? phoneNumber : "",
                }),
            });

            const data = await res.json().catch(() => ({}));

            if (!res.ok || !data.success) {
                setSaveError(data.message ?? "Unable to save security settings.");
                return;
            }

            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
            setSaveError("");
        } catch {
            setSaveError("Network error. Security settings were not saved.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="flex flex-col h-full">
            <RBHeader title="Settings" subtitle="Configuration and safety controls" />

            <RBContent className="space-y-6">
                <Tabs defaultValue="api" className="space-y-4">
                    <TabsList className="bg-muted/50">
                        <TabsTrigger value="api">API Keys</TabsTrigger>
                        <TabsTrigger value="agents">Agent Config</TabsTrigger>
                        <TabsTrigger value="notifications">Notifications</TabsTrigger>
                        <TabsTrigger value="risk">Risk Management</TabsTrigger>
                        <TabsTrigger value="security">Security</TabsTrigger>
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

                    {/* Security Tab */}
                    <TabsContent value="security" className="space-y-4">
                        {/* 2FA Card */}
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Lock className="size-4" /> Two-Factor Authentication
                                </CardTitle>
                                <CardDescription>Add an extra layer of security at login</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-5">
                                {/* Enable toggle */}
                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                    <div>
                                        <div className="text-sm font-medium">Enable 2FA</div>
                                        <div className="text-xs text-muted-foreground">Require a second factor every time you sign in</div>
                                    </div>
                                    <button
                                        onClick={() => setTwoFaEnabled(v => !v)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${twoFaEnabled ? "bg-sky-600" : "bg-slate-700"}`}
                                    >
                                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${twoFaEnabled ? "translate-x-6" : "translate-x-1"}`} />
                                    </button>
                                </div>

                                {/* Method selection */}
                                {twoFaEnabled && (
                                    <div className="space-y-3">
                                        <RBLabel className="text-xs text-muted-foreground uppercase tracking-wider">Method</RBLabel>
                                        <div className="grid grid-cols-3 gap-3">
                                            {(["email", "sms", "face"] as const).map((m) => (
                                                <button
                                                    key={m}
                                                    onClick={() => setTwoFaMethod(m)}
                                                    className={`p-3 rounded-lg border text-sm font-medium transition-colors ${twoFaMethod === m ? "border-sky-500 bg-sky-500/10 text-sky-400" : "border-border/40 bg-muted/20 text-muted-foreground hover:border-border/70"}`}
                                                >
                                                    {m === "email" ? "📧 Email OTP" : m === "sms" ? "📱 SMS OTP" : "🪪 Face ID"}
                                                </button>
                                            ))}
                                        </div>

                                        {/* Phone number input for SMS */}
                                        {twoFaMethod === "sms" && (
                                            <div className="space-y-1.5">
                                                <RBLabel htmlFor="phone" className="text-xs text-muted-foreground">Phone Number</RBLabel>
                                                <RBInput
                                                    id="phone"
                                                    type="tel"
                                                    placeholder="+1 555 000 0000"
                                                    value={phoneNumber}
                                                    onChange={e => setPhoneNumber(e.target.value)}
                                                />
                                            </div>
                                        )}
                                    </div>
                                )}

                                {saveError && (
                                    <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-400">
                                        {saveError}
                                    </div>
                                )}

                                <RBButton onClick={save2FA} disabled={saving} size="sm" className="gap-2">
                                    {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Shield className="size-3.5" />}
                                    {saved ? "Saved!" : saving ? "Saving…" : "Save Settings"}
                                </RBButton>
                            </CardContent>
                        </Card>

                        {/* Face Enrollment Card */}
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Camera className="size-4" /> Face Recognition
                                </CardTitle>
                                <CardDescription>Register your face for biometric login</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-border/30">
                                    <Shield className="size-5 text-sky-400 shrink-0" />
                                    <p className="text-xs text-muted-foreground">
                                        Your face data is encrypted with AES-256 and stored securely. Liveness detection prevents photo spoofing.
                                    </p>
                                </div>
                                <RBButton variant="secondary" size="sm" onClick={() => setShowEnrollModal(true)} className="gap-2">
                                    <Camera className="size-3.5" /> Enroll Face
                                </RBButton>
                            </CardContent>
                        </Card>
                    </TabsContent>

                </Tabs>
            </RBContent>

            {/* Face enroll modal */}
            {showEnrollModal && (
                <FaceEnrollModal
                    onClose={() => setShowEnrollModal(false)}
                    onEnrolled={() => {
                        setShowEnrollModal(false);
                        setTwoFaEnabled(true);
                        setTwoFaMethod("face");
                    }}
                />
            )}
        </div>
    );
}


