"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { useOnboarding } from "@/hooks/use-onboarding";

interface SpotlightRect {
    top: number;
    left: number;
    width: number;
    height: number;
}

const PADDING = 12;

export function OnboardingTour() {
    const { isOpen, currentStep, totalSteps, step, next, prev, skip } = useOnboarding();
    const [spotlight, setSpotlight] = useState<SpotlightRect | null>(null);
    const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);
    const tooltipRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isOpen || !step) return;

        function measure() {
            const el = document.querySelector(step!.target) as HTMLElement | null;
            if (!el) {
                setSpotlight(null);
                setTooltipPos(null);
                return;
            }
            const rect = el.getBoundingClientRect();
            const spRect: SpotlightRect = {
                top: rect.top - PADDING,
                left: rect.left - PADDING,
                width: rect.width + PADDING * 2,
                height: rect.height + PADDING * 2,
            };
            setSpotlight(spRect);

            // Position tooltip below or above
            const ttHeight = tooltipRef.current?.offsetHeight ?? 160;
            const spaceBelow = window.innerHeight - rect.bottom - PADDING;
            const topBelow = rect.bottom + PADDING + 8;
            const topAbove = rect.top - PADDING - ttHeight - 8;

            const top = spaceBelow > ttHeight ? topBelow : topAbove;
            const left = Math.max(
                16,
                Math.min(rect.left, window.innerWidth - 360 - 16)
            );
            setTooltipPos({ top, left });
        }

        measure();
        window.addEventListener("resize", measure);
        window.addEventListener("scroll", measure, true);
        return () => {
            window.removeEventListener("resize", measure);
            window.removeEventListener("scroll", measure, true);
        };
    }, [isOpen, step, currentStep]);

    if (!isOpen || !step) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Dark overlay with spotlight cutout */}
                    <motion.div
                        key="overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[9998] pointer-events-auto"
                        onClick={skip}
                        style={{ background: "rgba(2,6,23,0.75)" }}
                    >
                        {spotlight && (
                            <div
                                className="absolute rounded-xl ring-2 ring-violet-500 bg-transparent pointer-events-none"
                                style={{
                                    top: spotlight.top,
                                    left: spotlight.left,
                                    width: spotlight.width,
                                    height: spotlight.height,
                                    boxShadow: "0 0 0 9999px rgba(2,6,23,0.75)",
                                }}
                            />
                        )}
                    </motion.div>

                    {/* Tooltip popup */}
                    {tooltipPos && (
                        <motion.div
                            ref={tooltipRef}
                            key={`tip-${currentStep}`}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 6 }}
                            transition={{ duration: 0.2 }}
                            className="fixed z-[9999] w-80 rounded-2xl border border-violet-500/30 bg-slate-900/95 backdrop-blur-sm p-5 shadow-2xl"
                            style={tooltipPos}
                        >
                            {/* Header */}
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <Sparkles className="size-4 text-violet-400 flex-shrink-0" />
                                    <span className="text-xs font-bold text-violet-400 uppercase tracking-widest">
                                        {currentStep + 1} / {totalSteps}
                                    </span>
                                </div>
                                <button
                                    onClick={skip}
                                    className="text-slate-500 hover:text-slate-300 transition-colors"
                                >
                                    <X className="size-4" />
                                </button>
                            </div>

                            {/* Progress dots */}
                            <div className="flex gap-1.5 mb-4">
                                {Array.from({ length: totalSteps }).map((_, i) => (
                                    <div
                                        key={i}
                                        className={`h-1 rounded-full transition-all duration-300 ${
                                            i === currentStep
                                                ? "flex-1 bg-violet-500"
                                                : i < currentStep
                                                ? "w-6 bg-violet-700"
                                                : "w-3 bg-white/10"
                                        }`}
                                    />
                                ))}
                            </div>

                            <h3 className="text-sm font-bold text-white mb-1.5">{step.title}</h3>
                            <p className="text-xs text-slate-400 leading-relaxed mb-5">{step.content}</p>

                            {/* Navigation */}
                            <div className="flex items-center justify-between">
                                <button
                                    onClick={prev}
                                    disabled={currentStep === 0}
                                    className="flex items-center gap-1 text-xs text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
                                >
                                    <ChevronLeft className="size-3.5" /> Back
                                </button>
                                <button
                                    onClick={skip}
                                    className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
                                >
                                    Skip tour
                                </button>
                                <button
                                    onClick={next}
                                    className="flex items-center gap-1 text-xs text-white bg-violet-600 hover:bg-violet-500 transition-colors px-3 py-1.5 rounded-lg font-semibold"
                                >
                                    {currentStep === totalSteps - 1 ? "Done" : "Next"}
                                    {currentStep < totalSteps - 1 && <ChevronRight className="size-3.5" />}
                                </button>
                            </div>
                        </motion.div>
                    )}
                </>
            )}
        </AnimatePresence>,
        document.body
    );
}
