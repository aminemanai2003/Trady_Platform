"use client";

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    X,
    Loader2,
    CheckCircle2,
} from "lucide-react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { useSession } from "next-auth/react";

const TradingViewWidget = dynamic(
    () => import("@/components/tradingview-widget"),
    { ssr: false }
);

type PairKey = "EURUSD" | "USDJPY" | "USDCHF" | "GBPUSD";

interface Position {
    id: number;
    pair: string;
    side: string;
    size: number;
    entryPrice: number;
    currentPrice: number;
    stopLoss: number | null;
    takeProfit: number | null;
    pnl: number;
    pnlPct: number;
    status: string;
    openedAt: string;
}

const generateCandles = (base: number, isJpy: boolean) =>
    Array.from({ length: 80 }, (_, i) => {
        const noise = Math.sin(i / 8) * (isJpy ? 1.5 : 0.003) + (Math.random() - 0.5) * (isJpy ? 0.8 : 0.002);
        const o = base + noise;
        const c = o + (Math.random() - 0.48) * (isJpy ? 0.5 : 0.001);
        const h = Math.max(o, c) + Math.random() * (isJpy ? 0.3 : 0.0008);
        const l = Math.min(o, c) - Math.random() * (isJpy ? 0.3 : 0.0008);
        return { time: `${i}`, open: +o.toFixed(isJpy ? 2 : 4), high: +h.toFixed(isJpy ? 2 : 4), low: +l.toFixed(isJpy ? 2 : 4), close: +c.toFixed(isJpy ? 2 : 4), volume: Math.floor(Math.random() * 5000 + 500) };
    });

const pairConfig: Record<PairKey, { price: number; isJpy: boolean; signal: string; indicators: Record<string, number> }> = {
    EURUSD: { price: 1.0852, isJpy: false, signal: "BUY", indicators: { RSI: 34.2, MACD: 0.00012, "BB Upper": 1.08910, "BB Lower": 1.08120, SMA50: 1.08450, SMA200: 1.08320, ATR: 0.00650 } },
    USDJPY: { price: 149.52, isJpy: true, signal: "SELL", indicators: { RSI: 72.1, MACD: -0.15, "BB Upper": 150.42, "BB Lower": 148.65, SMA50: 149.80, SMA200: 149.10, ATR: 0.85 } },
    USDCHF: { price: 0.8823, isJpy: false, signal: "NEUTRAL", indicators: { RSI: 48.5, MACD: 0.00003, "BB Upper": 0.88720, "BB Lower": 0.87710, SMA50: 0.88200, SMA200: 0.88150, ATR: 0.00520 } },
    GBPUSD: { price: 1.2655, isJpy: false, signal: "BUY", indicators: { RSI: 38.7, MACD: 0.00025, "BB Upper": 1.27100, "BB Lower": 1.25950, SMA50: 1.26450, SMA200: 1.26200, ATR: 0.00780 } },
};

const signalMap: Record<string, string> = {
    BUY: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    SELL: "bg-rose-500/20 text-rose-400 border-rose-500/30",
    NEUTRAL: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

export default function TradingPage() {
    const [selectedPair, setSelectedPair] = useState<PairKey>("EURUSD");
    const [timeframe, setTimeframe] = useState("4H");
    const [lotSize, setLotSize] = useState(0.1);
    const [slPips, setSlPips] = useState(40);
    const [tpPips, setTpPips] = useState(80);
    const [positions, setPositions] = useState<Position[]>([]);
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState<{ message: string; type: string } | null>(null);

    const data = pairConfig[selectedPair];
    const candles = generateCandles(data.price, data.isJpy);
    const pipSize = data.isJpy ? 0.01 : 0.0001;

    // Fetch positions from database
    const fetchPositions = useCallback(async () => {
        try {
            const res = await fetch("/api/positions");
            if (res.ok) {
                const data = await res.json();
                setPositions(data);
            }
        } catch { }
    }, []);

    useEffect(() => { fetchPositions(); }, [fetchPositions]);

    // Show toast notification
    const showToast = (message: string, type: string) => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    // BUY or SELL — creates real position in MySQL
    const openPosition = async (side: "BUY" | "SELL") => {
        setLoading(true);
        const price = data.price;
        const sl = side === "BUY" ? price - slPips * pipSize : price + slPips * pipSize;
        const tp = side === "BUY" ? price + tpPips * pipSize : price - tpPips * pipSize;

        try {
            const res = await fetch("/api/positions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    pair: selectedPair,
                    side,
                    size: lotSize,
                    entryPrice: price,
                    stopLoss: +sl.toFixed(data.isJpy ? 2 : 5),
                    takeProfit: +tp.toFixed(data.isJpy ? 2 : 5),
                }),
            });

            if (res.ok) {
                showToast(`${side} ${selectedPair} — ${lotSize} lot @ ${price}`, "success");
                fetchPositions();
            } else {
                const err = await res.json();
                showToast(err.error || "Order failed", "error");
            }
        } catch {
            showToast("Network error", "error");
        }
        setLoading(false);
    };

    // Close position
    const closePosition = async (id: number, currentPrice: number) => {
        try {
            const res = await fetch("/api/positions", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id, currentPrice }),
            });
            if (res.ok) {
                showToast("Position closed", "success");
                fetchPositions();
            }
        } catch {
            showToast("Failed to close position", "error");
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Toast */}
            {toast && (
                <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium animate-in slide-in-from-right ${toast.type === "success" ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"}`}>
                    <CheckCircle2 className="size-4" />
                    {toast.message}
                </div>
            )}

            <header className="flex h-14 shrink-0 items-center gap-2 border-b px-6">
                <SidebarTrigger className="-ml-1" />
                <Separator orientation="vertical" className="mr-2 h-4" />
                <h1 className="text-lg font-semibold">Trading</h1>
                <div className="ml-auto flex items-center gap-2">
                    {(["EURUSD", "USDJPY", "USDCHF", "GBPUSD"] as PairKey[]).map((pair) => (
                        <Button key={pair} size="sm" variant={selectedPair === pair ? "default" : "outline"} onClick={() => setSelectedPair(pair)} className="text-xs">
                            {pair.slice(0, 3)}/{pair.slice(3)}
                        </Button>
                    ))}
                </div>
            </header>

            <div className="flex-1 overflow-auto p-6 space-y-4">
                <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
                    {/* TradingView Chart */}
                    <Card className="xl:col-span-3 border-border/50 bg-card/80 backdrop-blur">
                        <CardContent className="p-4">
                            <TradingViewWidget
                                symbol={selectedPair}
                                interval={timeframe === "1H" ? "60" : timeframe === "4H" ? "240" : timeframe === "1D" ? "D" : "W"}
                                theme="dark"
                                height={380}
                            />
                        </CardContent>
                    </Card>

                    {/* Order Panel */}
                    <div className="space-y-4">
                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader className="pb-3">
                                <CardTitle className="text-sm">Quick Order</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                <div className="grid grid-cols-2 gap-2">
                                    <Button onClick={() => openPosition("BUY")} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold">
                                        {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowUpRight className="size-4 mr-1" />} BUY
                                    </Button>
                                    <Button onClick={() => openPosition("SELL")} disabled={loading} className="bg-rose-600 hover:bg-rose-700 text-white font-bold">
                                        {loading ? <Loader2 className="size-4 animate-spin" /> : <ArrowDownRight className="size-4 mr-1" />} SELL
                                    </Button>
                                </div>
                                <div className="space-y-2 text-xs">
                                    <div className="flex justify-between items-center p-2 rounded bg-muted/30">
                                        <span className="text-muted-foreground">Lot Size</span>
                                        <select value={lotSize} onChange={(e) => setLotSize(+e.target.value)} className="bg-transparent text-right font-mono font-medium focus:outline-none cursor-pointer">
                                            {[0.01, 0.05, 0.1, 0.2, 0.5, 1.0].map((v) => <option key={v} value={v}>{v.toFixed(2)}</option>)}
                                        </select>
                                    </div>
                                    <div className="flex justify-between items-center p-2 rounded bg-muted/30">
                                        <span className="text-muted-foreground">Stop Loss</span>
                                        <select value={slPips} onChange={(e) => setSlPips(+e.target.value)} className="bg-transparent text-right font-mono font-medium focus:outline-none cursor-pointer">
                                            {[20, 30, 40, 50, 60, 80].map((v) => <option key={v} value={v}>{v} pips</option>)}
                                        </select>
                                    </div>
                                    <div className="flex justify-between items-center p-2 rounded bg-muted/30">
                                        <span className="text-muted-foreground">Take Profit</span>
                                        <select value={tpPips} onChange={(e) => setTpPips(+e.target.value)} className="bg-transparent text-right font-mono font-medium focus:outline-none cursor-pointer">
                                            {[40, 60, 80, 100, 120, 160].map((v) => <option key={v} value={v}>{v} pips</option>)}
                                        </select>
                                    </div>
                                    <div className="flex justify-between p-2 rounded bg-muted/30">
                                        <span className="text-muted-foreground">Risk/Reward</span>
                                        <span className="font-mono font-medium text-emerald-400">1:{(tpPips / slPips).toFixed(1)}</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-border/50 bg-card/80 backdrop-blur">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm">Indicators</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-1.5">
                                {Object.entries(data.indicators).map(([key, val]) => (
                                    <div key={key} className="flex justify-between text-xs p-1.5 rounded bg-muted/20">
                                        <span className="text-muted-foreground">{key}</span>
                                        <span className="font-mono font-medium">{val > 10 ? val.toFixed(2) : val.toFixed(5)}</span>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Positions Table */}
                <Card className="border-border/50 bg-card/80 backdrop-blur">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">Open Positions</CardTitle>
                            <Badge variant="outline" className="text-xs">{positions.length} active</Badge>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {positions.length === 0 ? (
                            <div className="text-center py-8 text-sm text-muted-foreground">
                                No open positions. Use the BUY/SELL buttons above to open one.
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Pair</TableHead>
                                        <TableHead>Side</TableHead>
                                        <TableHead>Size</TableHead>
                                        <TableHead>Entry</TableHead>
                                        <TableHead>SL</TableHead>
                                        <TableHead>TP</TableHead>
                                        <TableHead>Time</TableHead>
                                        <TableHead className="text-right">Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {positions.map((pos) => (
                                        <TableRow key={pos.id}>
                                            <TableCell className="font-medium">{pos.pair.slice(0, 3)}/{pos.pair.slice(3)}</TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className={signalMap[pos.side]}>{pos.side}</Badge>
                                            </TableCell>
                                            <TableCell className="font-mono text-xs">{pos.size}</TableCell>
                                            <TableCell className="font-mono text-xs">{pos.entryPrice}</TableCell>
                                            <TableCell className="font-mono text-xs text-rose-400">{pos.stopLoss || "—"}</TableCell>
                                            <TableCell className="font-mono text-xs text-emerald-400">{pos.takeProfit || "—"}</TableCell>
                                            <TableCell className="text-xs text-muted-foreground">{new Date(pos.openedAt).toLocaleTimeString()}</TableCell>
                                            <TableCell className="text-right">
                                                <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => closePosition(pos.id, pairConfig[pos.pair as PairKey]?.price || pos.entryPrice)}>
                                                    <X className="size-3 mr-1" /> Close
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
