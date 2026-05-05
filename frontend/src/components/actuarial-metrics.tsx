"use client";

import { motion } from "framer-motion";
import { TrendingUp, Target, Shield, Percent } from "lucide-react";
import { MetricTooltip } from "./metric-tooltip";
import type { MasterSignalResponse } from "@/types";

interface Props {
    actuarial: MasterSignalResponse["actuarial"];
    executionPlan?: MasterSignalResponse["execution_plan"];
}

interface MetricBarProps {
    label: string;
    tooltip: string;
    value: number;
    displayValue: string;
    max?: number;
    color?: string;
}

function MetricBar({ label, tooltip, value, displayValue, max = 100, color = "#8b5cf6" }: MetricBarProps) {
    const pct = Math.min(100, (value / max) * 100);
    return (
        <div className="space-y-1.5">
            <div className="flex items-center justify-between">
                <MetricTooltip label={label} description={tooltip} />
                <span className="text-sm font-bold text-white">{displayValue}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                    className="h-full rounded-full"
                    style={{ background: color }}
                />
            </div>
        </div>
    );
}

export function ActuarialMetrics({ actuarial, executionPlan }: Props) {
    const {
        expected_value_pips,
        probability_win,
        probability_loss,
        risk_reward_ratio,
        kelly_fraction,
    } = actuarial;

    const evColor = expected_value_pips >= 0 ? "#10b981" : "#f43f5e";
    const evStr = `${expected_value_pips >= 0 ? "+" : ""}${expected_value_pips.toFixed(1)} pips`;

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl border border-white/5 bg-white/[0.03] space-y-4"
            data-tour="actuarial-metrics"
        >
            <div className="flex items-center gap-2">
                <Shield className="size-4 text-violet-400" />
                <span className="text-sm font-bold text-white">Actuarial Risk Model</span>
            </div>

            {/* Top KPI row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <KpiTile
                    label="Expected Value"
                    tooltip="Average profit/loss per trade in pips, weighted by probability of winning and losing."
                    value={evStr}
                    color={evColor}
                    icon={TrendingUp}
                />
                <KpiTile
                    label="Prob. Win"
                    tooltip="Estimated probability this trade reaches take-profit before stop-loss."
                    value={`${(probability_win * 100).toFixed(1)}%`}
                    color="#10b981"
                    icon={Target}
                />
                <KpiTile
                    label="Risk / Reward"
                    tooltip="Ratio of average potential gain to average potential loss. Minimum 1.5 required by risk manager."
                    value={`1 : ${risk_reward_ratio.toFixed(2)}`}
                    color={risk_reward_ratio >= 1.5 ? "#10b981" : "#f59e0b"}
                    icon={Scale}
                />
                <KpiTile
                    label="Kelly Fraction"
                    tooltip="Kelly Criterion optimal bet size as a fraction of capital. Half-Kelly applied for conservatism."
                    value={`${(kelly_fraction * 100).toFixed(1)}%`}
                    color="#8b5cf6"
                    icon={Percent}
                />
            </div>

            {/* Progress bars */}
            <div className="space-y-3 pt-1">
                <MetricBar
                    label="Win Probability"
                    tooltip="Probability of a profitable exit before stop-loss."
                    value={probability_win * 100}
                    displayValue={`${(probability_win * 100).toFixed(1)}%`}
                    color="#10b981"
                />
                <MetricBar
                    label="Loss Probability"
                    tooltip="Probability of hitting the stop-loss."
                    value={probability_loss * 100}
                    displayValue={`${(probability_loss * 100).toFixed(1)}%`}
                    color="#f43f5e"
                />
                <MetricBar
                    label="Kelly Sizing"
                    tooltip="Optimal fraction of capital to risk per trade (Kelly Criterion, half-Kelly applied)."
                    value={kelly_fraction * 100}
                    displayValue={`${(kelly_fraction * 100).toFixed(1)}% of capital`}
                    max={5}
                    color="#8b5cf6"
                />
            </div>

            {/* Execution plan if approved */}
            {executionPlan && (
                <div className="pt-3 border-t border-white/5 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                    {[
                        { label: "Position Size", value: `${executionPlan.position_size?.toFixed(2)} lots` },
                        { label: "Risk %",         value: `${executionPlan.risk_pct?.toFixed(2)}%` },
                        { label: "SL (pips)",      value: `${executionPlan.stop_loss_pips?.toFixed(1)}` },
                        { label: "TP (pips)",      value: `${executionPlan.take_profit_pips?.toFixed(1)}` },
                        { label: "Entry",          value: executionPlan.entry_price?.toFixed(5) ?? "—" },
                        { label: "R:R",            value: `1:${risk_reward_ratio.toFixed(2)}` },
                    ].map(({ label, value }) => (
                        <div key={label} className="p-2 rounded-lg bg-white/[0.03] border border-white/5">
                            <p className="text-[10px] text-slate-500">{label}</p>
                            <p className="font-mono font-bold text-white text-sm">{value}</p>
                        </div>
                    ))}
                </div>
            )}
        </motion.div>
    );
}

function Scale(props: React.SVGProps<SVGSVGElement> & { className?: string }) {
    return <TrendingUp {...props} />;
}

interface KpiTileProps {
    label: string;
    tooltip: string;
    value: string;
    color: string;
    icon: React.ElementType;
}

function KpiTile({ label, tooltip, value, color, icon: Icon }: KpiTileProps) {
    return (
        <div className="p-3 rounded-xl border border-white/5 bg-white/[0.02] text-center space-y-1">
            <Icon className="size-3.5 mx-auto" style={{ color }} />
            <p className="text-xs font-bold" style={{ color }}>{value}</p>
            <MetricTooltip label={label} description={tooltip} />
        </div>
    );
}
