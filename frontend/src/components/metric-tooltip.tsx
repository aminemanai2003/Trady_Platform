"use client";

import { Info } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface MetricTooltipProps {
    label: string;
    description: string;
    className?: string;
}

const METRIC_DOCS: Record<string, string> = {
    "Sharpe Ratio":
        "Risk-adjusted return: (portfolio return – risk-free rate) / standard deviation. Above 1 is good, above 2 is excellent.",
    "Max Drawdown":
        "Largest peak-to-trough portfolio decline. Measures worst-case scenario loss from a historical high point.",
    "Kelly Fraction":
        "Kelly Criterion: optimal fraction of capital to risk per bet, given edge and odds. Half-Kelly is used for conservatism.",
    "Win Rate":
        "Percentage of closed trades that resulted in profit. Must be evaluated alongside the R:R ratio.",
    "Expected Value":
        "Average profit/loss per trade in pips, calculated as: (Prob. Win × TP pips) – (Prob. Loss × SL pips).",
    "Confidence":
        "Agent's certainty score (0–100%) for its signal direction, derived from feature consensus and model calibration.",
    "R:R Ratio":
        "Risk-to-reward ratio. A ratio of 1:2 means the potential gain is twice the potential loss.",
    "Prob. Win":
        "Estimated probability of the trade reaching take-profit before stop-loss, based on actuarial modeling.",
    "Prob. Loss":
        "Estimated probability of hitting the stop-loss before take-profit.",
    "Kelly Sizing":
        "Fraction of total capital allocated to this trade based on the Kelly Criterion with a 0.5× safety factor.",
    "Win Probability":
        "Estimated probability of the trade reaching take-profit before stop-loss.",
    "Loss Probability":
        "Estimated probability of hitting the stop-loss.",
    "Risk / Reward":
        "Ratio of average potential gain to average potential loss. A minimum of 1.5:1 is required by the risk manager.",
};

export function MetricTooltip({ label, description, className }: MetricTooltipProps) {
    const content = METRIC_DOCS[label] ?? description;

    return (
        <TooltipProvider delayDuration={150}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <span
                        className={`inline-flex items-center gap-1 text-xs text-slate-400 cursor-help hover:text-slate-200 transition-colors ${className ?? ""}`}
                    >
                        {label}
                        <Info className="size-3 opacity-60" />
                    </span>
                </TooltipTrigger>
                <TooltipContent
                    side="top"
                    className="max-w-xs text-xs bg-slate-900 border-white/10 text-slate-200"
                >
                    {content}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
