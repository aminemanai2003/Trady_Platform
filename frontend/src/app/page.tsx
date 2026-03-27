"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { TrendingUp, Brain, Newspaper, Shield, BarChart3, Users } from "lucide-react";
import BlurText from "@/components/BlurText";
import ShinyText from "@/components/ShinyText";
import GradientText from "@/components/GradientText";
import Particles from "@/components/Particles";
import StarBorder from "@/components/StarBorder";
import LightPillar from "@/components/LightPillar";
import SplashCursor from "@/components/SplashCursor";

const dsos = [
  { code: "DSO1.1", label: "Macro Agent", color: "#3b82f6", desc: "Directional bias score from -100 to +100 using FRED data: CPI, GDP, PMI, policy rates" },
  { code: "DSO1.2", label: "Technical Agent", color: "#10b981", desc: "120 multi-timeframe features: SMA, EMA, RSI, MACD, ATR, Bollinger Bands" },
  { code: "DSO1.3", label: "Sentiment Agent", color: "#f59e0b", desc: "FinBERT NLP on Reuters news with pair-level sentiment scoring" },
  { code: "DSO2.1", label: "Coordinator", color: "#8b5cf6", desc: "Weighted vote: Technical 40% - Macro 35% - Sentiment 25%" },
  { code: "DSO2.2", label: "Backtesting 5Y", color: "#f43f5e", desc: "Walk-forward validation with targets: Sharpe > 1.5, Win Rate > 55%" },
  { code: "DSO2.3", label: "Position Sizing", color: "#22d3ee", desc: "Kelly criterion + ATR-based risk management for optimal sizing" },
  { code: "DSO3.1", label: "Signal Validation", color: "#a78bfa", desc: "Conflict detection, quality filters, and confidence scoring" },
  { code: "DSO4.1", label: "Data Quality", color: "#4ade80", desc: "Pipeline validation: missing values, outliers, and timestamp consistency" },
  { code: "DSO4.2", label: "MLflow Monitoring", color: "#fb923c", desc: "Inference latency, PSI drift, and performance degradation alerts" },
  { code: "DSO5.1", label: "Analytics Reports", color: "#67e8f9", desc: "Structured signal history with explainable AI-agent rationale" },
];

const team = [
  { name: "Ines Chtioui", role: "Project Lead" },
  { name: "Amine Manai", role: "Project Manager" },
  { name: "Mariem Fersi", role: "Solution Architect" },
  { name: "Malek Chairat", role: "Data Scientist" },
  { name: "Maha Aloui", role: "Data Scientist" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#080d18] text-slate-100 overflow-hidden">
      <SplashCursor
        COLOR_PALETTE={["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b"]}
        BACK_COLOR={{ r: 8 / 255, g: 13 / 255, b: 24 / 255 }}
      />

      <div className="fixed inset-0 z-0">
        <Particles
          particleCount={120}
          particleColors={["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b"]}
          particleBaseSize={60}
          speed={0.5}
          moveParticlesOnHover
          alphaParticles
          className="w-full h-full"
        />
      </div>

      <nav className="relative z-20 flex items-center justify-between px-8 py-5 border-b border-white/5 bg-[#080d18]/60 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl overflow-hidden border border-white/10 flex items-center justify-center bg-gradient-to-br from-[#4D8048] to-[#0658BA]">
            <img
              src="/logo.png"
              alt="Trady"
              className="size-9 object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
            <TrendingUp className="size-5 text-white" style={{ display: "none" }} />
          </div>
          <ShinyText text="Trady" className="text-xl font-black" color="#e2e8f0" shineColor="#a78bfa" speed={3} />
          <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/20">
            DATAMINDS - ESPRIT 2025
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="px-4 py-2 rounded-lg text-sm text-slate-300 hover:text-white border border-white/10 hover:border-white/20 transition-all"
          >
            Login
          </Link>
          <StarBorder as="a" href="/dashboard" color="#8b5cf6" speed="4s" className="text-sm font-semibold cursor-pointer">
            Dashboard -&gt;
          </StarBorder>
        </div>
      </nav>

      <section className="relative z-10 w-full overflow-hidden">
        <div style={{ width: "100%", height: "68vh", minHeight: "500px", position: "relative" }}>
          <LightPillar
            topColor="#2596be"
            bottomColor="#395d41"
            intensity={1.4}
            rotationSpeed={0.3}
            glowAmount={0.002}
            pillarWidth={3}
            pillarHeight={0.4}
            noiseIntensity={0.5}
            pillarRotation={25}
            interactive={false}
            mixBlendMode="lighten"
            quality="medium"
            className="opacity-90"
          />
          <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#080d18] to-transparent pointer-events-none" />
          <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#080d18] to-transparent pointer-events-none" />
        </div>
      </section>

      <section className="relative z-10 text-center -mt-44 pb-20 px-6 max-w-5xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="mb-4">
          <ShinyText
            text="MULTI-AGENT FOREX INTELLIGENCE"
            className="text-[11px] tracking-[0.2em] font-bold uppercase"
            color="#475569"
            shineColor="#8b5cf6"
            speed={4}
          />
        </motion.div>

        <BlurText
          text="AI-Powered Forex Signal Prediction"
          className="text-4xl md:text-6xl font-extrabold text-white leading-tight mb-4 mx-auto w-full justify-center text-center"
          animateBy="words"
          direction="top"
          delay={80}
        />

        <motion.div className="text-lg mb-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}>
          <GradientText colors={["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]} className="text-lg md:text-xl font-semibold" animationSpeed={5}>
            EUR/USD - USD/JPY - GBP/USD - USD/CHF
          </GradientText>
        </motion.div>

        <motion.p className="text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }}>
          Three AI agents (Technical, Macro, Sentiment) coordinated by a multi-modal orchestrator to generate BUY/SELL/NEUTRAL signals,
          validated with 5-year backtesting and Kelly-driven risk controls.
        </motion.p>

        <motion.div className="flex flex-wrap items-center justify-center gap-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }}>
          <StarBorder as="a" href="/dashboard" color="#10b981" speed="5s" className="text-base font-bold cursor-pointer">
            <span className="flex items-center gap-2">
              <BarChart3 className="size-4" />
              Access Trady
            </span>
          </StarBorder>
          <Link
            href="/login"
            className="flex items-center gap-2 px-6 py-3 rounded-xl border border-white/10 bg-white/[0.03] text-white font-bold hover:border-white/20 hover:bg-white/[0.06] transition-all text-sm"
          >
            <Shield className="size-4 text-violet-400" />
            Sign in
          </Link>
        </motion.div>

        <motion.div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mt-20" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.3 }}>
          {[
            { v: "120", l: "Features", c: "#8b5cf6" },
            { v: "5Y", l: "History", c: "#3b82f6" },
            { v: "57%", l: "Win Rate", c: "#10b981" },
            { v: "1.73", l: "Sharpe", c: "#f59e0b" },
            { v: "3", l: "AI Agents", c: "#f43f5e" },
            { v: "4", l: "Forex Pairs", c: "#22d3ee" },
          ].map((s, i) => (
            <motion.div
              key={i}
              whileHover={{ scale: 1.05, y: -2 }}
              transition={{ type: "spring", stiffness: 300 }}
              className="p-4 rounded-xl bg-white/[0.04] border border-white/8 text-center cursor-default"
            >
              <div className="text-2xl font-black" style={{ color: s.c }}>
                {s.v}
              </div>
              <div className="text-[10px] text-slate-500 mt-1">{s.l}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      <section className="relative z-10 px-6 py-20 max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <BlurText text="Data Science Objectives" className="text-3xl font-bold text-white mb-3 w-full justify-center text-center" delay={50} direction="bottom" />
          <ShinyText text="10 DSOs - 5 Business Objectives - Complete AI pipeline" className="text-sm" color="#475569" shineColor="#6366f1" speed={5} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {dsos.map((d, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.92 }}
              whileInView={{ opacity: 1, scale: 1 }}
              whileHover={{ y: -4, scale: 1.02 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.03, type: "spring", stiffness: 260, damping: 20 }}
              className="p-4 rounded-xl border bg-white/[0.03] hover:bg-white/[0.06] transition-colors cursor-default"
              style={{ borderColor: `${d.color}30` }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded font-bold" style={{ color: d.color, background: `${d.color}18`, border: `1px solid ${d.color}30` }}>
                  {d.code}
                </span>
              </div>
              <div className="text-xs font-bold text-white mb-1">{d.label}</div>
              <p className="text-[10px] text-slate-500 leading-relaxed">{d.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="relative z-10 px-6 py-12 border-t border-white/5">
        <div className="max-w-5xl mx-auto text-center">
          <Users className="size-6 text-violet-400 mx-auto mb-3" />
          <BlurText text="Our Team Members" className="text-xl font-bold text-white mb-1 w-full justify-center text-center" delay={50} />
          <ShinyText text="Private Higher School of Engineering and Technology - ESPRIT 2025" className="text-xs mb-6 block" color="#475569" shineColor="#8b5cf6" speed={6} />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-stretch">
            {team.map((member, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="px-4 py-3 rounded-xl bg-white/[0.04] border border-white/10 text-left hover:border-white/20 transition-colors min-h-[88px]"
              >
                <div className="text-sm font-semibold text-white">{member.name}</div>
                <div className="text-[11px] text-slate-500 mt-1">{member.role}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <footer className="relative z-10 text-center py-6 border-t border-white/5 text-slate-600 text-xs">
        <ShinyText text="Trady - DATAMINDS - ESPRIT 2025 - Data Science Project" color="#334155" shineColor="#6366f1" speed={8} />
      </footer>
    </div>
  );
}
