"use client";

import { useEffect, useRef, useCallback, useState } from "react";

const WS_BASE =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) ||
    "ws://localhost:8000";

const RECONNECT_BASE_MS = 1_500;
const RECONNECT_MAX_MS = 30_000;

interface UseWebSocketOptions {
    /** Whether to auto-connect on mount. Defaults to true. */
    enabled?: boolean;
    /** Called when a message arrives (already parsed from JSON if possible). */
    onMessage: (data: unknown) => void;
    /** Called on connection establishment. */
    onOpen?: () => void;
    /** Called on connection close. */
    onClose?: () => void;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    /** Send a JSON-serializable object to the server. */
    send: (data: unknown) => void;
    /** Force close the connection (will NOT reconnect). */
    close: () => void;
}

/**
 * Generic persistent WebSocket hook with exponential-backoff reconnection.
 *
 * @param path  — relative WS path, e.g. "/ws/signals/EURUSD/"
 */
export function useWebSocket(
    path: string,
    { enabled = true, onMessage, onOpen, onClose }: UseWebSocketOptions
): UseWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const retryDelayRef = useRef(RECONNECT_BASE_MS);
    const shouldReconnect = useRef(true);

    const onMessageRef = useRef(onMessage);
    const onOpenRef = useRef(onOpen);
    const onCloseRef = useRef(onClose);
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;

    const connect = useCallback(() => {
        if (!enabled || typeof window === "undefined") return;

        shouldReconnect.current = true;
        const url = `${WS_BASE}${path}`;

        try {
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                retryDelayRef.current = RECONNECT_BASE_MS;
                onOpenRef.current?.();
            };

            ws.onmessage = (e) => {
                try {
                    const parsed = JSON.parse(e.data as string);
                    onMessageRef.current(parsed);
                } catch {
                    onMessageRef.current(e.data);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                onCloseRef.current?.();
                if (shouldReconnect.current) {
                    retryRef.current = setTimeout(() => {
                        retryDelayRef.current = Math.min(
                            retryDelayRef.current * 2,
                            RECONNECT_MAX_MS
                        );
                        connect();
                    }, retryDelayRef.current);
                }
            };

            ws.onerror = () => {
                ws.close();
            };
        } catch {
            // WebSocket not available (SSR) — skip silently
        }
    }, [path, enabled]);

    const close = useCallback(() => {
        shouldReconnect.current = false;
        if (retryRef.current) clearTimeout(retryRef.current);
        wsRef.current?.close();
    }, []);

    const send = useCallback((data: unknown) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
        }
    }, []);

    useEffect(() => {
        connect();
        return () => {
            shouldReconnect.current = false;
            if (retryRef.current) clearTimeout(retryRef.current);
            wsRef.current?.close();
        };
    }, [connect]);

    return { isConnected, send, close };
}
