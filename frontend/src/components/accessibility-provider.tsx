"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type FontScale = 1 | 1.1 | 1.2 | 1.3;
export type ContrastMode = "default" | "high";

export interface AccessibilityState {
    fontScale: FontScale;
    contrast: ContrastMode;
    reducedMotion: boolean;
    dyslexicFont: boolean;
}

interface AccessibilityContextValue extends AccessibilityState {
    setFontScale: (scale: FontScale) => void;
    setContrast: (mode: ContrastMode) => void;
    setReducedMotion: (enabled: boolean) => void;
    setDyslexicFont: (enabled: boolean) => void;
    resetAccessibility: () => void;
}

const DEFAULTS: AccessibilityState = {
    fontScale: 1,
    contrast: "default",
    reducedMotion: false,
    dyslexicFont: false,
};

const STORAGE_KEY = "trady-accessibility";

const AccessibilityContext = createContext<AccessibilityContextValue | null>(null);

function coerceFontScale(v: unknown): FontScale {
    const n = Number(v);
    if (n === 1 || n === 1.1 || n === 1.2 || n === 1.3) return n;
    return DEFAULTS.fontScale;
}

function coerceContrast(v: unknown): ContrastMode {
    if (v === "high" || v === "default") return v;
    return DEFAULTS.contrast;
}

function loadFromStorage(): AccessibilityState {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return DEFAULTS;
        const parsed = JSON.parse(raw) as Partial<AccessibilityState>;
        return {
            fontScale: coerceFontScale(parsed.fontScale),
            contrast: coerceContrast(parsed.contrast),
            reducedMotion: Boolean(parsed.reducedMotion),
            dyslexicFont: Boolean(parsed.dyslexicFont),
        };
    } catch {
        return DEFAULTS;
    }
}

function persist(next: AccessibilityState) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
        // ignore storage failures
    }
}

function applyToDom(state: AccessibilityState) {
    const root = document.documentElement;

    root.dataset.contrast = state.contrast;

    if (state.reducedMotion) {
        root.classList.add("reduce-motion");
    } else {
        root.classList.remove("reduce-motion");
    }

    if (state.dyslexicFont) {
        root.classList.add("dyslexic-font");
    } else {
        root.classList.remove("dyslexic-font");
    }

    const basePx = 16;
    root.style.fontSize = `${Math.round(basePx * state.fontScale)}px`;
}

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
    const [state, setState] = useState<AccessibilityState>(() => {
        if (typeof window === "undefined") return DEFAULTS;
        return loadFromStorage();
    });

    useEffect(() => {
        persist(state);
        applyToDom(state);
    }, [state]);

    const value = useMemo<AccessibilityContextValue>(
        () => ({
            ...state,
            setFontScale: (fontScale) => setState((s) => ({ ...s, fontScale })),
            setContrast: (contrast) => setState((s) => ({ ...s, contrast })),
            setReducedMotion: (reducedMotion) => setState((s) => ({ ...s, reducedMotion })),
            setDyslexicFont: (dyslexicFont) => setState((s) => ({ ...s, dyslexicFont })),
            resetAccessibility: () => setState(DEFAULTS),
        }),
        [state]
    );

    return <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>;
}

export function useAccessibility() {
    const ctx = useContext(AccessibilityContext);
    if (!ctx) {
        throw new Error("useAccessibility must be used within AccessibilityProvider");
    }
    return ctx;
}
