import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const rbButtonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue-500/40 disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      variant: {
        primary:   "bg-brand-blue-600 text-white hover:bg-brand-blue-500 active:scale-[0.97] shadow-sm hover:shadow-brand-blue-500/20 hover:shadow-md",
        secondary: "bg-secondary text-secondary-foreground hover:bg-accent border border-border active:scale-[0.97]",
        ghost:     "text-foreground hover:bg-accent active:scale-[0.97]",
        danger:    "bg-rose-600 text-white hover:bg-rose-500 active:scale-[0.97]",
        success:   "bg-brand-green-600 text-white hover:bg-brand-green-500 active:scale-[0.97]",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface RBButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof rbButtonVariants> {}

export function RBButton({ className, variant, size, ...props }: RBButtonProps) {
  return <button className={cn(rbButtonVariants({ variant, size }), className)} {...props} />;
}

export function RBCard({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card/80 text-card-foreground backdrop-blur-sm shadow-[0_8px_30px_rgba(2,6,23,0.16)] dark:shadow-[0_8px_30px_rgba(2,6,23,0.45)]",
        className
      )}
      {...props}
    />
  );
}

export function RBInput({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-xl border border-input bg-background/80 px-3 text-sm text-foreground placeholder:text-muted-foreground",
        "focus:outline-none focus:ring-2 focus:ring-brand-blue-500/35 focus:border-brand-blue-500/60",
        "aria-invalid:ring-rose-500/30 aria-invalid:border-rose-500/60",
        "transition-[border-color,box-shadow] duration-150",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className
      )}
      {...props}
    />
  );
}

export function RBLabel({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("mb-1.5 block text-sm font-medium text-muted-foreground", className)} {...props} />;
}

export function RBPage({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "min-h-screen bg-background text-foreground",
        className
      )}
      {...props}
    />
  );
}
