"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { FileText, Download, TrendingUp, TrendingDown, Minus, Filter } from "lucide-react";
import { AuroraBackground, FadeInUp, StaggerContainer, StaggerItem, AnimatedCounter, AnimatedProgressBar, FloatingCard } from "@/components/animations";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const PAIRS = ["Tous","EUR/USD","USD/JPY","GBP/USD","USD/CHF"];

const signalHistory = [
    { id:"SIG-0247", time:"2025-01-15 09:42", pair:"EUR/USD", direction:"BUY",  confidence:78.4, entry:1.0831, sl:1.0801, tp:1.0871, outcome:"WIN",  pnl:+320, reason:"Momentum haussier + divergence RSI + CPI US bas" },
    { id:"SIG-0246", time:"2025-01-15 07:18", pair:"GBP/USD", direction:"BUY",  confidence:82.1, entry:1.2641, sl:1.2601, tp:1.2721, outcome:"WIN",  pnl:+480, reason:"Breakout LH précédent + BoE hawkish + sentiment positif" },
    { id:"SIG-0245", time:"2025-01-14 14:55", pair:"USD/JPY", direction:"SELL", confidence:66.3, entry:157.82, sl:158.20, tp:157.06, outcome:"LOSS", pnl:-240, reason:"Divergence baissière MACD · BoJ intervention possible" },
    { id:"SIG-0244", time:"2025-01-14 11:02", pair:"USD/CHF", direction:"SELL", confidence:71.8, entry:0.9072, sl:0.9100, tp:0.9016, outcome:"WIN",  pnl:+180, reason:"SNB faible inflation · USD weak sentiment · Bearish macro" },
    { id:"SIG-0243", time:"2025-01-14 08:30", pair:"EUR/USD", direction:"SELL", confidence:59.2, entry:1.0818, sl:1.0848, tp:1.0778, outcome:"WIN",  pnl:+160, reason:"Résistance 1.0850 + PMI zone euro inférieur aux attentes" },
    { id:"SIG-0242", time:"2025-01-13 15:44", pair:"GBP/USD", direction:"BUY",  confidence:74.5, entry:1.2589, sl:1.2555, tp:1.2657, outcome:"LOSS", pnl:-200, reason:"Breakout partiel · volume insuffisant · news surprise CPI" },
    { id:"SIG-0241", time:"2025-01-13 09:10", pair:"USD/JPY", direction:"BUY",  confidence:69.0, entry:157.12, sl:156.74, tp:157.88, outcome:"WIN",  pnl:+290, reason:"Support 157.00 + Fed hawkish + dollar index fort" },
];

const perfCurve = Array.from({length:30}, (_,i) => {
    const d = new Date("2024-12-16"); d.setDate(d.getDate()+i);
    return {
        date: d.toLocaleDateString("fr-FR",{month:"short",day:"numeric"}),
        pnl: Math.round(1200 + Math.sin(i/6)*400 + i*38 + (Math.random()-0.4)*120),
    };
});

export default function ReportsPage() {
    const [filter, setFilter] = useState("Tous");
    const filtered = filter==="Tous" ? signalHistory : signalHistory.filter(s=>s.pair===filter);

    const wins  = filtered.filter(s=>s.outcome==="WIN").length;
    const wr    = filtered.length ? Math.round(wins/filtered.length*100) : 0;
    const totalPnl = filtered.reduce((acc,s)=>acc+s.pnl,0);

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <FileText className="size-4 text-indigo-400" />
                <h1 className="text-sm font-bold text-white">Rapports Analytiques</h1>
                <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DSO5.1</span>
                <div className="ml-auto flex items-center gap-2">
                    <Filter className="size-3.5 text-slate-500"/>
                    <div className="flex gap-1">
                        {PAIRS.map(p => (
                            <button key={p} onClick={()=>setFilter(p)}
                                className={`px-2 py-1 rounded text-[10px] font-medium transition-all ${filter===p?"bg-indigo-600 text-white":"text-slate-500 hover:text-white border border-white/5 hover:border-white/10"}`}>
                                {p}
                            </button>
                        ))}
                    </div>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/10 text-xs text-slate-300 hover:bg-white/[0.08] transition-all">
                        <Download className="size-3.5"/> Exporter PDF
                    </button>
                </div>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">
                {/* KPIs */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                            { l:"P&L Total",    v:totalPnl, s:"$", c:"text-emerald-400", pos:true },
                            { l:"Win Rate",     v:wr,       s:"%", c:"text-blue-400",    pos:true },
                            { l:"Signaux",      v:filtered.length, s:"", c:"text-violet-400", pos:true },
                            { l:"Convergences", v:Math.round(wr*0.75), s:"", c:"text-amber-400", pos:true },
                        ].map((k,i) => (
                            <motion.div key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                className="p-4 rounded-xl border border-white/5 bg-white/[0.03] text-center">
                                <div className={`text-xl font-bold ${k.c}`}>
                                    {k.s==="$" && k.pos && "+"}<AnimatedCounter to={Math.abs(totalPnl)} suffix={k.s==="$"?"$":""} decimals={0}/>
                                    {k.s!=="$" && k.s}
                                </div>
                                <div className="text-[10px] text-slate-400 mt-0.5">{k.l}</div>
                            </motion.div>
                        ))}
                    </div>
                </FadeInUp>

                {/* P&L Curve */}
                <FloatingCard delay={0.1}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <h3 className="text-sm font-bold text-white mb-1">Courbe P&L — 30 jours glissants (DSO5.1)</h3>
                        <p className="text-[11px] text-slate-500 mb-4">Rapport analytique structuré · Performance cumulée · Historique des signaux avec raisonnement agents</p>
                        <ResponsiveContainer width="100%" height={200}>
                            <AreaChart data={perfCurve}>
                                <defs>
                                    <linearGradient id="pnl" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                <XAxis dataKey="date" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={4}/>
                                <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}`}/>
                                <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                <Area type="monotone" dataKey="pnl" stroke="#6366f1" strokeWidth={2} fill="url(#pnl)" name="P&L Cumulé ($)"/>
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </FloatingCard>

                {/* Signal History Table */}
                <FloatingCard delay={0.15}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <h3 className="text-sm font-bold text-white mb-4">Historique des Signaux avec Raisonnements (DSO5.1)</h3>
                        <div className="space-y-3">
                            <StaggerContainer>
                                {filtered.map((s, i) => (
                                    <StaggerItem key={s.id}>
                                        <div className="p-4 rounded-xl bg-white/[0.04] border border-white/5 hover:border-white/10 transition-colors">
                                            <div className="flex items-start gap-4">
                                                <div className="shrink-0 text-center">
                                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${s.direction==="BUY"?"bg-emerald-500/15 border border-emerald-500/30":"bg-rose-500/15 border border-rose-500/30"}`}>
                                                        {s.direction==="BUY"
                                                            ? <TrendingUp className="size-5 text-emerald-400"/>
                                                            : <TrendingDown className="size-5 text-rose-400"/>}
                                                    </div>
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 flex-wrap">
                                                        <span className="text-xs font-mono text-slate-500">{s.id}</span>
                                                        <span className="font-bold text-white">{s.pair}</span>
                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${s.direction==="BUY"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":"bg-rose-500/15 text-rose-400 border-rose-500/30"}`}>{s.direction}</span>
                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${s.outcome==="WIN"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":"bg-rose-500/15 text-rose-400 border-rose-500/30"}`}>{s.outcome}</span>
                                                        <span className="text-[10px] text-slate-500 ml-auto">{s.time}</span>
                                                    </div>
                                                    <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{s.reason}</p>
                                                    <div className="flex items-center gap-4 mt-2 text-[10px]">
                                                        <span className="text-slate-500">Confiance: <span className="text-blue-400 font-bold">{s.confidence}%</span></span>
                                                        <span className="text-slate-500">Entrée: <span className="text-slate-300">{s.entry}</span></span>
                                                        <span className="text-slate-500">SL: <span className="text-rose-400">{s.sl}</span></span>
                                                        <span className="text-slate-500">TP: <span className="text-emerald-400">{s.tp}</span></span>
                                                        <span className={`ml-auto font-bold ${s.pnl>0?"text-emerald-400":"text-rose-400"}`}>{s.pnl>0?"+":""}{s.pnl}$</span>
                                                    </div>
                                                    <AnimatedProgressBar value={s.confidence} color="blue" height={2} className="mt-2"/>
                                                </div>
                                            </div>
                                        </div>
                                    </StaggerItem>
                                ))}
                            </StaggerContainer>
                        </div>
                    </div>
                </FloatingCard>
            </div>
        </div>
    );
}
