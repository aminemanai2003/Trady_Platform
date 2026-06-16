"use client";

import { useState } from "react";
import { useWebSocket } from "./use-websocket";
import type { PriceTick } from "@/types";

interface UseLivePricesReturn {
    latestPrice: PriceTick | null;
    isConnected: boolean;
}

/**
 * Subscribe to live price ticks for a given pair.
 * The backend pushes a tick every ~5 seconds via the price_broadcaster job.
 *
 * @param pair — e.g. "EURUSD"
 */
export function useLivePrices(pair: string, enabled = true): UseLivePricesReturn {
    const [latestPrice, setLatestPrice] = useState<PriceTick | null>(null);

    const { isConnected } = useWebSocket(`/ws/prices/${pair}/`, {
        enabled,
        onMessage: (raw) => {
            // Shape from consumer: { type: "price", data: PriceTick }
            const msg = raw as { type?: string; data?: PriceTick };
            if (msg?.data) {
                setLatestPrice(msg.data);
            }
        },
    });

    return { latestPrice, isConnected };
}
