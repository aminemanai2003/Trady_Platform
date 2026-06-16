"use client";

import { useEffect, useRef, useState, ReactNode } from "react";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";

// â”€â”€â”€ Animated Counter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function AnimatedCounter({
    from = 0,
    to,
    duration = 1.5,
    suffix = "",
    prefix = "",
    decimals = 0,
    className = "",
}: {
    from?: number;
    to: number;
    duration?: number;
    suffix?: string;
    prefix?: string;
    decimals?: number;
    className?: string;
}) {
    const ref = useRef<HTMLSpanElement>(null);
    const inView = useInView(ref, { once: true });
    const motionVal = useMotionValue(from);
    const spring = useSpring(motionVal, { duration: duration * 1000, bounce: 0 });
    const [display, setDisplay] = useState(from.toFixed(decimals));

    useEffect(() => {
        if (inView) motionVal.set(to);
    }, [inView, to, motionVal]);

    useEffect(() => {
        return spring.on("change", (v) => setDisplay(v.toFixed(decimals)));
    }, [spring, decimals]);

    return (
        <span ref={ref} className={className}>
            {prefix}{display}{suffix}
        </span>
    );
}

// â”€â”€â”€ Fade In Up â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function FadeInUp({
    children,
    delay = 0,
    duration = 0.5,
    className = "",
}: {
    children: ReactNode;
    delay?: number;
    duration?: number;
    className?: string;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration, delay, ease: "easeOut" }}
            className={className}
        >
            {children}
        </motion.div>
    );
}

// â”€â”€â”€ Stagger Container â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function StaggerContainer({
    children,
    staggerDelay = 0.1,
    className = "",
}: {
    children: ReactNode;
    staggerDelay?: number;
    className?: string;
}) {
    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={{
                visible: { transition: { staggerChildren: staggerDelay } },
                hidden: {},
            }}
            className={className}
        >
            {children}
        </motion.div>
    );
}

export function StaggerItem({
    children,
    className = "",
}: {
    children: ReactNode;
    className?: string;
}) {
    return (
        <motion.div
            variants={{
                hidden: { opacity: 0, y: 16 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
            }}
            className={className}
        >
            {children}
        </motion.div>
    );
}

// â”€â”€â”€ Spotlight Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function SpotlightCard({
    children,
    className = "",
    spotlightColor = "rgba(139,92,246,0.15)",
}: {
    children: ReactNode;
    className?: string;
    spotlightColor?: string;
}) {
    const card = useRef<HTMLDivElement>(null);
    const [pos, setPos] = useState({ x: 0, y: 0 });
    const [isHovered, setHovered] = useState(false);

    const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!card.current) return;
        const rect = card.current.getBoundingClientRect();
        setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };

    return (
        <div
            ref={card}
            onMouseMove={handleMove}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            className={`relative overflow-hidden ${className}`}
            style={{
                background: isHovered
                    ? `radial-gradient(300px circle at ${pos.x}px ${pos.y}px, ${spotlightColor}, transparent 80%)`
                    : undefined,
            }}
        >
            {children}
        </div>
    );
}

// â”€â”€â”€ Shimmer Border Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function ShimmerCard({
    children,
    className = "",
}: {
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={`relative group rounded-xl overflow-hidden ${className}`}>
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-violet-500 via-blue-500 to-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-[1px]" />
            <div className="absolute inset-[1px] rounded-xl bg-slate-900/95 z-10" />
            <div className="relative z-20">{children}</div>
        </div>
    );
}

// â”€â”€â”€ Aurora Background â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function AuroraBackground({ className = "" }: { className?: string }) {
    return (
        <div className={`fixed inset-0 pointer-events-none overflow-hidden ${className}`}>
            <div className="aurora-orb-1 absolute w-[700px] h-[700px] rounded-full opacity-[0.07]" />
            <div className="aurora-orb-2 absolute w-[500px] h-[500px] rounded-full opacity-[0.07]" />
            <div className="aurora-orb-3 absolute w-[600px] h-[600px] rounded-full opacity-[0.05]" />
            {/* Subtle grid */}
            <div
                className="absolute inset-0 opacity-[0.03]"
                style={{
                    backgroundImage:
                        "linear-gradient(rgba(148,163,184,1) 1px, transparent 1px), linear-gradient(to right, rgba(148,163,184,1) 1px, transparent 1px)",
                    backgroundSize: "60px 60px",
                }}
            />
        </div>
    );
}

// â”€â”€â”€ Glow Pulse Dot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function GlowDot({ color = "emerald" }: { color?: "emerald" | "violet" | "blue" | "amber" | "rose" }) {
    const colorMap: Record<string, string> = {
        emerald: "bg-emerald-500 shadow-emerald-500/50",
        violet:  "bg-violet-500 shadow-violet-500/50",
        blue:    "bg-blue-500 shadow-blue-500/50",
        amber:   "bg-amber-500 shadow-amber-500/50",
        rose:    "bg-rose-500 shadow-rose-500/50",
    };
    return (
        <span className={`inline-block size-2 rounded-full shadow-lg animate-pulse ${colorMap[color]}`} />
    );
}

// â”€â”€â”€ DSO Badge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function DSOBadge({ code, label }: { code: string; label: string }) {
    return (
        <motion.span
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                       bg-violet-500/10 border border-violet-500/30 text-violet-300"
        >
            <span className="font-mono text-violet-400">{code}</span>
            <span className="text-slate-300">{label}</span>
        </motion.span>
    );
}

// â”€â”€â”€ Progress Bar Animated â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function AnimatedProgressBar({
    value,
    max = 100,
    color = "violet",
    height = 6,
    className = "",
}: {
    value: number;
    max?: number;
    color?: string;
    height?: number;
    className?: string;
}) {
    const pct = Math.min(100, (value / max) * 100);
    const colorMap: Record<string, string> = {
        emerald: "bg-emerald-500",
        violet:  "bg-violet-500",
        blue:    "bg-blue-500",
        amber:   "bg-amber-500",
        rose:    "bg-rose-500",
    };
    return (
        <div className={`w-full bg-white/5 rounded-full overflow-hidden ${className}`} style={{ height }}>
            <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
                className={`h-full rounded-full ${colorMap[color] || "bg-violet-500"}`}
            />
        </div>
    );
}

// â”€â”€â”€ Floating Label Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function FloatingCard({
    children,
    className = "",
    delay = 0,
}: {
    children: ReactNode;
    className?: string;
    delay?: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay, ease: "easeOut" }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className={className}
        >
            {children}
        </motion.div>
    );
}

// â”€â”€â”€ Typewriter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function Typewriter({ text, delay = 0, speed = 40 }: { text: string; delay?: number; speed?: number }) {
    const [display, setDisplay] = useState("");
    const [started, setStarted] = useState(false);

    useEffect(() => {
        const timeout = setTimeout(() => setStarted(true), delay * 1000);
        return () => clearTimeout(timeout);
    }, [delay]);

    useEffect(() => {
        if (!started) return;
        let i = 0;
        const timer = setInterval(() => {
            setDisplay(text.slice(0, i + 1));
            i++;
            if (i >= text.length) clearInterval(timer);
        }, speed);
        return () => clearInterval(timer);
    }, [started, text, speed]);

    return <span>{display}<span className="animate-pulse">|</span></span>;
}

// â”€â”€â”€ Metric Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function MetricCard({
    icon: Icon,
    label,
    value,
    suffix = "",
    prefix = "",
    subtext,
    color = "violet",
    decimals = 0,
    delay = 0,
}: {
    icon: React.ElementType;
    label: string;
    value: number;
    suffix?: string;
    prefix?: string;
    subtext?: string;
    color?: string;
    decimals?: number;
    delay?: number;
}) {
    const colorMap: Record<string, { icon: string; glow: string; bg: string }> = {
        emerald: { icon: "text-emerald-400", glow: "shadow-emerald-500/20", bg: "bg-emerald-500/10 border-emerald-500/20" },
        violet:  { icon: "text-violet-400",  glow: "shadow-violet-500/20",  bg: "bg-violet-500/10 border-violet-500/20"  },
        blue:    { icon: "text-blue-400",     glow: "shadow-blue-500/20",    bg: "bg-blue-500/10 border-blue-500/20"       },
        amber:   { icon: "text-amber-400",    glow: "shadow-amber-500/20",   bg: "bg-amber-500/10 border-amber-500/20"    },
        rose:    { icon: "text-rose-400",     glow: "shadow-rose-500/20",    bg: "bg-rose-500/10 border-rose-500/20"       },
    };
    const c = colorMap[color] || colorMap.violet;

    return (
        <FloatingCard delay={delay}>
            <div className={`p-5 rounded-xl border bg-white/[0.03] backdrop-blur-sm shadow-xl ${c.glow}`}>
                <div className="flex items-center gap-3 mb-3">
                    <div className={`p-2.5 rounded-lg border ${c.bg}`}>
                        <Icon className={`size-4 ${c.icon}`} />
                    </div>
                    <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
                </div>
                <div className="text-2xl font-bold text-white">
                    <AnimatedCounter to={value} decimals={decimals} prefix={prefix} suffix={suffix} />
                </div>
                {subtext && <div className="text-xs text-slate-500 mt-1.5">{subtext}</div>}
            </div>
        </FloatingCard>
    );
}

