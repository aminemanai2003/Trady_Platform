"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Download, TrendingUp, TrendingDown, Filter } from "lucide-react";
import { FadeInUp, StaggerContainer, StaggerItem, AnimatedCounter, AnimatedProgressBar, FloatingCard } from "@/components/animations";
import { RBContent, RBHeader } from "@/components/reactbits";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import type { ReportSummaryResponse } from "@/types";

const PAIRS = ["All","EUR/USD","USD/JPY","GBP/USD","USD/CHF"];

export default function ReportsPage() {
    const [filter, setFilter] = useState("All");
    const [report, setReport] = useState<ReportSummaryResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const data = await api.reportsSummary(filter, 90);
                setReport(data);
            } catch (err) {
                console.error("Failed to load reports summary", err);
                setReport(null);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [filter]);

    const totalPnl = report?.kpis.total_pnl ?? 0;
    const wr = report?.kpis.win_rate ?? 0;
    const signals = report?.kpis.signals ?? 0;
    const confluence = report?.kpis.confluence ?? 0;
    const sharpe = report?.kpis.sharpe ?? 0;
    const history = report?.history ?? [];
    const perfCurve = report?.curve ?? [];

    return (
        <div className="flex flex-col h-full bg-slate-950 text-slate-100">
            <RBHeader
                title="Analytics Reports"
                subtitle="DSO5.1"
                right={
                    <>
                        <Filter className="size-3.5 text-slate-500"/>
                        <div className="flex gap-1">
                            {PAIRS.map(p => (
                                <button key={p} onClick={()=>setFilter(p)}
                                    className={`px-2 py-1 rounded text-[10px] font-medium transition-all ${filter===p?"bg-indigo-600 text-white":"text-slate-500 hover:text-white border border-white/5 hover:border-white/10"}`}>
                                    {p}
                                </button>
                            ))}
                        </div>
                        <a
                            href={api.reportsExportUrl(filter, 90)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/10 text-xs text-slate-300 hover:bg-white/[0.08] transition-all"
                        >
                            <Download className="size-3.5"/> Export CSV
                        </a>
                    </>
                }
            />

            <RBContent className="space-y-6">
                {/* KPIs */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                            { l:"P&L Total",    v:totalPnl, s:"$", c:"text-emerald-400", pos:true },
                            { l:"Win Rate",     v:wr,       s:"%", c:"text-blue-400",    pos:true },
                            { l:"Signals",      v:signals, s:"", c:"text-violet-400", pos:true },
                            { l:"Sharpe", v:sharpe, s:"", c:"text-amber-400", pos:true },
                        ].map((k,i) => (
                            <motion.div key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                className="p-4 rounded-xl border border-white/5 bg-white/[0.03] text-center">
                                <div className={`text-xl font-bold ${k.c}`}>
                                    {k.s==="$" && k.pos && totalPnl >= 0 && "+"}<AnimatedCounter to={Math.abs(k.v)} suffix={k.s==="$"?"$":""} decimals={k.l==="Sharpe"?2:0}/>
                                    {k.s!=="$" && k.s}
                                </div>
                                <div className="text-[10px] text-slate-400 mt-0.5">{k.l}</div>
                            </motion.div>
                        ))}
                    </div>
                </FadeInUp>

                {!loading && (
                    <div className="text-[11px] text-slate-500">Confluence score: {confluence.toFixed(1)}</div>
                )}

                {/* P&L Curve */}
                <FloatingCard delay={0.1}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <h3 className="text-sm font-bold text-white mb-1">P&L Curve - Rolling 30 Days (DSO5.1)</h3>
                        <p className="text-[11px] text-slate-500 mb-4">Dynamic analytics report - real performance curve from backend</p>
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
                                <Area type="monotone" dataKey="cumulative_pnl" stroke="#6366f1" strokeWidth={2} fill="url(#pnl)" name="Cumulative P&L ($)"/>
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </FloatingCard>

                {/* Signal History Table */}
                <FloatingCard delay={0.15}>
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                        <h3 className="text-sm font-bold text-white mb-4">Signal History with Rationales (DSO5.1)</h3>
                        <div className="space-y-3">
                            <StaggerContainer>
                                {history.map((s) => (
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
                                                        <span className="text-xs font-mono text-slate-500">LOG-{s.id}</span>
                                                        <span className="font-bold text-white">{s.pair}</span>
                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${s.direction==="BUY"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":"bg-rose-500/15 text-rose-400 border-rose-500/30"}`}>{s.direction}</span>
                                                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${s.outcome==="WIN"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":"bg-rose-500/15 text-rose-400 border-rose-500/30"}`}>{s.outcome}</span>
                                                        <span className="text-[10px] text-slate-500 ml-auto">{new Date(s.time).toLocaleString()}</span>
                                                    </div>
                                                    <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{s.agent_name} outcome log</p>
                                                    <div className="flex items-center gap-4 mt-2 text-[10px]">
                                                        <span className="text-slate-500">Confidence: <span className="text-blue-400 font-bold">{s.confidence}%</span></span>
                                                        <span className={`ml-auto font-bold ${s.pnl>0?"text-emerald-400":"text-rose-400"}`}>{s.pnl>0?"+":""}{s.pnl}$</span>
                                                    </div>
                                                    <AnimatedProgressBar value={s.confidence} color="blue" height={2} className="mt-2"/>
                                                </div>
                                            </div>
                                        </div>
                                    </StaggerItem>
                                ))}
                            </StaggerContainer>
                            {!loading && history.length === 0 && (
                                <div className="text-xs text-slate-500">No report rows found for the selected filter.</div>
                            )}
                        </div>
                    </div>
                </FloatingCard>
            </RBContent>
        </div>
    );
}


