"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

export function ThemeToggle({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === "dark";

    return (
        <button
            type="button"
            onClick={toggleTheme}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            className={`inline-flex items-center justify-center gap-2 rounded-lg text-sm text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-white ${compact ? "size-8" : "px-2.5 py-2"} ${className}`}
        >
            {isDark ? <Moon className="size-4" /> : <Sun className="size-4 text-amber-500" />}
            {!compact && <span className="text-xs">{isDark ? "Dark mode" : "Light mode"}</span>}
        </button>
    );
}
