"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

export type FontScale = 1 | 1.1 | 1.2 | 1.3;
export type ContrastMode = "default" | "high";
export type ColorBlindMode = "none" | "deuteranopia" | "protanopia" | "tritanopia";
export type CursorSize = "default" | "large" | "x-large";
export type LineSpacing = "default" | "relaxed" | "loose";

export interface AccessibilityState {
    fontScale: FontScale;
    contrast: ContrastMode;
    reducedMotion: boolean;
    dyslexicFont: boolean;
    textToSpeech: boolean;
    colorBlindMode: ColorBlindMode;
    cursorSize: CursorSize;
    highlightLinks: boolean;
    lineSpacing: LineSpacing;
}

interface AccessibilityContextValue extends AccessibilityState {
    setFontScale: (scale: FontScale) => void;
    setContrast: (mode: ContrastMode) => void;
    setReducedMotion: (enabled: boolean) => void;
    setDyslexicFont: (enabled: boolean) => void;
    setTextToSpeech: (enabled: boolean) => void;
    setColorBlindMode: (mode: ColorBlindMode) => void;
    setCursorSize: (size: CursorSize) => void;
    setHighlightLinks: (enabled: boolean) => void;
    setLineSpacing: (spacing: LineSpacing) => void;
    resetAccessibility: () => void;
    /** Speak a string immediately (respects textToSpeech toggle) */
    speak: (text: string) => void;
    /** Stop any current speech */
    stopSpeech: () => void;
    /** Whether speech is currently playing */
    isSpeaking: boolean;
}

const DEFAULTS: AccessibilityState = {
    fontScale: 1,
    contrast: "default",
    reducedMotion: false,
    dyslexicFont: false,
    textToSpeech: false,
    colorBlindMode: "none",
    cursorSize: "default",
    highlightLinks: false,
    lineSpacing: "default",
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

function coerceColorBlind(v: unknown): ColorBlindMode {
    if (v === "none" || v === "deuteranopia" || v === "protanopia" || v === "tritanopia") return v;
    return DEFAULTS.colorBlindMode;
}

function coerceCursorSize(v: unknown): CursorSize {
    if (v === "default" || v === "large" || v === "x-large") return v;
    return DEFAULTS.cursorSize;
}

function coerceLineSpacing(v: unknown): LineSpacing {
    if (v === "default" || v === "relaxed" || v === "loose") return v;
    return DEFAULTS.lineSpacing;
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
            textToSpeech: Boolean(parsed.textToSpeech),
            colorBlindMode: coerceColorBlind(parsed.colorBlindMode),
            cursorSize: coerceCursorSize(parsed.cursorSize),
            highlightLinks: Boolean(parsed.highlightLinks),
            lineSpacing: coerceLineSpacing(parsed.lineSpacing),
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

const COLOR_BLIND_CLASSES: Record<ColorBlindMode, string> = {
    none: "",
    deuteranopia: "cb-deuteranopia",
    protanopia: "cb-protanopia",
    tritanopia: "cb-tritanopia",
};

const CURSOR_SIZE_CLASSES: Record<CursorSize, string> = {
    default: "",
    large: "cursor-large",
    "x-large": "cursor-x-large",
};

const LINE_SPACING_CLASSES: Record<LineSpacing, string> = {
    default: "",
    relaxed: "line-spacing-relaxed",
    loose: "line-spacing-loose",
};

function applyToDom(state: AccessibilityState) {
    const root = document.documentElement;

    // Contrast
    root.dataset.contrast = state.contrast;

    // Reduced motion
    root.classList.toggle("reduce-motion", state.reducedMotion);

    // Dyslexic font
    root.classList.toggle("dyslexic-font", state.dyslexicFont);

    // Color blind modes (remove all, then add active)
    for (const cls of ["cb-deuteranopia", "cb-protanopia", "cb-tritanopia"]) {
        root.classList.remove(cls);
    }
    const cbClass = COLOR_BLIND_CLASSES[state.colorBlindMode];
    if (cbClass) root.classList.add(cbClass);

    // Cursor size (remove all, then add active)
    for (const cls of ["cursor-large", "cursor-x-large"]) {
        root.classList.remove(cls);
    }
    const cursorClass = CURSOR_SIZE_CLASSES[state.cursorSize];
    if (cursorClass) root.classList.add(cursorClass);

    // Highlight links
    root.classList.toggle("highlight-links", state.highlightLinks);

    // Line spacing (remove all, then add active)
    for (const cls of ["line-spacing-relaxed", "line-spacing-loose"]) {
        root.classList.remove(cls);
    }
    const spacingClass = LINE_SPACING_CLASSES[state.lineSpacing];
    if (spacingClass) root.classList.add(spacingClass);

    // Font size
    const basePx = 16;
    root.style.fontSize = `${Math.round(basePx * state.fontScale)}px`;
}

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
    const [state, setState] = useState<AccessibilityState>(() => {
        if (typeof window === "undefined") return DEFAULTS;
        return loadFromStorage();
    });

    const [isSpeaking, setIsSpeaking] = useState(false);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    useEffect(() => {
        persist(state);
        applyToDom(state);
    }, [state]);

    // TTS: read selected text on mouseup when enabled
    useEffect(() => {
        if (!state.textToSpeech) return;

        function handleSelection() {
            const sel = window.getSelection()?.toString().trim();
            if (sel && sel.length > 1) {
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(sel);
                utter.lang = "en-US";
                utter.rate = 0.95;
                utter.onstart = () => setIsSpeaking(true);
                utter.onend = () => setIsSpeaking(false);
                utter.onerror = () => setIsSpeaking(false);
                utteranceRef.current = utter;
                window.speechSynthesis.speak(utter);
            }
        }

        document.addEventListener("mouseup", handleSelection);
        return () => {
            document.removeEventListener("mouseup", handleSelection);
            window.speechSynthesis.cancel();
        };
    }, [state.textToSpeech]);

    const speak = useCallback((text: string) => {
        if (typeof window === "undefined" || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = "en-US";
        utter.rate = 0.95;
        utter.onstart = () => setIsSpeaking(true);
        utter.onend = () => setIsSpeaking(false);
        utter.onerror = () => setIsSpeaking(false);
        utteranceRef.current = utter;
        window.speechSynthesis.speak(utter);
    }, []);

    const stopSpeech = useCallback(() => {
        if (typeof window === "undefined" || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
    }, []);

    const value = useMemo<AccessibilityContextValue>(
        () => ({
            ...state,
            isSpeaking,
            setFontScale: (fontScale) => setState((s) => ({ ...s, fontScale })),
            setContrast: (contrast) => setState((s) => ({ ...s, contrast })),
            setReducedMotion: (reducedMotion) => setState((s) => ({ ...s, reducedMotion })),
            setDyslexicFont: (dyslexicFont) => setState((s) => ({ ...s, dyslexicFont })),
            setTextToSpeech: (textToSpeech) => setState((s) => ({ ...s, textToSpeech })),
            setColorBlindMode: (colorBlindMode) => setState((s) => ({ ...s, colorBlindMode })),
            setCursorSize: (cursorSize) => setState((s) => ({ ...s, cursorSize })),
            setHighlightLinks: (highlightLinks) => setState((s) => ({ ...s, highlightLinks })),
            setLineSpacing: (lineSpacing) => setState((s) => ({ ...s, lineSpacing })),
            resetAccessibility: () => setState(DEFAULTS),
            speak,
            stopSpeech,
        }),
        [state, isSpeaking, speak, stopSpeech]
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
