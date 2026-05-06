"use client";

/**
 * DataRefreshProvider
 * Triggers a background news-data refresh every time the dashboard loads.
 * The backend runs the scraper in a daemon thread and returns 202 immediately,
 * so this never blocks the UI.
 */

import { useEffect } from "react";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
// Minimum interval between refreshes (ms) — avoids hammering on every tab open
const MIN_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function DataRefreshProvider({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        const lastRefresh = localStorage.getItem("lastNewsRefresh");
        const now = Date.now();

        if (lastRefresh && now - parseInt(lastRefresh) < MIN_INTERVAL_MS) {
            return; // Already refreshed recently
        }

        // Fire-and-forget: POST to refresh endpoint
        fetch(`${BACKEND}/api/v2/data/refresh_news/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        })
            .then((res) => {
                if (res.ok || res.status === 202) {
                    localStorage.setItem("lastNewsRefresh", String(now));
                    console.info("[DataRefresh] News refresh triggered in background ✓");
                }
            })
            .catch(() => {
                // Silently ignore — backend might be starting up
            });
    }, []);

    return <>{children}</>;
}
