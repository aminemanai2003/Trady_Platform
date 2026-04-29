"use client";

/**
 * DataRefreshProvider
 * Triggers background data refresh (News, OHLCV, Macro) on dashboard load via MCP endpoints.
 * The backend runs collectors in daemon threads and returns 202 immediately — never blocks UI.
 * Respects a minimum interval to avoid hammering on every tab open.
 */

import { useEffect } from "react";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
// Minimum interval between auto-refreshes per source (ms)
const NEWS_INTERVAL_MS = 2 * 60 * 60 * 1000;   // 2 hours
const OHLCV_INTERVAL_MS = 4 * 60 * 60 * 1000;  // 4 hours
const MACRO_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 hours

function triggerRefresh(source: "refresh_news" | "refresh_ohlcv" | "refresh_macro", storageKey: string, intervalMs: number) {
    const lastRefresh = localStorage.getItem(storageKey);
    const now = Date.now();
    if (lastRefresh && now - parseInt(lastRefresh) < intervalMs) {
        return; // Already refreshed recently
    }

    fetch(`${BACKEND}/v2/data/${source}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
    })
        .then((res) => {
            if (res.ok || res.status === 202) {
                localStorage.setItem(storageKey, String(now));
                console.info(`[DataRefresh] ${source} triggered in background`);
            }
        })
        .catch(() => {
            // Silently ignore — backend might be starting up
        });
}

export function DataRefreshProvider({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        triggerRefresh("refresh_news", "lastNewsRefresh", NEWS_INTERVAL_MS);
        triggerRefresh("refresh_ohlcv", "lastOhlcvRefresh", OHLCV_INTERVAL_MS);
        triggerRefresh("refresh_macro", "lastMacroRefresh", MACRO_INTERVAL_MS);
    }, []);

    return <>{children}</>;
}

