"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { TrendingUp, Brain, Newspaper, ArrowRight, Shield, BarChart3, Users } from "lucide-react";
import BlurText from "@/components/BlurText";
import ShinyText from "@/components/ShinyText";
import GradientText from "@/components/GradientText";
import Particles from "@/components/Particles";
import StarBorder from "@/components/StarBorder";

const dsos = [
    { code:"DSO1.1", label:"Macro Agent",         color:"#3b82f6", desc:"Score biais -100→+100 via FRED: CPI, GDP, PMI, taux directeurs" },
    { code:"DSO1.2", label:"Technical Agent",      color:"#10b981", desc:"120 features multi-timeframe: SMA, EMA, RSI, MACD, ATR, BB" },
    { code:"DSO1.3", label:"Sentiment Agent",      color:"#f59e0b", desc:"FinBERT NLP sur news Reuters · Score sentiment par paire" },
    { code:"DSO2.1", label:"Coordinateur",         color:"#8b5cf6", desc:"Vote pondéré: Technique 40% · Macro 35% · Sentiment 25%" },
    { code:"DSO2.2", label:"Backtesting 5Y",       color:"#f43f5e", desc:"Walk-forward validation · Sharpe >1.5 · Win Rate >55%" },
    { code:"DSO2.3", label:"Position Sizing",      color:"#22d3ee", desc:"Critère de Kelly + gestion ATR · Risk management optimal" },
    { code:"DSO3.1", label:"Validation Signal",    color:"#a78bfa", desc:"Détection conflits · Filtre qualité · Score de confiance" },
    { code:"DSO4.1", label:"Data Quality",         color:"#4ade80", desc:"Pipeline validation: missing values, outliers, timestamps" },
    { code:"DSO4.2", label:"MLflow Monitoring",    color:"#fb923c", desc:"Latence inférence · Drift PSI · Performance degradation alerts" },
    { code:"DSO5.1", label:"Rapports Analytiques", color:"#67e8f9", desc:"Historique signaux structuré avec raisonnements agents IA" },
];

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-[#080d18] text-slate-100 overflow-hidden">
            {/* Particles background */}
            <div className="fixed inset-0 z-0">
                <Particles
                    particleCount={120}
                    particleColors={["#8b5cf6","#3b82f6","#10b981","#f59e0b"]}
                    particleBaseSize={60}
                    speed={0.5}
                    moveParticlesOnHover
                    alphaParticles
                    className="w-full h-full"
                />
            </div>

            {/* Nav */}
            <nav className="relative z-20 flex items-center justify-between px-8 py-5 border-b border-white/5 bg-[#080d18]/60 backdrop-blur-xl">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl overflow-hidden border border-white/10 flex items-center justify-center bg-gradient-to-br from-[#4D8048] to-[#0658BA]">
                        <img src="/logo.png" alt="Trady" className="size-9 object-cover"
                            onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display="none"; }}/>
                        <TrendingUp className="size-5 text-white" style={{display:"none"}} />
                    </div>
                    <ShinyText text="Trady" className="text-xl font-black" color="#e2e8f0" shineColor="#a78bfa" speed={3}/>
                    <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/20">
                        DATAMINDS · ESPRIT 2025
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <Link href="/login"
                        className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:text-white border border-white/10 hover:border-white/20 transition-all">
                        Connexion
                    </Link>
                    <StarBorder as="a" href="/dashboard" color="#8b5cf6" speed="4s"
                        className="text-sm font-semibold cursor-pointer">
                        Tableau de bord →
                    </StarBorder>
                </div>
            </nav>

            {/* Hero */}
            <section className="relative z-10 text-center pt-24 pb-16 px-6 max-w-5xl mx-auto">
                <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:0.5}} className="mb-4">
                    <ShinyText
                        text="MULTI-AGENT FOREX INTELLIGENCE"
                        className="text-[11px] tracking-[0.2em] font-bold uppercase"
                        color="#475569" shineColor="#8b5cf6" speed={4}
                    />
                </motion.div>

                <BlurText
                    text="Prédiction de Signaux Forex avec IA"
                    className="text-4xl md:text-6xl font-extrabold text-white leading-tight mb-4 mx-auto"
                    animateBy="words"
                    direction="top"
                    delay={80}
                />

                <motion.div className="text-lg mb-8" initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.7}}>
                    <GradientText
                        colors={["#8b5cf6","#3b82f6","#10b981","#f59e0b","#8b5cf6"]}
                        className="text-lg md:text-xl font-semibold"
                        animationSpeed={5}
                    >
                        EUR/USD · USD/JPY · GBP/USD · USD/CHF
                    </GradientText>
                </motion.div>

                <motion.p
                    className="text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
                    initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:0.9}}
                >
                    Trois agents IA (Technique, Macro, Sentiment) orchestrés par un coordinateur multi-modal pour générer des signaux BUY/SELL/NEUTRAL validés avec backtesting 5 ans et gestion du risque Kelly.
                </motion.p>

                <motion.div className="flex flex-wrap items-center justify-center gap-4"
                    initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{delay:1.1}}>
                    <StarBorder as="a" href="/dashboard" color="#10b981" speed="5s"
                        className="text-base font-bold cursor-pointer">
                        <span className="flex items-center gap-2"><BarChart3 className="size-4"/> Accéder à Trady</span>
                    </StarBorder>
                    <Link href="/login"
                        className="flex items-center gap-2 px-6 py-3 rounded-xl border border-white/10 bg-white/[0.03] text-white font-bold hover:border-white/20 hover:bg-white/[0.06] transition-all text-sm">
                        <Shield className="size-4 text-violet-400"/> Se connecter
                    </Link>
                </motion.div>

                {/* Stats */}
                <motion.div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mt-20"
                    initial={{opacity:0}} animate={{opacity:1}} transition={{delay:1.3}}>
                    {[
                        { v:"120",  l:"Features",       c:"#8b5cf6" },
                        { v:"5Y",   l:"Historique",      c:"#3b82f6" },
                        { v:"57%",  l:"Win Rate",        c:"#10b981" },
                        { v:"1.73", l:"Sharpe",          c:"#f59e0b" },
                        { v:"3",    l:"Agents IA",        c:"#f43f5e" },
                        { v:"4",    l:"Paires Forex",    c:"#22d3ee" },
                    ].map((s,i) => (
                        <motion.div key={i} whileHover={{scale:1.05,y:-2}} transition={{type:"spring",stiffness:300}}
                            className="p-4 rounded-xl bg-white/[0.04] border border-white/8 text-center cursor-default">
                            <div className="text-2xl font-black" style={{color:s.c}}>{s.v}</div>
                            <div className="text-[10px] text-slate-500 mt-1">{s.l}</div>
                        </motion.div>
                    ))}
                </motion.div>
            </section>

            {/* DSO Grid */}
            <section className="relative z-10 px-6 py-16 max-w-6xl mx-auto">
                <div className="text-center mb-12">
                    <BlurText text="Objectifs Data Science" className="text-3xl font-bold text-white mb-3" delay={50} direction="bottom"/>
                    <ShinyText text="10 DSOs · 5 Business Objectives · Pipeline IA complet"
                        className="text-sm" color="#475569" shineColor="#6366f1" speed={5}/>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
                    {dsos.map((d, i) => (
                        <motion.div key={i}
                            initial={{opacity:0,scale:0.92}} whileInView={{opacity:1,scale:1}}
                            whileHover={{y:-4,scale:1.02}} viewport={{once:true}}
                            transition={{delay:i*0.03, type:"spring", stiffness:260, damping:20}}
                            className="p-4 rounded-xl border bg-white/[0.03] hover:bg-white/[0.06] transition-colors cursor-default"
                            style={{borderColor:`${d.color}30`}}>
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded font-bold"
                                    style={{color:d.color, background:`${d.color}18`, border:`1px solid ${d.color}30`}}>
                                    {d.code}
                                </span>
                            </div>
                            <div className="text-xs font-bold text-white mb-1">{d.label}</div>
                            <p className="text-[10px] text-slate-500 leading-relaxed">{d.desc}</p>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Agents Section */}
            <section className="relative z-10 px-6 py-16 bg-white/[0.02] border-t border-white/5">
                <div className="max-w-4xl mx-auto">
                    <div className="text-center mb-10">
                        <BlurText text="Architecture Multi-Agents" className="text-2xl font-bold text-white mb-2" delay={60} direction="bottom"/>
                        <ShinyText text="Trois experts IA collaborent pour chaque signal" className="text-sm" color="#475569" shineColor="#10b981" speed={4}/>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[
                            { icon: Brain,    color:"#3b82f6", label:"Macro Agent",    dso:"DSO1.1", w:35, desc:"FRED API · CPI · NFP · Taux · LLM ECB/Fed analysis" },
                            { icon: TrendingUp,color:"#10b981",label:"Technical Agent", dso:"DSO1.2", w:40, desc:"60 indicateurs · Multi-timeframe · RSI MACD ATR BB" },
                            { icon: Newspaper, color:"#f59e0b",label:"Sentiment Agent", dso:"DSO1.3", w:25, desc:"FinBERT · Reuters · COT Reports · Social sentiment" },
                        ].map((a,i) => (
                            <motion.div key={i}
                                initial={{opacity:0,y:16}} whileInView={{opacity:1,y:0}}
                                whileHover={{y:-4}} viewport={{once:true}}
                                transition={{delay:i*0.1}}
                                className="p-5 rounded-xl border border-white/8 bg-white/[0.03] hover:bg-white/[0.06] transition-colors">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{background:`${a.color}18`, border:`1px solid ${a.color}30`}}>
                                        <a.icon className="size-5" style={{color:a.color}}/>
                                    </div>
                                    <div>
                                        <div className="text-sm font-bold text-white">{a.label}</div>
                                        <span className="text-[9px] font-mono" style={{color:a.color}}>{a.dso}</span>
                                    </div>
                                    <div className="ml-auto text-right">
                                        <div className="text-lg font-black" style={{color:a.color}}>{a.w}%</div>
                                        <div className="text-[9px] text-slate-600">poids</div>
                                    </div>
                                </div>
                                <p className="text-[11px] text-slate-500 leading-relaxed">{a.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                    <div className="text-center mt-8">
                        <StarBorder as="a" href="/agents" color="#8b5cf6" speed="6s" className="text-sm font-bold inline-block cursor-pointer">
                            <span className="flex items-center gap-2"><Brain className="size-4"/> Ouvrir le Signal Lab</span>
                        </StarBorder>
                    </div>
                </div>
            </section>

            {/* Team */}
            <section className="relative z-10 px-6 py-12 border-t border-white/5">
                <div className="max-w-3xl mx-auto text-center">
                    <Users className="size-6 text-violet-400 mx-auto mb-3"/>
                    <BlurText text="Équipe DATAMINDS" className="text-xl font-bold text-white mb-1" delay={50}/>
                    <ShinyText text="École Supérieure Privée d'Ingénierie et de Technologie — ESPRIT · 2025"
                        className="text-xs mb-6 block" color="#475569" shineColor="#8b5cf6" speed={6}/>
                    <div className="flex flex-wrap gap-3 justify-center">
                        {[
                            ["Mariem Chtioui","Lead ML / Macro Agent"],
                            ["Khalil Manai","NLP / Sentiment Agent"],
                            ["Youssef Fersi","Backtesting / Risk"],
                            ["Rayen Chairat","Feature Engineering"],
                            ["Mehdi Aloui","Architecture / Monitoring"],
                        ].map(([name,role],i) => (
                            <motion.div key={i} initial={{opacity:0,scale:0.9}} whileInView={{opacity:1,scale:1}} viewport={{once:true}} transition={{delay:i*0.06}}
                                className="px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-left hover:border-white/20 transition-colors">
                                <div className="text-sm font-semibold text-white">{name}</div>
                                <div className="text-[10px] text-slate-500">{role}</div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            <footer className="relative z-10 text-center py-6 border-t border-white/5 text-slate-600 text-xs">
                <ShinyText text="Trady · DATAMINDS · ESPRIT 2025 · Projet Data Science" color="#334155" shineColor="#6366f1" speed={8}/>
            </footer>
        </div>
    );
}
