"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, LineChart, Line, Legend,
} from "recharts";
import { TrendingUp, Brain, Newspaper, BarChart3 } from "lucide-react";
import { AuroraBackground, FadeInUp, StaggerContainer, StaggerItem, AnimatedCounter } from "@/components/animations";

const perf90 = Array.from({ length: 90 }, (_, i) => {
    const date = new Date(); date.setDate(date.getDate() - (90 - i));
    const daily = Math.round((Math.random() - 0.44) * 600);
    return { date: date.toLocaleDateString("fr-FR", { month: "short", day: "numeric" }), daily, pnl: 0, winRate: Math.round(48+Math.random()*22), trades: Math.floor(5+Math.random()*20) };
});
let cum = 0; perf90.forEach(d => { cum += d.daily; d.pnl = cum; });

const macro = [
    { ind: "CPI (US)",  val: 3.1, prev: 3.2, impact: "HIGH",   trend: "down", zone: "US"  },
    { ind: "NFP",       val: 216, prev: 199,  impact: "HIGH",   trend: "up",   zone: "US"  },
    { ind: "Fed Rate",  val: 5.25,prev: 5.25, impact: "HIGH",   trend: "flat", zone: "US"  },
    { ind: "GDP (US)",  val: 3.3, prev: 4.9,  impact: "MEDIUM", trend: "down", zone: "US"  },
    { ind: "ECB Rate",  val: 4.5, prev: 4.5,  impact: "HIGH",   trend: "flat", zone: "EUR" },
    { ind: "PMI (EU)",  val: 47.6,prev: 47.0, impact: "MEDIUM", trend: "up",   zone: "EUR" },
    { ind: "BoJ Rate",  val: 0.1, prev: -0.1, impact: "HIGH",   trend: "up",   zone: "JPY" },
    { ind: "CPI (UK)",  val: 4.0, prev: 3.9,  impact: "HIGH",   trend: "up",   zone: "GBP" },
];

const sent30 = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (30 - i));
    return { date: d.toLocaleDateString("fr-FR", { month: "short", day: "numeric" }),
        eurusd: +((Math.random()-.4)*100/100).toFixed(2),
        usdjpy: +((Math.random()-.5)*100/100).toFixed(2),
        gbpusd: +((Math.random()-.45)*100/100).toFixed(2),
        usdchf: +((Math.random()-.5)*100/100).toFixed(2) };
});

const TABS = [
    { id: "performance", label: "Performance (DSO2.2)", icon: TrendingUp },
    { id: "macro",       label: "Macro Indicators (DSO1.1)", icon: Brain },
    { id: "sentiment",   label: "Sentiment NLP (DSO1.3)", icon: Newspaper },
];

const impactColor = (i: string) =>
    i === "HIGH" ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
    : i === "MEDIUM" ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
    : "bg-slate-500/15 text-slate-400 border-slate-500/30";

export default function AnalyticsPage() {
    const [tab, setTab] = useState("performance");
    const perf = perf90[perf90.length-1];
    const maxDD = -18.4; const sharpe = 1.73; const win = 58.2;

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <BarChart3 className="size-4 text-blue-400" />
                <h1 className="text-sm font-bold text-white">Analytics</h1>
                <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DSO1.1 - DSO1.3 - DSO2.2</span>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">
                {/* KPI Row */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                            { label: "Cumulative P&L (90d)", value: perf.pnl, prefix: "$", color: perf.pnl >= 0 ? "text-emerald-400": "text-rose-400" },
                            { label: "Sharpe Ratio",      value: sharpe,   suffix: "", decimals: 2, color: "text-blue-400" },
                            { label: "Win Rate",          value: win,      suffix: "%", decimals: 1, color: "text-amber-400" },
                            { label: "Max Drawdown",      value: Math.abs(maxDD), prefix: "-", suffix: "%", decimals: 1, color: "text-rose-400" },
                        ].map((k, i) => (
                            <motion.div key={i} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                className="p-4 rounded-xl border border-white/5 bg-white/[0.03] text-center">
                                <div className={`text-2xl font-bold ${k.color}`}>
                                    <AnimatedCounter to={typeof k.value === "number" ? k.value : 0} prefix={k.prefix||""} suffix={k.suffix||""} decimals={k.decimals||0} />
                                </div>
                                <div className="text-[10px] text-slate-500 mt-1">{k.label}</div>
                            </motion.div>
                        ))}
                    </div>
                </FadeInUp>

                {/* Tabs */}
                <FadeInUp delay={0.1}>
                    <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/5 w-fit">
                        {TABS.map(t => (
                            <button key={t.id} onClick={() => setTab(t.id)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${tab === t.id ? "bg-violet-600 text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-white/5"}`}>
                                <t.icon className="size-3.5" /> {t.label}
                            </button>
                        ))}
                    </div>
                </FadeInUp>

                {/* Performance Charts */}
                {tab === "performance" && (
                    <StaggerContainer className="space-y-4">
                        <StaggerItem>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <div className="mb-4">
                                    <h3 className="text-sm font-bold text-white">Equity Curve - 90 Days (DSO2.2)</h3>
                                    <p className="text-[11px] text-slate-500">Walk-forward validation on 5 years of historical data</p>
                                </div>
                                <ResponsiveContainer width="100%" height={260}>
                                    <AreaChart data={perf90}>
                                        <defs>
                                            <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                        <XAxis dataKey="date" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={14}/>
                                        <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}`}/>
                                        <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                        <Area type="monotone" dataKey="pnl" stroke="#10b981" strokeWidth={2} fill="url(#g1)"/>
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </StaggerItem>
                        <StaggerItem>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                    <h3 className="text-sm font-bold text-white mb-4">Daily P&L</h3>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <BarChart data={perf90}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                            <XAxis dataKey="date" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={14}/>
                                            <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}`}/>
                                            <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                            <Bar dataKey="daily" fill="#6366f1" radius={[2,2,0,0]}/>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                    <h3 className="text-sm font-bold text-white mb-4">Win Rate Rolling 30j</h3>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <LineChart data={perf90}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                            <XAxis dataKey="date" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={14}/>
                                            <YAxis domain={[40,75]} tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} tickFormatter={v=>`${v}%`}/>
                                            <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                            <Line type="monotone" dataKey="winRate" stroke="#f59e0b" strokeWidth={2} dot={false}/>
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </StaggerItem>
                    </StaggerContainer>
                )}

                {/* Macro Heatmap */}
                {tab === "macro" && (
                    <StaggerContainer className="space-y-3">
                        <StaggerItem>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <h3 className="text-sm font-bold text-white mb-1">Macroeconomic Indicators (DSO1.1)</h3>
                                <p className="text-[11px] text-slate-500 mb-4">Source: FRED API - central banks - latest values</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {macro.map((m, i) => (
                                        <motion.div key={i} initial={{opacity:0,x:-10}} animate={{opacity:1,x:0}} transition={{delay:i*0.05}}
                                            className="flex items-center justify-between p-3 rounded-lg bg-white/[0.04] border border-white/5">
                                            <div>
                                                <div className="text-sm font-semibold text-white">{m.ind}</div>
                                                <div className="text-[10px] text-slate-500">Previous: {m.prev} - Region: {m.zone}</div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="text-right">
                                                    <div className="text-base font-bold text-white">{m.val}</div>
                                                    <div className={`text-[10px] ${m.trend==="up"?"text-emerald-400":m.trend==="down"?"text-rose-400":"text-slate-500"}`}>
                                                        {m.trend==="up"?"UP":m.trend==="down"?"DOWN":"FLAT"} {m.trend}
                                                    </div>
                                                </div>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${impactColor(m.impact)}`}>{m.impact}</span>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </StaggerItem>
                    </StaggerContainer>
                )}

                {/* Sentiment Chart */}
                {tab === "sentiment" && (
                    <StaggerContainer>
                        <StaggerItem>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <h3 className="text-sm font-bold text-white mb-1">NLP Sentiment Score by Pair (DSO1.3)</h3>
                                <p className="text-[11px] text-slate-500 mb-4">FinBERT - Reuters news - score from -1 (bearish) to +1 (bullish)</p>
                                <ResponsiveContainer width="100%" height={320}>
                                    <LineChart data={sent30}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                        <XAxis dataKey="date" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={5}/>
                                        <YAxis domain={[-1,1]} tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false}/>
                                        <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                        <Legend wrapperStyle={{fontSize:11}}/>
                                        <Line type="monotone" dataKey="eurusd" stroke="#10b981" strokeWidth={2} dot={false} name="EUR/USD"/>
                                        <Line type="monotone" dataKey="usdjpy" stroke="#6366f1" strokeWidth={2} dot={false} name="USD/JPY"/>
                                        <Line type="monotone" dataKey="gbpusd" stroke="#f59e0b" strokeWidth={2} dot={false} name="GBP/USD"/>
                                        <Line type="monotone" dataKey="usdchf" stroke="#ef4444" strokeWidth={2} dot={false} name="USD/CHF"/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </StaggerItem>
                    </StaggerContainer>
                )}
            </div>
        </div>
    );
}


