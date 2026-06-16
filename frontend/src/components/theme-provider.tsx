"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

type ThemeMode = "dark" | "light";

type ThemeContextValue = {
    theme: ThemeMode;
    setTheme: (theme: ThemeMode) => void;
    toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyTheme(theme: ThemeMode) {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setThemeState] = useState<ThemeMode>("dark");
    const pathname = usePathname();
    const isLandingPage = pathname === "/";

    useEffect(() => {
        const stored = window.localStorage.getItem("trady-theme");
        const nextTheme: ThemeMode = stored === "light" ? "light" : "dark";
        setThemeState(nextTheme);
    }, []);

    useEffect(() => {
        applyTheme(isLandingPage ? "dark" : theme);
    }, [isLandingPage, theme]);

    const value = useMemo<ThemeContextValue>(() => ({
        theme,
        setTheme(nextTheme) {
            window.localStorage.setItem("trady-theme", nextTheme);
            setThemeState(nextTheme);
        },
        toggleTheme() {
            const nextTheme = theme === "dark" ? "light" : "dark";
            window.localStorage.setItem("trady-theme", nextTheme);
            setThemeState(nextTheme);
        },
    }), [theme]);

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
    const value = useContext(ThemeContext);
    if (!value) {
        throw new Error("useTheme must be used inside ThemeProvider");
    }
    return value;
}
