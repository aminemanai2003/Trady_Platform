"use client";

import { useEffect, useRef, memo } from "react";

interface TradingViewWidgetProps {
    symbol: string;
    interval?: string;
    theme?: "light" | "dark";
    height?: number;
}

function TradingViewWidget({
    symbol,
    interval = "240",
    theme = "dark",
    height = 500,
}: TradingViewWidgetProps) {
    const container = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!container.current) return;

        // Clear previous widget
        container.current.innerHTML = "";

        const script = document.createElement("script");
        script.src = "https://s3.tradingview.com/tv.js";
        script.type = "text/javascript";
        script.async = true;
        script.onload = () => {
            if (typeof window.TradingView !== "undefined" && container.current) {
                new window.TradingView.widget({
                    autosize: false,
                    width: "100%",
                    height: height,
                    symbol: `FX_IDC:${symbol}`,
                    interval: interval,
                    timezone: "Etc/UTC",
                    theme: theme,
                    style: "1",
                    locale: "en",
                    toolbar_bg: theme === "dark" ? "#0a1929" : "#f1f3f6",
                    enable_publishing: false,
                    hide_side_toolbar: false,
                    allow_symbol_change: false,
                    details: true,
                    hotlist: true,
                    calendar: true,
                    studies: [
                        "RSI@tv-basicstudies",
                        "MASimple@tv-basicstudies",
                        "MACD@tv-basicstudies",
                        "BB@tv-basicstudies",
                    ],
                    container_id: container.current.id,
                    hide_top_toolbar: false,
                    hide_legend: false,
                    save_image: false,
                });
            }
        };
        container.current.appendChild(script);

        return () => {
            if (container.current) {
                container.current.innerHTML = "";
            }
        };
    }, [symbol, interval, theme, height]);

    return (
        <div
            ref={container}
            id={`tradingview_${symbol}_${Date.now()}`}
            className="rounded-lg overflow-hidden border border-slate-700/50"
        />
    );
}

export default memo(TradingViewWidget);

// Declare TradingView on window
declare global {
    interface Window {
        TradingView: any;
    }
}

