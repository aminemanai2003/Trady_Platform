"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "trady_onboarding_complete";

export interface TourStep {
    target: string;        // CSS selector for the spotlight
    title: string;
    content: string;
    placement?: "top" | "bottom" | "left" | "right";
}

export const TOUR_STEPS: TourStep[] = [
    {
        target: "[data-tour='dashboard-kpis']",
        title: "📊 Portfolio KPIs",
        content: "Track your Sharpe ratio, win rate, max drawdown and other key performance indicators in real time.",
        placement: "bottom",
    },
    {
        target: "[data-tour='agents-lab']",
        title: "🤖 AI Agents Lab",
        content: "Run the full 4-agent pipeline: Technical, Macro, Sentiment, and Geopolitical. Each agent votes with a weighted score.",
        placement: "right",
    },
    {
        target: "[data-tour='xai-breakdown']",
        title: "🔍 Explainable AI",
        content: "The XAI Breakdown shows exactly which agent influenced the decision and why — including the LLM Judge's reasoning.",
        placement: "top",
    },
    {
        target: "[data-tour='actuarial-metrics']",
        title: "📉 Actuarial Risk Model",
        content: "Every signal is scored with Expected Value (pips), Probability of Win, Risk-Reward Ratio, and Kelly Criterion position sizing.",
        placement: "top",
    },
    {
        target: "[data-tour='paper-trading']",
        title: "💹 Paper Trading",
        content: "Approved signals automatically open simulated positions. Track PnL, drawdown, and exposure in real time.",
        placement: "left",
    },
    {
        target: "[data-tour='strategy-tutor']",
        title: "🎓 Strategy Tutor",
        content: "Upload trading books or PDFs. The RAG-powered tutor answers questions using your documents as context.",
        placement: "right",
    },
];

interface UseOnboardingReturn {
    isOpen: boolean;
    currentStep: number;
    totalSteps: number;
    step: TourStep;
    next: () => void;
    prev: () => void;
    skip: () => void;
    startTour: () => void;
    hasCompleted: boolean;
}

export function useOnboarding(): UseOnboardingReturn {
    const [hasCompleted, setHasCompleted] = useState(true); // default true → no flash on SSR
    const [isOpen, setIsOpen] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);

    useEffect(() => {
        const done = localStorage.getItem(STORAGE_KEY) === "1";
        setHasCompleted(done);
        if (!done) {
            // Small delay so page renders first
            setTimeout(() => setIsOpen(true), 800);
        }
    }, []);

    const complete = useCallback(() => {
        localStorage.setItem(STORAGE_KEY, "1");
        setHasCompleted(true);
        setIsOpen(false);
        setCurrentStep(0);
    }, []);

    const next = useCallback(() => {
        if (currentStep < TOUR_STEPS.length - 1) {
            setCurrentStep((s) => s + 1);
        } else {
            complete();
        }
    }, [currentStep, complete]);

    const prev = useCallback(() => {
        setCurrentStep((s) => Math.max(0, s - 1));
    }, []);

    const skip = useCallback(() => {
        complete();
    }, [complete]);

    const startTour = useCallback(() => {
        setCurrentStep(0);
        setIsOpen(true);
    }, []);

    return {
        isOpen,
        currentStep,
        totalSteps: TOUR_STEPS.length,
        step: TOUR_STEPS[currentStep],
        next,
        prev,
        skip,
        startTour,
        hasCompleted,
    };
}
