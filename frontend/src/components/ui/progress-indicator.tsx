import * as React from "react";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface ProgressIndicatorProps {
    currentStep: number;
    totalSteps: number;
    /** "numbers" renders step circles with numbers, "dots" renders condensed dots */
    type?: "numbers" | "dots";
    /** Show step labels below each step (only for numbers type) */
    showLabels?: boolean;
    labels?: string[];
    className?: string;
}

const DEFAULT_LABELS = ["Account", "Security", "Verify"];

export function ProgressIndicator({
    currentStep,
    totalSteps,
    type = "numbers",
    showLabels = false,
    labels,
    className,
}: ProgressIndicatorProps) {
    const stepLabels = labels ?? DEFAULT_LABELS.slice(0, totalSteps);

    if (type === "dots") {
        return (
            <div className={cn("flex items-center gap-2", className)}>
                {Array.from({ length: totalSteps }, (_, i) => {
                    const step = i + 1;
                    const isDone    = step < currentStep;
                    const isActive  = step === currentStep;
                    return (
                        <span
                            key={step}
                            aria-label={`Step ${step} of ${totalSteps}${isDone ? " — completed" : isActive ? " — current" : ""}`}
                            className={cn(
                                "rounded-full transition-all duration-300",
                                isDone   && "size-2.5 bg-brand-green-500",
                                isActive && "size-3 bg-brand-blue-500",
                                !isDone && !isActive && "size-2 bg-white/20"
                            )}
                        />
                    );
                })}
            </div>
        );
    }

    return (
        <div className={cn("flex items-center", className)} role="list" aria-label="Progress">
            {Array.from({ length: totalSteps }, (_, i) => {
                const step      = i + 1;
                const isDone    = step < currentStep;
                const isActive  = step === currentStep;
                const isUpcoming = step > currentStep;
                const isLast    = step === totalSteps;

                return (
                    <React.Fragment key={step}>
                        <div
                            role="listitem"
                            aria-current={isActive ? "step" : undefined}
                            className="flex flex-col items-center gap-1"
                        >
                            {/* circle */}
                            <span
                                className={cn(
                                    "flex size-9 items-center justify-center rounded-full border-2 text-sm font-bold transition-all duration-300",
                                    isDone   && "border-brand-blue-600 bg-brand-blue-600 text-white",
                                    isActive && "border-brand-blue-500 bg-brand-blue-500/15 text-brand-blue-400 shadow-[0_0_0_3px_oklch(0.50_0.190_258/20%)]",
                                    isUpcoming && "border-white/15 bg-transparent text-white/30"
                                )}
                            >
                                {isDone ? (
                                    <Check className="size-4" strokeWidth={2.5} />
                                ) : (
                                    <span>{step}</span>
                                )}
                            </span>

                            {/* label */}
                            {showLabels && stepLabels[i] && (
                                <span
                                    className={cn(
                                        "text-[10px] font-medium transition-colors",
                                        isDone    && "text-brand-blue-400",
                                        isActive  && "text-brand-blue-300",
                                        isUpcoming && "text-white/25"
                                    )}
                                >
                                    {stepLabels[i]}
                                </span>
                            )}
                        </div>

                        {/* connector line */}
                        {!isLast && (
                            <span
                                aria-hidden="true"
                                className={cn(
                                    "mb-4 h-0.5 flex-1 mx-1 rounded-full transition-all duration-500",
                                    step < currentStep
                                        ? "bg-brand-blue-600"
                                        : "bg-white/10"
                                )}
                            />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}
