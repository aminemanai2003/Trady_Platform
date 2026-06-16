import React from "react";
import { cn } from "@/lib/utils";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
    size?: "xs" | "sm" | "md" | "lg";
    label?: string;
}

export function Spinner({ size = "md", label = "Loading…", className = "", ...props }: SpinnerProps) {
    const sizeClass = {
        xs: "size-3 border-[1.5px]",
        sm: "size-4 border-2",
        md: "size-6 border-2",
        lg: "size-8 border-[3px]",
    }[size];

    return (
        <div
            role="status"
            aria-label={label}
            className={cn("inline-flex items-center justify-center", className)}
            {...props}
        >
            <span
                aria-hidden="true"
                className={cn(
                    "rounded-full border-current border-t-transparent animate-spin",
                    sizeClass
                )}
            />
            <span className="sr-only">{label}</span>
        </div>
    );
}

