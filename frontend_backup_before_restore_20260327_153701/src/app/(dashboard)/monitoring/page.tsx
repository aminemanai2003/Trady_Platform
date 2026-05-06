"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, ReferenceLine,
} from "recharts";
import { ShieldCheck, AlertTriangle, Cpu, Activity, CheckCircle2, XCircle, Clock } from "lucide-react";
import { AuroraBackground, FadeInUp, StaggerContainer, StaggerItem, AnimatedCounter, AnimatedProgressBar, FloatingCard } from "@/components/animations";

// DSO4.1 — Data Validation
const validationChecks = [
    { label:"Valeurs manquantes",     status:"ok",   score:99.2, threshold:95, detail:"0.8% de gaps comblés par interpolation" },
    { label:"Outliers (z-score >4)",  status:"warn", score:97.1, threshold:98, detail:"3 anomalies détectées sur USD/JPY ce jour" },
    { label:"Cohérence temporelle",   status:"ok",   score:100,  threshold:99, detail:"Aucun saut de timestamp détecté" },
    { label:"Qualité OHLC",           status:"ok",   score:98.8, threshold:97, detail:"High ≥ Low vérifié sur toutes les bougies" },
    { label:"Taux de collecte FRED",  status:"ok",   score:100,  threshold:95, detail:"20/20 séries macroéconomiques reçues" },
    { label:"Latence API MT5",        status:"ok",   score:98.5, threshold:95, detail:"Latence moyenne: 42ms (seuil 200ms)" },
];

// DSO4.2 — MLflow / Performance Monitoring
const latency7d = Array.from({length:7}, (_,i) => {
    const d = new Date(); d.setDate(d.getDate()-6+i);
    return {
        day: d.toLocaleDateString("fr-FR",{weekday:"short"}),
        inference: Math.round(38+Math.random()*20),
        pipeline: Math.round(120+Math.random()*60),
    };
});

const signalDrift = Array.from({length:30}, (_,i) => ({
    day: i+1,
    drift: +(0.02+Math.sin(i/7)*0.015+Math.random()*0.01).toFixed(4),
    threshold: 0.05,
}));

const runHistory = [
    { run:"2025-01-15 08:00", wr:57.2, sharpe:1.71, drift:0.023, status:"ok"   },
    { run:"2025-01-14 08:00", wr:56.8, sharpe:1.68, drift:0.028, status:"ok"   },
    { run:"2025-01-13 08:00", wr:55.1, sharpe:1.55, drift:0.041, status:"warn" },
    { run:"2025-01-12 08:00", wr:58.4, sharpe:1.82, drift:0.018, status:"ok"   },
    { run:"2025-01-11 08:00", wr:54.3, sharpe:1.48, drift:0.052, status:"err"  },
];

export default function MonitoringPage() {
    const [tab, setTab] = useState<"validation"|"mlflow">("validation");

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <ShieldCheck className="size-4 text-rose-400" />
                <h1 className="text-sm font-bold text-white">Monitoring & Validation</h1>
                <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DSO4.1 · DSO4.2</span>
                <div className="ml-auto flex gap-1 p-1 rounded-lg bg-white/[0.03] border border-white/5">
                    {[{id:"validation",l:"Validation Données (DSO4.1)"},{id:"mlflow",l:"MLflow Metrics (DSO4.2)"}].map(t=>(
                        <button key={t.id} onClick={()=>setTab(t.id as any)}
                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${tab===t.id?"bg-rose-600 text-white":"text-slate-400 hover:text-white"}`}>
                            {t.l}
                        </button>
                    ))}
                </div>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">

                {/* KPI row always visible */}
                <FadeInUp>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                            { l:"Qualité Données",   v:99.2, s:"%", c:"text-emerald-400", desc:"DSO4.1 · Seuil: 90%" },
                            { l:"Latence Inference",  v:48,   s:"ms",c:"text-blue-400",   desc:"DSO4.2 · Cible < 200ms" },
                            { l:"Drift Signal (PSI)", v:0.028,s:"",  c:"text-amber-400",  desc:"DSO4.2 · Seuil: 0.05" },
                            { l:"Uptime Système",     v:99.7, s:"%", c:"text-violet-400", desc:"7 jours glissants" },
                        ].map((k,i) => (
                            <motion.div key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                className="p-4 rounded-xl border border-white/5 bg-white/[0.03] text-center">
                                <div className={`text-xl font-bold ${k.c}`}>
                                    <AnimatedCounter to={k.v} suffix={k.s} decimals={k.v<1?3:1}/>
                                </div>
                                <div className="text-[10px] text-slate-400 mt-0.5">{k.l}</div>
                                <div className="text-[9px] text-slate-600">{k.desc}</div>
                            </motion.div>
                        ))}
                    </div>
                </FadeInUp>

                {tab === "validation" && <>
                    <FloatingCard delay={0.1}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-sm font-bold text-white mb-1">Pipeline de Validation des Données (DSO4.1)</h3>
                            <p className="text-[11px] text-slate-500 mb-4">Contrôles automatiques à chaque collecte · Valeurs manquantes · Outliers · Cohérence temporelle · Qualité OHLC</p>
                            <StaggerContainer>
                                {validationChecks.map((c,i) => (
                                    <StaggerItem key={i}>
                                        <div className="flex items-center gap-4 p-3 rounded-lg bg-white/[0.03] border border-white/5 mb-2">
                                            <div className="shrink-0">
                                                {c.status==="ok"  && <CheckCircle2 className="size-4 text-emerald-400"/>}
                                                {c.status==="warn" && <AlertTriangle className="size-4 text-amber-400"/>}
                                                {c.status==="err"  && <XCircle className="size-4 text-rose-400"/>}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex justify-between items-center">
                                                    <span className="text-sm text-white">{c.label}</span>
                                                    <span className={`text-xs font-bold ${c.score>=c.threshold?"text-emerald-400":"text-amber-400"}`}>{c.score}%</span>
                                                </div>
                                                <p className="text-[10px] text-slate-500 mt-0.5">{c.detail}</p>
                                                <AnimatedProgressBar value={c.score} color={c.score>=c.threshold?"emerald":"amber"} height={3} className="mt-1"/>
                                            </div>
                                        </div>
                                    </StaggerItem>
                                ))}
                            </StaggerContainer>
                        </div>
                    </FloatingCard>
                </>}

                {tab === "mlflow" && <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Latency */}
                        <FloatingCard delay={0.1}>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <h3 className="text-sm font-bold text-white mb-1">Latence End-to-End (DSO4.2)</h3>
                                <p className="text-[11px] text-slate-500 mb-4">Inférence ML + Pipeline de données — 7 derniers jours</p>
                                <ResponsiveContainer width="100%" height={200}>
                                    <BarChart data={latency7d}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                        <XAxis dataKey="day" tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false}/>
                                        <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} unit="ms"/>
                                        <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                        <Bar dataKey="inference" name="Inférence" fill="#6366f1" radius={[4,4,0,0]}/>
                                        <Bar dataKey="pipeline"  name="Pipeline"  fill="#3b82f6" radius={[4,4,0,0]}/>
                                        <ReferenceLine y={200} stroke="#f43f5e" strokeDasharray="4 4" label={{value:"Seuil 200ms",position:"right",fontSize:9,fill:"#f43f5e"}}/>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </FloatingCard>

                        {/* Signal Drift */}
                        <FloatingCard delay={0.15}>
                            <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                                <h3 className="text-sm font-bold text-white mb-1">Drift du Signal (PSI) — 30 jours</h3>
                                <p className="text-[11px] text-slate-500 mb-4">Population Stability Index · Alerte si PSI &gt; 0.05</p>
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={signalDrift}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                        <XAxis dataKey="day" tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false}/>
                                        <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} domain={[0,0.08]}/>
                                        <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                        <Line type="monotone" dataKey="drift" stroke="#f59e0b" strokeWidth={2} dot={false} name="PSI"/>
                                        <Line type="monotone" dataKey="threshold" stroke="#f43f5e" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Seuil"/>
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </FloatingCard>
                    </div>

                    {/* MLflow run history */}
                    <FloatingCard delay={0.2}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-sm font-bold text-white mb-4">Historique des Runs MLflow (DSO4.2)</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-[11px]">
                                    <thead>
                                        <tr className="text-slate-500 border-b border-white/5">
                                            {["Run","Win Rate","Sharpe","PSI Drift","Statut"].map(h=>(
                                                <th key={h} className="py-2 px-3 text-left font-medium">{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {runHistory.map((r,i)=>(
                                            <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                                                <td className="py-2 px-3 font-mono text-slate-400">{r.run}</td>
                                                <td className="py-2 px-3 text-emerald-400">{r.wr}%</td>
                                                <td className="py-2 px-3 text-blue-400">{r.sharpe}</td>
                                                <td className={`py-2 px-3 ${r.drift>=0.05?"text-rose-400":r.drift>=0.04?"text-amber-400":"text-emerald-400"}`}>{r.drift}</td>
                                                <td className="py-2 px-3">
                                                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${r.status==="ok"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":r.status==="warn"?"bg-amber-500/15 text-amber-400 border-amber-500/30":"bg-rose-500/15 text-rose-400 border-rose-500/30"}`}>
                                                        {r.status==="ok"?"OK":r.status==="warn"?"ATTENTION":"ERREUR"}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </FloatingCard>
                </>}
            </div>
        </div>
    );
}
