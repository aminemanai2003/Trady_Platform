"use client";

import { useState } from "react";
import { useWebSocket } from "./use-websocket";
import type { MasterSignalResponse } from "@/types";

interface UseLiveSignalsReturn {
    /** Latest signal pushed from the backend (null until first push). */
    latestSignal: MasterSignalResponse | null;
    /** Whether the WebSocket connection is currently open. */
    isConnected: boolean;
}

/**
 * Subscribe to live agent pipeline decisions for a given pair.
 *
 * Backend pushes a new message every time MasterSignalView generates a signal.
 *
 * @param pair — e.g. "EURUSD"
 */
export function useLiveSignals(pair: string, enabled = true): UseLiveSignalsReturn {
    const [latestSignal, setLatestSignal] = useState<MasterSignalResponse | null>(null);

    const { isConnected } = useWebSocket(`/ws/signals/${pair}/`, {
        enabled,
        onMessage: (raw) => {
            // Shape from consumer: { type: "signal", data: MasterSignalResponse }
            const msg = raw as { type?: string; data?: MasterSignalResponse };
            if (msg?.data) {
                setLatestSignal(msg.data);
            }
        },
    });

    return { latestSignal, isConnected };
}
