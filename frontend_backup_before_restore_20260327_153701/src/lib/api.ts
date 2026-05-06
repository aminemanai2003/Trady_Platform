/* API client + React Query hooks for the Django backend. */
import type {
    CandleData,
    TradingSignal,
    AgentStatusResponse,
    KpiScorecard,
    TechnicalAnalysis,
    EconomicEvent,
    DailyPerformance,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetcher<T>(url: string): Promise<T> {
    const res = await fetch(`${API_BASE}${url}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// ─── API Functions ────────────────────────────
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
        generateSignal: (pair: string) =>
            fetch(`${API_BASE}/v2/signals/generate_signal/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pair }),
            }).then((r) => r.json()),

        agentPerformance: () =>
            fetcher(`/v2/monitoring/agent_performance/`),

        healthCheck: () =>
            fetcher(`/v2/monitoring/health_check/`),

        driftDetection: () =>
            fetcher(`/v2/monitoring/drift_detection/`),
    },
};

// ─── Custom Hooks ─────────────────────────────
// These can be used with React Query (already installed):
//
//   import { useQuery } from "@tanstack/react-query";
//   const { data } = useQuery({ queryKey: ["prices", pair], queryFn: () => api.prices(pair) });
//
// For now, pages use mock data with optional API overlay.
