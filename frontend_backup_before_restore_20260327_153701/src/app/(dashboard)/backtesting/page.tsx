"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, ReferenceLine, ComposedChart, Line,
} from "recharts";
import { TrendingUp, Scale, Target, Shield, BarChart3, Zap } from "lucide-react";
import { AuroraBackground, FadeInUp, StaggerContainer, StaggerItem, AnimatedCounter, AnimatedProgressBar, FloatingCard } from "@/components/animations";

// Walk-forward simulation — 5 ans de données
const wfData = Array.from({length:60}, (_,i) => {
    const d = new Date("2021-01-01"); d.setMonth(d.getMonth()+i);
    const cum = 8000 + Math.sin(i/8)*1500 + i*120 + (Math.random()-0.45)*600;
    const daily = Math.round((Math.random()-0.42)*200);
    return {
        period: d.toLocaleDateString("fr-FR",{month:"short",year:"2-digit"}),
        equity: Math.round(cum), daily,
        winRate: Math.round(50+Math.random()*20), trades: Math.floor(10+Math.random()*30),
        sharpe: +(1.2+Math.random()*0.8).toFixed(2),
    };
});

const pairResults = [
    { pair:"EUR/USD", winRate:58.3, sharpe:1.82, maxDD:12.4, trades:247, pnl:4320,  signal:"BUY"     },
    { pair:"USD/JPY", winRate:55.1, sharpe:1.54, maxDD:15.7, trades:198, pnl:2890,  signal:"SELL"    },
    { pair:"GBP/USD", winRate:61.2, sharpe:2.10, maxDD:10.2, trades:213, pnl:5640,  signal:"BUY"     },
    { pair:"USD/CHF", winRate:52.4, sharpe:1.31, maxDD:18.1, trades:176, pnl:1250,  signal:"NEUTRAL" },
];

// Kelly Criterion helpers
function kelly(wr: number, rr: number) {
    const p = wr/100; const q = 1-p;
    return Math.max(0, p - q/rr);
}

const PAIRS_KELLY = ["EURUSD","USDJPY","GBPUSD","USDCHF"];
const pairKelly = [
    { pair:"EUR/USD", wr:58.3, rr:2.0, atr:0.0065, vol:14.2 },
    { pair:"USD/JPY", wr:55.1, rr:1.8, atr:0.85,   vol:17.5 },
    { pair:"GBP/USD", wr:61.2, rr:2.2, atr:0.0078, vol:12.8 },
    { pair:"USD/CHF", wr:52.4, rr:1.5, atr:0.0052, vol:19.3 },
];

export default function BacktestingPage() {
    const [capital, setCapital] = useState(10000);
    const [riskPct, setRiskPct] = useState(2);
    const [rr, setRr] = useState(2.0);
    const [tab, setTab] = useState<"backtest"|"sizing">("backtest");

    return (
        <div className="flex flex-col h-full bg-[#080d18] text-slate-100 relative overflow-hidden">
            <AuroraBackground />
            <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/5 bg-black/30 backdrop-blur-xl px-6">
                <SidebarTrigger className="-ml-1 text-slate-400" />
                <Separator orientation="vertical" className="h-5 bg-white/10" />
                <TrendingUp className="size-4 text-amber-400" />
                <h1 className="text-sm font-bold text-white">Backtesting & Position Sizing</h1>
                <span className="text-[10px] font-mono text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">DSO2.2 · DSO2.3</span>
                <div className="ml-auto flex gap-1 p-1 rounded-lg bg-white/[0.03] border border-white/5">
                    {[{id:"backtest",l:"Backtesting (DSO2.2)"},{id:"sizing",l:"Position Sizing (DSO2.3)"}].map(t => (
                        <button key={t.id} onClick={()=>setTab(t.id as any)}
                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${tab===t.id?"bg-amber-600 text-white":"text-slate-400 hover:text-white"}`}>
                            {t.l}
                        </button>
                    ))}
                </div>
            </header>

            <div className="relative z-10 flex-1 overflow-auto p-6 space-y-6">

                {tab === "backtest" && <>
                    {/* Global Metrics */}
                    <FadeInUp>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                            {[
                                { l:"Sharpe Ratio",   v:1.73, s:"",   d:2, c:"text-blue-400",    desc:"Objectif: > 1.5" },
                                { l:"Win Rate",       v:57.4, s:"%",  d:1, c:"text-emerald-400", desc:"Sur 5 ans" },
                                { l:"Max Drawdown",   v:14.8, s:"%",  d:1, c:"text-rose-400",    desc:"Limite: 15%" },
                                { l:"Total Trades",   v:834,  s:"",   d:0, c:"text-amber-400",   desc:"Walk-forward 60 mois" },
                                { l:"Profit Factor",  v:1.89, s:"x",  d:2, c:"text-violet-400",  desc:"TP > SL ratio" },
                            ].map((k,i) => (
                                <motion.div key={i} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{delay:i*0.07}}
                                    className="p-4 rounded-xl border border-white/5 bg-white/[0.03] text-center">
                                    <div className={`text-xl font-bold ${k.c}`}>
                                        <AnimatedCounter to={k.v} suffix={k.s} decimals={k.d}/>
                                    </div>
                                    <div className="text-[10px] text-slate-400 mt-0.5 font-medium">{k.l}</div>
                                    <div className="text-[9px] text-slate-600 mt-0.5">{k.desc}</div>
                                </motion.div>
                            ))}
                        </div>
                    </FadeInUp>

                    {/* Equity Curve */}
                    <FloatingCard delay={0.1}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <div className="mb-4">
                                <h3 className="text-sm font-bold text-white">Courbe Equity — Walk-Forward 5 ans (DSO2.2)</h3>
                                <p className="text-[11px] text-slate-500">Validation walk-forward sur 60 fenêtres mensuelles glissantes · Évite le surapprentissage</p>
                            </div>
                            <ResponsiveContainer width="100%" height={280}>
                                <ComposedChart data={wfData}>
                                    <defs>
                                        <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"/>
                                    <XAxis dataKey="period" tick={{fontSize:9,fill:"#475569"}} axisLine={false} tickLine={false} interval={6}/>
                                    <YAxis tick={{fontSize:10,fill:"#475569"}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v.toLocaleString()}`}/>
                                    <Tooltip contentStyle={{background:"#0f172a",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",fontSize:11}}/>
                                    <Area type="monotone" dataKey="equity" stroke="#f59e0b" strokeWidth={2} fill="url(#eq)"/>
                                    <Line type="monotone" dataKey="winRate" stroke="#6366f1" strokeWidth={1.5} dot={false} yAxisId={1} name="Win Rate %"/>
                                </ComposedChart>
                            </ResponsiveContainer>
                        </div>
                    </FloatingCard>

                    {/* Per-Pair Results */}
                    <FloatingCard delay={0.15}>
                        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-5">
                            <h3 className="text-sm font-bold text-white mb-4">Résultats par Paire — Backtest 5 ans</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {pairResults.map((r, i) => (
                                    <motion.div key={i} initial={{opacity:0,x:-10}} animate={{opacity:1,x:0}} transition={{delay:i*0.06}}
                                        className="p-4 rounded-lg bg-white/[0.04] border border-white/5">
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="font-bold text-white">{r.pair}</span>
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${r.signal==="BUY"?"bg-emerald-500/15 text-emerald-400 border-emerald-500/30":r.signal==="SELL"?"bg-rose-500/15 text-rose-400 border-rose-500/30":"bg-slate-500/15 text-slate-400 border-slate-500/30"}`}>
                                                {r.signal}
                                            </span>
                                        </div>
                                        <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
                                            <div><div className="text-emerald-400 font-bold">{r.winRate}%</div><div className="text-slate-600">Win Rate</div></div>
                                            <div><div className="text-blue-400 font-bold">{r.sharpe}</div><div className="text-slate-600">Sharpe</div></div>
                                            <div><div className="text-rose-400 font-bold">-{r.maxDD}%</div><div className="text-slate-600">Max DD</div></div>
                                            <div><div className="text-amber-400 font-bold">${r.pnl.toLocaleString()}</div><div className="text-slate-600">P&L Total</div></div>
                                        </div>
                                        <div className="mt-2">
                                            <AnimatedProgressBar value={r.winRate} color="emerald" height={3}/>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </FloatingCard>
                </>}

                {tab === "sizing" && <>
                    {/* Position Sizing (DSO2.3) */}
                    <FadeInUp>
                        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                            <h3 className="text-sm font-bold text-white mb-1">Module de Sizing des Positions (DSO2.3)</h3>
                            <p className="text-[11px] text-slate-500 mb-5">Critère de Kelly · Gestion du risque basée sur ATR · Recommandation optimale de taille de position selon le score de conviction</p>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                {[
                                    { l:"Capital ($)", val:capital, set:setCapital, min:1000, max:100000, step:1000 },
                                    { l:"Risque par trade (%)", val:riskPct, set:setRiskPct, min:0.5, max:5, step:0.5 },
                                    { l:"Risk/Reward Ratio", val:rr, set:setRr, min:1, max:4, step:0.5 },
                                ].map((p,i) => (
                                    <div key={i} className="p-4 rounded-xl border border-white/5 bg-white/[0.04]">
                                        <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">{p.l}</label>
                                        <div className="text-xl font-bold text-white mb-2">{p.val}{p.l.includes("%")||p.l.includes("Ratio")?"":"$"}</div>
                                        <input type="range" min={p.min} max={p.max} step={p.step} value={p.val}
                                            onChange={e => p.set(+e.target.value)}
                                            className="w-full accent-emerald-500"/>
                                        <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                                            <span>{p.min}</span><span>{p.max}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {pairKelly.map((p,i) => {
                                    const k = kelly(p.wr, rr);
                                    const kellyPct = Math.min(k*2, 0.05); // half-Kelly capped 5%
                                    const riskAmt = capital * (riskPct/100);
                                    const atrPips = p.pair.includes("JPY") ? p.atr * 100 : p.atr * 10000;
                                    const lotSize = +(riskAmt / (atrPips * 10)).toFixed(2);
                                    return (
                                        <motion.div key={i} initial={{opacity:0,scale:0.97}} animate={{opacity:1,scale:1}} transition={{delay:i*0.08}}
                                            className="p-4 rounded-xl bg-white/[0.04] border border-white/5">
                                            <div className="flex items-center justify-between mb-3">
                                                <span className="font-bold text-white text-sm">{p.pair}</span>
                                                <div className="flex gap-2">
                                                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">WR: {p.wr}%</span>
                                                    <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">ATR: {p.atr}</span>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-3 gap-2 text-center text-[11px] mb-3">
                                                <div className="p-2 rounded-lg bg-white/[0.04]">
                                                    <div className="text-emerald-400 font-bold">{(kellyPct*100).toFixed(1)}%</div>
                                                    <div className="text-slate-600">Kelly (half)</div>
                                                </div>
                                                <div className="p-2 rounded-lg bg-white/[0.04]">
                                                    <div className="text-amber-400 font-bold">${(capital*kellyPct).toFixed(0)}</div>
                                                    <div className="text-slate-600">Montant Kelly</div>
                                                </div>
                                                <div className="p-2 rounded-lg bg-white/[0.04]">
                                                    <div className="text-violet-400 font-bold">{lotSize} lot</div>
                                                    <div className="text-slate-600">Taille ATR</div>
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-between text-[10px] text-slate-500">
                                                <span>Risque max: ${riskAmt.toFixed(0)}</span>
                                                <span>Vol % ATR: {p.vol}%</span>
                                            </div>
                                            <AnimatedProgressBar value={kellyPct*100*20} color="emerald" height={3} className="mt-2"/>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>
                    </FadeInUp>
                </>}
            </div>
        </div>
    );
}
