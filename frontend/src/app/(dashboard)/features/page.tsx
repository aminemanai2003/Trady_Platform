"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
         BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { Cpu, TrendingUp, Globe2, MessageSquare, Clock, CheckCircle2 } from "lucide-react";
import { AuroraBackground, FadeInUp, StaggerContainer, StaggerItem, AnimatedProgressBar, ShimmerCard, FloatingCard } from "@/components/animations";

const CATEGORIES = [
    {
        id: "technical", label: "Technical Indicators", icon: TrendingUp, color: "violet",
        count: 60, dso: "DSO1.2",
        features: [
            { name:"SMA 20/50/200",  imp:82, desc:"Simple moving averages across multiple periods" },
            { name:"EMA 12/26/50",   imp:78, desc:"Exponential moving averages" },
            { name:"RSI 14",         imp:91, desc:"Relative Strength Index - momentum" },
            { name:"MACD Signal",    imp:88, desc:"MA convergence/divergence - trend" },
            { name:"Bollinger Bands",imp:75, desc:"Bollinger Bands - volatility" },
            { name:"ATR 14",         imp:84, desc:"Average True Range - absolute volatility" },
            { name:"Stochastic K/D", imp:69, desc:"Stochastic oscillator - overbought/oversold zones" },
            { name:"Williams %R",    imp:65, desc:"Momentum oscillator similar to stochastic" },
        ]
    },
    {
        id: "fundamental", label: "Fundamental Indicators", icon: Globe2, color: "blue",
        count: 20, dso: "DSO1.1",
        features: [
            { name:"CPI (Inflation)",    imp:93, desc:"Consumer Price Index - FRED" },
            { name:"GDP Growth Rate",    imp:89, desc:"Quarterly GDP growth rate" },
            { name:"PMI Manufacturing",  imp:85, desc:"Purchasing Managers Index - activity" },
            { name:"Interest Rate Diff", imp:96, desc:"Central bank policy rate differential" },
            { name:"Trade Balance",      imp:74, desc:"Trade balance - capital flows" },
            { name:"Unemployment Rate",  imp:81, desc:"Unemployment rate - NFP labor signal" },
        ]
    },
    {
        id: "sentiment", label: "Sentiment Indicators", icon: MessageSquare, color: "emerald",
        count: 15, dso: "DSO1.3",
        features: [
            { name:"FinBERT Score",    imp:88, desc:"NLP - positive/negative/neutral classification" },
            { name:"News Velocity",    imp:72, desc:"FX news publication frequency" },
            { name:"Sentiment Trend",  imp:79, desc:"5-day sentiment score evolution" },
            { name:"Event Proximity",  imp:83, desc:"Proximity to major events (NFP, CPI)" },
            { name:"Volume Anomalies", imp:67, desc:"FX volume anomaly detection" },
        ]
    },
    {
        id: "temporal", label: "Temporal Features", icon: Clock, color: "amber",
        count: 25, dso: "DSO1.2",
        features: [
            { name:"Session Encoding",   imp:77, desc:"London/New York/Tokyo/Sydney - one-hot" },
            { name:"Hour of Day",        imp:71, desc:"Encoded hour (sin/cos) - cyclic features" },
            { name:"Day of Week",        imp:66, desc:"Cyclical weekday feature" },
            { name:"Event Countdown",    imp:89, desc:"Days until next macro event" },
            { name:"Market Regime",      imp:92, desc:"Bull/Bear/Sideways - HMM detection" },
        ]
    },
];

const radarData = [
    { subject:"Technical",   A:82, fullMark:100 },
    { subject:"Fundamental", A:88, fullMark:100 },
    { subject:"Sentiment",   A:74, fullMark:100 },
    { subject:"Temporal",    A:79, fullMark:100 },
    { subject:"Correlation", A:71, fullMark:100 },
];

const importanceTop10 = [
    { name:"Policy Rate Diff",    value:96 },
    { name:"Market Regime HMM",   value:92 },
    { name:"RSI Momentum",        value:91 },
    { name:"Event Countdown",     value:89 },
    { name:"GDP Growth",          value:89 },
    { name:"FinBERT Score",       value:88 },
    { name:"MACD Signal",         value:88 },
    { name:"CPI Inflation",       value:93 },
    { name:"ATR Volatility",      value:84 },
    { name:"Event Proximity",     value:83 },
].sort((a,b)=>b.value-a.value);

const colorMap: Record<string,string> = {
    violet:"#8b5cf6", blue:"#3b82f6", emerald:"#10b981", amber:"#f59e0b"
};

export default function FeaturesPage() {
    const [active, setActive] = useState("technical");
    const cat = CATEGORIES.find(c => c.id === active)!;

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <Cpu className="size-4 text-violet-400" />
                <h1 className="text-sm font-bold text-white">Feature Lab - Feature Engineering</h1>
                <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DSO1.2</span>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">
                {/* Stats row */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {CATEGORIES.map((c, i) => {
                            const Icon = c.icon;
                            return (
                                <motion.button key={c.id} onClick={() => setActive(c.id)}
                                    initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                    className={`p-4 rounded-xl border text-left transition-all ${active===c.id ? `border-${c.color}-500/50 bg-${c.color}-500/10` : "border-white/5 bg-white/[0.03] hover:border-white/10"}`}>
                                    <div className="flex items-center gap-2 mb-2">
                                        <Icon className={`size-4 text-${c.color}-400`}/>
                                        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded bg-${c.color}-500/10 text-${c.color}-400 border border-${c.color}-500/20`}>{c.dso}</span>
                                    </div>
                                    <div className="text-2xl font-bold text-white">{c.count}</div>
                                    <div className="text-[10px] text-slate-500">{c.label}</div>
                                </motion.button>
                            );
                        })}
                    </div>
                </FadeInUp>

                {/* Total */}
                <FadeInUp delay={0.05}>
                    <div className="p-4 rounded-xl border border-violet-500/20 bg-violet-500/5 flex items-center gap-4">
                        <CheckCircle2 className="size-6 text-violet-400 shrink-0"/>
                        <div>
                            <span className="text-white font-bold">120 features in total</span>
                            <span className="text-slate-500 text-sm ml-2">- 60 technical - 20 fundamental - 15 sentiment - 25 temporal - random forest selection</span>
                        </div>
                    </div>
                </FadeInUp>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Feature list */}
                    <div className="lg:col-span-2">
                        <FloatingCard delay={0.1}>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <div className="flex items-center gap-2 mb-4">
                                    {(() => { const Icon = cat.icon; return <Icon className={`size-4 text-${cat.color}-400`}/>; })()}
                                    <h3 className="text-sm font-bold text-white">{cat.label}</h3>
                                    <span className="text-[10px] text-slate-500">{cat.count} features - {cat.dso}</span>
                                </div>
                                <StaggerContainer>
                                    {cat.features.map((f, i) => (
                                        <StaggerItem key={i}>
                                            <div className="p-3 rounded-lg bg-white/[0.04] border border-white/5 mb-2 hover:border-white/10 transition-colors">
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <span className="text-sm font-semibold text-white">{f.name}</span>
                                                    <span className={`text-xs font-bold text-${cat.color}-400`}>{f.imp}/100</span>
                                                </div>
                                                <p className="text-[11px] text-slate-500 mb-1.5">{f.desc}</p>
                                                <AnimatedProgressBar value={f.imp} color={cat.color as any} height={3}/>
                                            </div>
                                        </StaggerItem>
                                    ))}
                                </StaggerContainer>
                            </div>
                        </FloatingCard>
                    </div>

                    {/* Right column */}
                    <div className="space-y-4">
                        {/* Radar */}
                        <FloatingCard delay={0.15}>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
                                <h3 className="text-xs font-bold text-white mb-3">Coverage by Dimension</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <RadarChart data={radarData}>
                                        <PolarGrid stroke="rgba(255,255,255,0.1)"/>
                                        <PolarAngleAxis dataKey="subject" tick={{fontSize:10,fill:"#475569"}}/>
                                        <Radar dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.25} strokeWidth={1.5}/>
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                        </FloatingCard>

                        {/* Top 10 importance */}
                        <FloatingCard delay={0.2}>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
                                <h3 className="text-xs font-bold text-white mb-3">Top 10 - Random Forest Importance</h3>
                                <div className="space-y-2">
                                    {importanceTop10.slice(0,6).map((f,i) => (
                                        <div key={i} className="flex items-center gap-2">
                                            <span className="text-[9px] text-slate-500 w-3">{i+1}</span>
                                            <span className="text-[10px] text-slate-300 flex-1 truncate">{f.name}</span>
                                            <span className="text-[10px] text-violet-400 font-bold w-6 text-right">{f.value}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </FloatingCard>
                    </div>
                </div>
            </div>
        </div>
    );
}


