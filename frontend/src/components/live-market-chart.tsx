"use client";

import {
    CandlestickSeries,
    ColorType,
    createChart,
    HistogramSeries,
    LineSeries,
    type IChartApi,
    type Time,
} from "lightweight-charts";
import {
    forwardRef,
    useEffect,
    useImperativeHandle,
    useRef,
} from "react";

export type MarketCandle = {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
};

export type LiveMarketChartHandle = {
    capture: () => string | null;
    download: (filename: string) => void;
};

function ema(candles: MarketCandle[], period: number) {
    const multiplier = 2 / (period + 1);
    let current = candles[0]?.close ?? 0;
    return candles.map((candle, index) => {
        current = index === 0 ? candle.close : (candle.close - current) * multiplier + current;
        return { time: candle.time as Time, value: current };
    });
}

export const LiveMarketChart = forwardRef<
    LiveMarketChartHandle,
    { candles: MarketCandle[]; height?: number }
>(function LiveMarketChart({ candles, height = 520 }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useImperativeHandle(ref, () => ({
        capture() {
            return chartRef.current?.takeScreenshot().toDataURL("image/png") ?? null;
        },
        download(filename: string) {
            const dataUrl = chartRef.current?.takeScreenshot().toDataURL("image/png");
            if (!dataUrl) return;
            const anchor = document.createElement("a");
            anchor.href = dataUrl;
            anchor.download = filename;
            anchor.click();
        },
    }));

    useEffect(() => {
        const container = containerRef.current;
        if (!container || candles.length === 0) return;

        const dark = document.documentElement.classList.contains("dark");
        const chart = createChart(container, {
            width: container.clientWidth,
            height,
            layout: {
                background: { type: ColorType.Solid, color: dark ? "#090d15" : "#ffffff" },
                textColor: dark ? "#9aa7bd" : "#526176",
                attributionLogo: false,
            },
            grid: {
                vertLines: { color: dark ? "#172033" : "#e8edf5" },
                horzLines: { color: dark ? "#172033" : "#e8edf5" },
            },
            rightPriceScale: { borderColor: dark ? "#253047" : "#d8e0ec" },
            timeScale: {
                borderColor: dark ? "#253047" : "#d8e0ec",
                timeVisible: true,
                secondsVisible: false,
            },
            crosshair: {
                vertLine: { color: "#4f8cff", labelBackgroundColor: "#1554c4" },
                horzLine: { color: "#4f8cff", labelBackgroundColor: "#1554c4" },
            },
        });
        chartRef.current = chart;

        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: "#16c79a",
            downColor: "#ef5b78",
            wickUpColor: "#16c79a",
            wickDownColor: "#ef5b78",
            borderVisible: false,
        });
        candleSeries.setData(candles.map((candle) => ({ ...candle, time: candle.time as Time })));

        const volumeSeries = chart.addSeries(HistogramSeries, {
            priceFormat: { type: "volume" },
            priceScaleId: "volume",
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.83, bottom: 0 },
        });
        volumeSeries.setData(candles.map((candle) => ({
            time: candle.time as Time,
            value: candle.volume,
            color: candle.close >= candle.open ? "#16c79a35" : "#ef5b7835",
        })));

        const ema21 = chart.addSeries(LineSeries, {
            color: "#36a3ff",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        ema21.setData(ema(candles, 21));
        const ema55 = chart.addSeries(LineSeries, {
            color: "#f2b84b",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        ema55.setData(ema(candles, 55));
        chart.timeScale().fitContent();

        const observer = new ResizeObserver(() => {
            chart.applyOptions({ width: container.clientWidth });
        });
        observer.observe(container);

        return () => {
            observer.disconnect();
            chart.remove();
            chartRef.current = null;
        };
    }, [candles, height]);

    return <div ref={containerRef} className="h-full min-h-[420px] w-full" />;
});
