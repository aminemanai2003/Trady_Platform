import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

const alertVariants = cva(
    "relative flex items-start gap-3 rounded-xl border p-4 text-sm animate-fade-in",
    {
        variants: {
            variant: {
                info:        "border-brand-blue-500/30  bg-brand-blue-500/8  text-brand-blue-300",
                success:     "border-brand-green-500/30 bg-brand-green-500/8 text-brand-green-300",
                error:       "border-rose-500/30        bg-rose-500/8        text-rose-300",
                warning:     "border-amber-500/30       bg-amber-500/8       text-amber-300",
                destructive: "border-destructive/30     bg-destructive/8     text-destructive",
            },
        },
        defaultVariants: {
            variant: "info",
        },
    }
);

const ICONS = {
    info:        Info,
    success:     CheckCircle2,
    error:       AlertCircle,
    warning:     TriangleAlert,
    destructive: AlertCircle,
} as const;

interface AlertProps
    extends React.HTMLAttributes<HTMLDivElement>,
        VariantProps<typeof alertVariants> {
    /** If provided, renders a close button */
    onClose?: () => void;
    icon?: React.ReactNode;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
    ({ className, variant = "info", onClose, icon, children, ...props }, ref) => {
        const Icon = ICONS[variant ?? "info"];

        return (
            <div
                ref={ref}
                role="alert"
                aria-live="polite"
                className={cn(alertVariants({ variant }), className)}
                {...props}
            >
                <span aria-hidden="true" className="mt-0.5 shrink-0">
                    {icon ?? <Icon className="size-4" />}
                </span>
                <div className="flex-1 min-w-0">{children}</div>
                {onClose && (
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Dismiss alert"
                        className="shrink-0 rounded-md p-0.5 opacity-60 hover:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-current"
                    >
                        <X className="size-3.5" />
                    </button>
                )}
            </div>
        );
    }
);
Alert.displayName = "Alert";

const AlertTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
    ({ className, ...props }, ref) => (
        <p ref={ref} className={cn("font-semibold leading-none mb-1", className)} {...props} />
    )
);
AlertTitle.displayName = "AlertTitle";

const AlertDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
    ({ className, ...props }, ref) => (
        <p ref={ref} className={cn("text-xs leading-relaxed opacity-85", className)} {...props} />
    )
);
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription };
