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
} from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { useAccessibility, type FontScale, type ContrastMode, type ColorBlindMode, type CursorSize, type LineSpacing } from "@/components/accessibility-provider";
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
    const { fontScale, contrast, reducedMotion, dyslexicFont, setFontScale, setContrast, setReducedMotion, setDyslexicFont, resetAccessibility, textToSpeech, colorBlindMode, cursorSize, highlightLinks, lineSpacing, isSpeaking, setTextToSpeech, setColorBlindMode, setCursorSize, setHighlightLinks, setLineSpacing, speak, stopSpeech } = useAccessibility();

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
                        <TabsTrigger value="api" data-testid="settings-tab-api">API Keys</TabsTrigger>
                        <TabsTrigger value="agents" data-testid="settings-tab-agents">Agent Config</TabsTrigger>
                        <TabsTrigger value="notifications" data-testid="settings-tab-notifications">Notifications</TabsTrigger>
                        <TabsTrigger value="risk" data-testid="settings-tab-risk">Risk Management</TabsTrigger>
                        <TabsTrigger value="security" data-testid="settings-tab-security">Security</TabsTrigger>
                        <TabsTrigger value="accessibility" data-testid="settings-tab-accessibility">Accessibility</TabsTrigger>
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
                                        <div className={`w-10 h-5 rounded-full flex items-center px-0.5 cursor-pointer transition-colors ${n.enabled ? "bg-brand-green-600 justify-end" : "bg-muted justify-start"}`}>
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
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 ${twoFaEnabled ? "bg-brand-blue-600" : "bg-slate-700"}`}
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
                                                    className={`p-3 rounded-lg border text-sm font-medium transition-colors ${twoFaMethod === m ? "border-brand-blue-500/70 bg-brand-blue-500/10 text-brand-blue-400" : "border-border/40 bg-muted/20 text-muted-foreground hover:border-border/70"}`}
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
                                    <Alert variant="error" onClose={() => setSaveError("")}>
                                        {saveError}
                                    </Alert>
                                )}

                                <RBButton onClick={save2FA} disabled={saving} size="sm" className="gap-2" data-testid="settings-save-btn">
                                    {saving ? <Spinner size="xs" aria-label="Saving…" /> : <Shield className="size-3.5" />}
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
                                    <Shield className="size-5 text-brand-blue-400 shrink-0" />
                                    <p className="text-xs text-muted-foreground">
                                        Your face data is encrypted with AES-256 and stored securely. Liveness detection prevents photo spoofing.
                                    </p>
                                </div>
                                <RBButton variant="secondary" size="sm" onClick={() => setShowEnrollModal(true)} className="gap-2" data-testid="settings-enroll-face-btn">
                                    <Camera className="size-3.5" /> Enroll Face
                                </RBButton>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Accessibility Tab */}
                    <TabsContent value="accessibility" className="space-y-4">

                        {/* Vision */}
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Shield className="size-4" /> Vision
                                </CardTitle>
                                <CardDescription>Font, contrast and color-vision adjustments</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <RBLabel className="text-xs text-muted-foreground">Font size</RBLabel>
                                        <select
                                            className="w-full rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-sm"
                                            value={String(fontScale)}
                                            onChange={(e) => setFontScale(Number(e.target.value) as FontScale)}
                                        >
                                            <option value="1">Default (100%)</option>
                                            <option value="1.1">Large (110%)</option>
                                            <option value="1.2">Extra large (120%)</option>
                                            <option value="1.3">Huge (130%)</option>
                                        </select>
                                        <p className="text-xs text-muted-foreground">Scales the base UI text size across the app.</p>
                                    </div>

                                    <div className="space-y-2">
                                        <RBLabel className="text-xs text-muted-foreground">Contrast</RBLabel>
                                        <select
                                            className="w-full rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-sm"
                                            value={contrast}
                                            onChange={(e) => setContrast(e.target.value as ContrastMode)}
                                        >
                                            <option value="default">Default</option>
                                            <option value="high">High contrast</option>
                                        </select>
                                        <p className="text-xs text-muted-foreground">Boosts legibility by strengthening borders and muted text.</p>
                                    </div>

                                    <div className="space-y-2">
                                        <RBLabel className="text-xs text-muted-foreground">Color vision mode</RBLabel>
                                        <select
                                            className="w-full rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-sm"
                                            value={colorBlindMode}
                                            onChange={(e) => setColorBlindMode(e.target.value as ColorBlindMode)}
                                        >
                                            <option value="none">Normal vision</option>
                                            <option value="deuteranopia">Deuteranopia (green-blind)</option>
                                            <option value="protanopia">Protanopia (red-blind)</option>
                                            <option value="tritanopia">Tritanopia (blue-blind)</option>
                                        </select>
                                        <p className="text-xs text-muted-foreground">Applies a color filter to simulate and compensate for color blindness.</p>
                                    </div>

                                    <div className="space-y-2">
                                        <RBLabel className="text-xs text-muted-foreground">Line spacing</RBLabel>
                                        <select
                                            className="w-full rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-sm"
                                            value={lineSpacing}
                                            onChange={(e) => setLineSpacing(e.target.value as LineSpacing)}
                                        >
                                            <option value="default">Default</option>
                                            <option value="relaxed">Relaxed (1.9×)</option>
                                            <option value="loose">Loose (2.4×)</option>
                                        </select>
                                        <p className="text-xs text-muted-foreground">Increases vertical spacing between lines for easier reading.</p>
                                    </div>
                                </div>

                                {[{
                                    label: "Dyslexia-friendly font",
                                    desc: "Switches to a wider-spaced font that is easier to read for people with dyslexia.",
                                    value: dyslexicFont, onChange: () => setDyslexicFont(!dyslexicFont),
                                }, {
                                    label: "Highlight all links",
                                    desc: "Adds a visible outline and underline to every clickable link on the page.",
                                    value: highlightLinks, onChange: () => setHighlightLinks(!highlightLinks),
                                }].map(({ label, desc, value, onChange }) => (
                                    <div key={label} className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                        <div>
                                            <div className="text-sm font-medium">{label}</div>
                                            <div className="text-xs text-muted-foreground">{desc}</div>
                                        </div>
                                        <button
                                            aria-pressed={value}
                                            onClick={onChange}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 ${value ? "bg-brand-blue-600" : "bg-slate-700"}`}
                                        >
                                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? "translate-x-6" : "translate-x-1"}`} />
                                        </button>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>

                        {/* Motion & Interaction */}
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Shield className="size-4" /> Motion &amp; Interaction
                                </CardTitle>
                                <CardDescription>Cursor size and animation preferences</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-5">
                                <div className="space-y-2">
                                    <RBLabel className="text-xs text-muted-foreground">Cursor size</RBLabel>
                                    <select
                                        className="w-full rounded-md border border-border/40 bg-muted/20 px-3 py-2 text-sm"
                                        value={cursorSize}
                                        onChange={(e) => setCursorSize(e.target.value as CursorSize)}
                                    >
                                        <option value="default">Default</option>
                                        <option value="large">Large</option>
                                        <option value="x-large">Extra large</option>
                                    </select>
                                    <p className="text-xs text-muted-foreground">Increases the mouse cursor size for better visibility.</p>
                                </div>

                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                    <div>
                                        <div className="text-sm font-medium">Reduced motion</div>
                                        <div className="text-xs text-muted-foreground">Disables UI animations and transitions (useful for vestibular disorders / motion sensitivity).</div>
                                    </div>
                                    <button
                                        aria-pressed={reducedMotion}
                                        onClick={() => setReducedMotion(!reducedMotion)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 ${reducedMotion ? "bg-brand-blue-600" : "bg-slate-700"}`}
                                    >
                                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${reducedMotion ? "translate-x-6" : "translate-x-1"}`} />
                                    </button>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Text-to-Speech */}
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader>
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Shield className="size-4" /> Text-to-Speech
                                </CardTitle>
                                <CardDescription>Browser built-in speech synthesis — no plugin required</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center justify-between p-3 rounded-lg bg-muted/20 border border-border/30">
                                    <div>
                                        <div className="text-sm font-medium">Read selected text aloud 🔊</div>
                                        <div className="text-xs text-muted-foreground">Select any text on the page with your mouse and it will be read aloud automatically.</div>
                                    </div>
                                    <button
                                        aria-pressed={textToSpeech}
                                        onClick={() => setTextToSpeech(!textToSpeech)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 ${textToSpeech ? "bg-brand-blue-600" : "bg-slate-700"}`}
                                    >
                                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${textToSpeech ? "translate-x-6" : "translate-x-1"}`} />
                                    </button>
                                </div>

                                <div className="flex items-center gap-3">
                                    <RBButton
                                        variant="secondary" size="sm"
                                        onClick={() => speak("Welcome to Trady. Text to speech is working correctly.")}
                                        className="gap-2"
                                    >
                                        🔊 Test voice
                                    </RBButton>
                                    {isSpeaking && (
                                        <RBButton variant="secondary" size="sm" onClick={stopSpeech} className="gap-2 text-rose-400">
                                            ⏹ Stop
                                        </RBButton>
                                    )}
                                    {isSpeaking && (
                                        <span className="text-xs text-brand-blue-400 animate-pulse">▶ Speaking…</span>
                                    )}
                                </div>

                                <div className="p-3 rounded-lg bg-muted/20 border border-border/30 text-xs text-muted-foreground space-y-1">
                                    <p className="font-medium text-foreground">How to use:</p>
                                    <ul className="list-disc list-inside space-y-0.5">
                                        <li>Enable the toggle above</li>
                                        <li>Select any text on any page with your mouse</li>
                                        <li>The selected text will be read aloud automatically</li>
                                        <li>Or use the sidebar Accessibility panel → “Read page” to read visible content</li>
                                    </ul>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Reset */}
                        <div className="flex items-center gap-3">
                            <RBButton variant="secondary" size="sm" onClick={resetAccessibility}>
                                Reset all accessibility settings
                            </RBButton>
                            <div className="text-xs text-muted-foreground">
                                All preferences are stored locally in your browser — nothing is sent to the server.
                            </div>
                        </div>

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


