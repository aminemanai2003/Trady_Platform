/* API client + React Query hooks for the Django backend. */
import type {
    CandleData,
    TradingSignal,
    AgentStatusResponse,
    KpiScorecard,
    TechnicalAnalysis,
    EconomicEvent,
    DailyPerformance,
    FreshnessHealthV2,
    ReportSummaryResponse,
    MasterSignalResponse,
    PaperPosition,
    PortfolioStats,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchWithTimeout(input: string, init: RequestInit = {}, timeoutMs = 15000): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        return await fetch(input, {
            ...init,
            signal: controller.signal,
        });
    } finally {
        clearTimeout(timeoutId);
    }
}

export class ApiRequestError extends Error {
    status?: number;

    constructor(message: string, status?: number) {
        super(message);
        this.name = "ApiRequestError";
        this.status = status;
    }
}

async function fetcher<T>(url: string): Promise<T> {
    const res = await fetchWithTimeout(`${API_BASE}${url}`, { cache: "no-store" }, 15000);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// â”€â”€â”€ API Functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export const api = {
    prices: (pair: string, timeframe = "1D", limit = 200) =>
        fetcher<CandleData[]>(`/prices/${pair}/?timeframe=${timeframe}&limit=${limit}`),

    latestSignals: () =>
        fetcher<TradingSignal[]>("/signals/latest/"),

    agentStatus: () =>
        fetcher<AgentStatusResponse>("/agents/status/"),

    kpis: () =>
        fetcher<KpiScorecard>("/kpis/"),

    performance: () =>
        fetcher<DailyPerformance[]>("/analytics/performance/"),

    reportsSummary: (pair = "all", days = 90) =>
        fetcher<ReportSummaryResponse>(`/analytics/reports/summary/?pair=${encodeURIComponent(pair)}&days=${days}`),

    reportsExportUrl: (pair = "all", days = 90) =>
        `${API_BASE}/analytics/reports/export/?pair=${encodeURIComponent(pair)}&days=${days}`,

    technicals: (pair: string) =>
        fetcher<TechnicalAnalysis>(`/technicals/${pair}/`),

    calendar: () =>
        fetcher<EconomicEvent[]>("/calendar/"),

    news: () =>
        fetcher<{ results: Array<{ title: string; source: string; published_at: string }> }>("/news/"),

    triggerAgents: (pair: string) =>
        fetch(`${API_BASE}/agents/run/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pair }),
        }).then((r) => r.json()),

    // V2 Architecture Endpoints
    v2: {
        generateSignal: async (pair: string) => {
            try {
                const response = await fetchWithTimeout(
                    `${API_BASE}/v2/signals/generate_signal/`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        cache: "no-store",
                        body: JSON.stringify({ pair }),
                    },
                    180000
                );

                if (!response.ok) {
                    let backendMessage = "";
                    try {
                        const payload = await response.json();
                        backendMessage = payload?.error || payload?.reason || "";
                    } catch {
                        // Ignore non-JSON error responses
                    }

                    const detail = backendMessage
                        ? ` (${backendMessage})`
                        : "";
                    throw new ApiRequestError(
                        `Signal generation failed (HTTP ${response.status})${detail}.`,
                        response.status
                    );
                }

                return response.json();
            } catch (error) {
                if (error instanceof ApiRequestError) {
                    throw error;
                }

                if (error instanceof DOMException && error.name === "AbortError") {
                    throw new ApiRequestError(
                        "Signal generation took too long (3-minute timeout). Please try again.",
                    );
                }

                const details = error instanceof Error ? ` (${error.message})` : "";
                throw new ApiRequestError(
                    `Unable to connect to the backend. Make sure the Django API is running on port 8000 and CORS is configured.${details}`,
                );
            }
        },

        agentPerformance: () =>
            fetcher(`/v2/monitoring/agent_performance/`),

        healthCheck: () =>
            fetcher(`/v2/monitoring/health_check/`),

        driftDetection: () =>
            fetcher(`/v2/monitoring/drift_detection/`),

        freshnessHealth: () =>
            fetcher<FreshnessHealthV2>(`/v2/monitoring/freshness_health/`),  // targets set server-side (news 2880m, macro/ohlcv 10080m)
    },

    // ─── Master Unified Pipeline ─────────────────────────────────────────────
    generateMaster: async (
        pair: string,
        options: { capital?: number; currentEquity?: number; currentPositions?: number } = {}
    ): Promise<MasterSignalResponse> => {
        const { capital = 10_000, currentEquity, currentPositions = 0 } = options;
        try {
            const response = await fetchWithTimeout(
                `${API_BASE}/v2/master/generate/`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    cache: "no-store",
                    body: JSON.stringify({
                        pair,
                        capital,
                        current_equity: currentEquity ?? capital,
                        current_positions: currentPositions,
                    }),
                },
                180_000 // 3-minute timeout
            );

            if (!response.ok) {
                let msg = "";
                try {
                    const payload = await response.json();
                    msg = payload?.error || payload?.reason || "";
                } catch { /* ignore */ }
                throw new ApiRequestError(
                    `Master signal failed (HTTP ${response.status})${msg ? ` — ${msg}` : ""}.`,
                    response.status
                );
            }
            return response.json();
        } catch (error) {
            if (error instanceof ApiRequestError) throw error;
            if (error instanceof DOMException && error.name === "AbortError") {
                throw new ApiRequestError("Signal generation timed out (3 min). Please retry.");
            }
            const details = error instanceof Error ? ` (${error.message})` : "";
            throw new ApiRequestError(
                `Cannot reach backend. Ensure Django runs on port 8000 with CORS enabled.${details}`
            );
        }
    },

    // ─── Data Ingestion ───────────────────────────────────────────────────────
    dataIngest: {
        refreshNews: () =>
            fetchWithTimeout(`${API_BASE}/v2/data/refresh_news/`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
            }, 10000).then((r) => r.json()),

        refreshOhlcv: () =>
            fetchWithTimeout(`${API_BASE}/v2/data/refresh_ohlcv/`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
            }, 10000).then((r) => r.json()),

        refreshMacro: () =>
            fetchWithTimeout(`${API_BASE}/v2/data/refresh_macro/`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
            }, 10000).then((r) => r.json()),

        status: () =>
            fetcher<{
                sources: Record<string, { running: boolean; last_run: string | null; last_result: unknown }>;
                db_last_success: Record<string, string | null>;
            }>(`/v2/data/status/`),
    },

    // ─── Paper Trading ────────────────────────────────────────────────────────
    paperTrading: {
        getPositions: () =>
            fetcher<PaperPosition[]>("/v2/paper-trading/positions/"),

        openPosition: (data: {
            pair: string; side: "BUY" | "SELL"; size: number;
            entry_price: number; stop_loss?: number; take_profit?: number;
        }) =>
            fetchWithTimeout(`${API_BASE}/v2/paper-trading/positions/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            }).then((r) => r.json()),

        closePosition: (id: number, closePrice?: number) =>
            fetchWithTimeout(`${API_BASE}/v2/paper-trading/positions/${id}/`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(closePrice != null ? { close_price: closePrice } : {}),
            }).then((r) => r.json()),

        getHistory: (limit = 100) =>
            fetcher<PaperPosition[]>(`/v2/paper-trading/history/?limit=${limit}`),

        getStats: () =>
            fetcher<PortfolioStats>("/v2/paper-trading/stats/"),
    },
};

// â”€â”€â”€ Custom Hooks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// These can be used with React Query (already installed):
//
//   import { useQuery } from "@tanstack/react-query";
//   const { data } = useQuery({ queryKey: ["prices", pair], queryFn: () => api.prices(pair) });
//
// For now, pages use mock data with optional API overlay.

