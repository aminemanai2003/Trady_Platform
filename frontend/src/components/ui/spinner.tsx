import React from "react";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
    size?: "sm" | "md" | "lg";
}

export function Spinner({ size = "md", className = "", ...props }: SpinnerProps) {
    const sizeClass = {
        sm: "size-4",
        md: "size-6",
        lg: "size-8",
    }[size];

    return (
        <div
            className={`animate-spin rounded-full border-2 border-current border-t-transparent ${sizeClass} ${className}`}
            {...props}
        />
    );
}

