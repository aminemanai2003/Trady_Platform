"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import styles from "./page.module.css";

interface TickMap {
    [symbol: string]: {
        bid?: number;
        ask?: number;
    };
}

interface Trade {
    id: string;
    symbol: string;
    side: "BUY" | "SELL";
    timeframe: string;
    size: number;
    entry_price: number;
    close_price?: number;
    pnl?: number;
    pnl_pct?: number;
    opened_at: string;
    status: "OPEN" | "CLOSED";
}

interface TradeListResponse {
    trades: Trade[];
    count: number;
}

interface TestingSummary {
    total_trades?: number;
    open_trades?: number;
    closed_trades?: number;
    win_rate?: number;
    total_pnl?: number;
    avg_pnl_pct?: number;
}

interface CoachSignal {
    tradeId: string;
    symbol: string;
    action: "HOLD" | "PREPARE" | "TAKE_PARTIAL" | "CLOSE_NOW";
    confidence: number;
    title: string;
    detail: string;
    ttlSeconds: number;
    priority: number;
    message?: string;
}

// All API calls go through Next.js proxy routes (same-origin) to avoid CORS issues.
// The proxy routes are defined in src/app/api/{ticks,testing,signals}/route.ts
// and forward requests server-side to Django on localhost:8000.
const API = {
    ticks: "/api/ticks",
    trades: "/api/testing/trades",
    summary: "/api/testing/summary",
    reset: "/api/testing/reset",
    coach: "/api/testing/coach",
    decision: (symbol: string, timeframe: string) => `/api/signals/decision/${symbol}?timeframe=${timeframe}`,
};

function fmt(value: unknown, digits = 5): string {
    const n = Number(value);
    if (!Number.isFinite(n)) return "-";
    return n.toFixed(digits);
}

function getPipSize(symbol: string): number {
    return symbol.includes("JPY") ? 0.01 : 0.0001;
}

function actionLabel(action: string): string {
    if (action === "CLOSE_NOW") return "Close now";
    if (action === "TAKE_PARTIAL") return "Take partial";
    if (action === "PREPARE") return "Prepare";
    return "Hold";
}

function clamp(text: string, max: number): string {
    return text.length > max ? `${text.slice(0, max)}...` : text;
}

function coachActionClass(action: string): string {
    return `act${String(action || "HOLD").toLowerCase().replaceAll("_", "")}`;
}

export default function TestingPage() {
    const [sessionId, setSessionId] = useState("");
    const [symbol, setSymbol] = useState("EURUSD");
    const [side, setSide] = useState<"BUY" | "SELL">("BUY");
    const [timeframe, setTimeframe] = useState("1H");
    const [size, setSize] = useState("1.00");
    const [entryPrice, setEntryPrice] = useState("");
    const [note, setNote] = useState("");
    const [formHint, setFormHint] = useState("Session is local to this browser. Trades are persisted on backend storage.");

    const [latestTicks, setLatestTicks] = useState<TickMap>({});
    const [trades, setTrades] = useState<Trade[]>([]);
    const [summary, setSummary] = useState<TestingSummary>({});
    const [openLivePnlSum, setOpenLivePnlSum] = useState(0);
    const [openLiveWinRate, setOpenLiveWinRate] = useState(0);
    const [coachMode, setCoachMode] = useState("beginner");
    const [coachMessages, setCoachMessages] = useState<CoachSignal[]>([]);
    const [coachBubble, setCoachBubble] = useState<{ show: boolean; action: string; title: string; body: string }>({
        show: false,
        action: "HOLD",
        title: "",
        body: "",
    });
    const [pnlMood, setPnlMood] = useState<"happy" | "sad" | "neutral">("neutral");
    const [pnlMoodText, setPnlMoodText] = useState("Mood: Neutral");

    const coachAdviceCacheRef = useRef<Map<string, { ts: number; advice: Array<Record<string, unknown>> }>>(new Map());
    const coachActionStateRef = useRef<Record<string, { action: string; emittedAt: number }>>({});
    const lastCoachEmitAtRef = useRef(0);
    const coachBubbleTimerRef = useRef<number | null>(null);

    useEffect(() => {
        const key = "trady-testing-session-id";
        let current = localStorage.getItem(key);
        if (!current) {
            current = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
            localStorage.setItem(key, current);
        }
        setSessionId(current);

        const storedMode = localStorage.getItem("trady-coach-mode") || "beginner";
        setCoachMode(storedMode);
    }, []);

    const openTrades = useMemo(() => trades.filter((t) => t.status === "OPEN"), [trades]);
    const closedTrades = useMemo(() => trades.filter((t) => t.status === "CLOSED"), [trades]);

    const computeLivePnl = useCallback(
        (trade: Trade, tickMap: TickMap = latestTicks) => {
            const tick = tickMap[trade.symbol];
            if (!tick || !Number.isFinite(Number(tick.bid))) {
                return { price: NaN, pnl: NaN };
            }
            const current = Number(tick.bid);
            const entry = Number(trade.entry_price);
            const tradeSize = Number(trade.size);
            const direction = trade.side === "BUY" ? 1 : -1;
            const pnl = (current - entry) * direction * tradeSize;
            return { price: current, pnl };
        },
        [latestTicks]
    );

    const estimateRiskAbs = (trade: Trade): number => {
        const entry = Number(trade.entry_price || 0);
        const tradeSize = Number(trade.size || 0);
        const basePips = 15;
        return Math.max(getPipSize(trade.symbol) * basePips * tradeSize, entry * 0.0012 * tradeSize, 0.0001);
    };

    const minutesOpen = (trade: Trade): number => {
        const opened = Date.parse(trade.opened_at || "");
        if (!Number.isFinite(opened)) return 0;
        return Math.max(0, (Date.now() - opened) / 60000);
    };

    const buildCoachSignal = useCallback((trade: Trade, livePnl: number): CoachSignal | null => {
        if (!Number.isFinite(livePnl)) return null;

        const risk = estimateRiskAbs(trade);
        const r = livePnl / risk;
        const mins = minutesOpen(trade);
        const sideWord = trade.side === "BUY" ? "long" : "short";

        if (r <= -1.0 || (mins > 240 && livePnl < 0)) {
            return {
                tradeId: trade.id,
                symbol: trade.symbol,
                action: "CLOSE_NOW",
                confidence: 0.87,
                title: `${trade.symbol} ${sideWord}: protect capital`,
                detail: `Loss reached ${fmt(Math.abs(r), 2)}R or time-stop is breached. Closing now preserves your next opportunity.`,
                ttlSeconds: 14,
                priority: 100,
            };
        }
        if (r >= 2.0) {
            return {
                tradeId: trade.id,
                symbol: trade.symbol,
                action: "TAKE_PARTIAL",
                confidence: 0.81,
                title: `${trade.symbol} ${sideWord}: lock gains`,
                detail: `Trade is at ${fmt(r, 2)}R. Consider partial profit and trail stop to reduce giveback risk.`,
                ttlSeconds: 12,
                priority: 85,
            };
        }
        if (r >= 1.0 && mins > 90) {
            return {
                tradeId: trade.id,
                symbol: trade.symbol,
                action: "PREPARE",
                confidence: 0.72,
                title: `${trade.symbol} ${sideWord}: prepare decision`,
                detail: "Profit is positive for a long duration. Prepare to tighten stop if momentum weakens.",
                ttlSeconds: 10,
                priority: 70,
            };
        }
        return {
            tradeId: trade.id,
            symbol: trade.symbol,
            action: "HOLD",
            confidence: 0.62,
            title: `${trade.symbol} ${sideWord}: stay patient`,
            detail: "No high-priority trigger yet. Keep waiting for stop, target, or stronger confirmation.",
            ttlSeconds: 9,
            priority: 30,
        };
    }, []);

    const coachCacheKey = (signals: CoachSignal[]): string =>
        signals
            .map((signal) => `${signal.tradeId}:${signal.action}:${Math.round(signal.confidence * 100)}:${Math.round(signal.priority)}`)
            .join("|");

    const enrichCoachSignals = useCallback(
        async (signals: CoachSignal[]): Promise<Array<Record<string, unknown>>> => {
            if (!signals.length || !sessionId) return [];

            const key = coachCacheKey(signals);
            const cached = coachAdviceCacheRef.current.get(key);
            if (cached && Date.now() - cached.ts < 45000) {
                return cached.advice;
            }

            const payload = {
                session_id: sessionId,
                mode: coachMode,
                signals: signals.slice(0, 4).map((signal) => ({
                    trade_id: signal.tradeId,
                    symbol: signal.symbol,
                    action: signal.action,
                    confidence: signal.confidence,
                    detail: signal.detail,
                    priority: signal.priority,
                })),
            };

            try {
                const res = await fetch(API.coach, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                if (!res.ok) {
                    throw new Error(`Coach API HTTP ${res.status}`);
                }
                const out = (await res.json()) as { advice?: Array<Record<string, unknown>> };
                const advice = Array.isArray(out.advice) ? out.advice : [];
                coachAdviceCacheRef.current.set(key, { ts: Date.now(), advice });
                return advice;
            } catch {
                return [];
            }
        },
        [sessionId, coachMode]
    );

    const shouldEmitCoach = (signal: CoachSignal): boolean => {
        const key = `${signal.tradeId}`;
        const now = Date.now();
        const prior = coachActionStateRef.current[key];

        if (!prior || prior.action !== signal.action) {
            coachActionStateRef.current[key] = { action: signal.action, emittedAt: now };
            return true;
        }

        if (now - prior.emittedAt > 120000 && signal.action !== "HOLD") {
            coachActionStateRef.current[key] = { action: signal.action, emittedAt: now };
            return true;
        }
        return false;
    };

    const showCoachBubble = (message: CoachSignal) => {
        setCoachBubble({
            show: true,
            action: message.action,
            title: `${actionLabel(message.action)} - ${message.symbol}`,
            body: `${message.message || message.detail} (confidence ${fmt(message.confidence * 100, 0)}%)`,
        });

        if (coachBubbleTimerRef.current) {
            window.clearTimeout(coachBubbleTimerRef.current);
        }

        coachBubbleTimerRef.current = window.setTimeout(() => {
            setCoachBubble((current) => ({ ...current, show: false }));
        }, Math.max(4000, Number(message.ttlSeconds || 9) * 1000));
    };

    const runCoach = useCallback(
        async (openPositions: Trade[], ticks: TickMap) => {
            const signals = openPositions
                .map((trade) => ({ trade, live: computeLivePnl(trade, ticks) }))
                .map(({ trade, live }) => buildCoachSignal(trade, Number(live.pnl)))
                .filter((signal): signal is CoachSignal => signal !== null)
                .sort((a, b) => b.priority - a.priority);

            const advice = await enrichCoachSignals(signals);
            const adviceByTradeAction: Record<string, Record<string, unknown>> = {};
            advice.forEach((row) => {
                const tradeId = String(row.trade_id || "");
                const action = String(row.action || "");
                adviceByTradeAction[`${tradeId}|${action}`] = row;
            });

            signals.forEach((signal) => {
                const match = adviceByTradeAction[`${signal.tradeId}|${signal.action}`];
                if (match && match.message) {
                    signal.message = String(match.message);
                }
            });

            setCoachMessages(signals);

            if (!signals.length) return;

            const now = Date.now();
            if (now - lastCoachEmitAtRef.current < 8000) return;

            const candidate = signals.find((signal) => signal.action !== "HOLD" && shouldEmitCoach(signal));
            if (!candidate) return;

            lastCoachEmitAtRef.current = now;
            showCoachBubble(candidate);
        },
        [buildCoachSignal, computeLivePnl, enrichCoachSignals]
    );

    const refreshAll = useCallback(async () => {
        if (!sessionId) return;

        const [ticksRes, tradesRes, summaryRes] = await Promise.all([
            fetch(API.ticks, { cache: "no-store" }),
            fetch(`${API.trades}?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" }),
            fetch(`${API.summary}?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" }),
        ]);

        const ticksData = (await ticksRes.json()) as TickMap;
        const tradeData = (await tradesRes.json()) as TradeListResponse;
        const summaryData = (await summaryRes.json()) as TestingSummary;

        setLatestTicks(ticksData || {});
        const loadedTrades = Array.isArray(tradeData.trades) ? tradeData.trades : [];
        setTrades(loadedTrades);
        setSummary(summaryData || {});

        const openPositions = loadedTrades.filter((trade) => trade.status === "OPEN");
        const openLive = openPositions
            .map((trade) => {
                const tick = ticksData[trade.symbol];
                if (!tick || !Number.isFinite(Number(tick.bid))) {
                    return { pnl: NaN };
                }
                const current = Number(tick.bid);
                const direction = trade.side === "BUY" ? 1 : -1;
                const pnl = (current - Number(trade.entry_price)) * direction * Number(trade.size);
                return { pnl };
            })
            .filter((row) => Number.isFinite(row.pnl));

        const unrealized = openLive.reduce((acc, row) => acc + Number(row.pnl), 0);
        const openWins = openLive.filter((row) => Number(row.pnl) > 0).length;
        const openWinrate = openLive.length ? (openWins / openLive.length) * 100.0 : 0;

        setOpenLivePnlSum(unrealized);
        setOpenLiveWinRate(openWinrate);

        const net = Number(summaryData.total_pnl || 0) + Number(unrealized || 0);
        if (net > 0.000001) {
            setPnlMood("happy");
            setPnlMoodText(`Mood: Happy (Net +${fmt(net, 4)})`);
        } else if (net < -0.000001) {
            setPnlMood("sad");
            setPnlMoodText(`Mood: Sad (Net ${fmt(net, 4)})`);
        } else {
            setPnlMood("neutral");
            setPnlMoodText("Mood: Neutral (Flat)");
        }

        await runCoach(openPositions, ticksData);
    }, [sessionId, runCoach]);

    useEffect(() => {
        if (!sessionId) return;
        void refreshAll();
        const id = window.setInterval(() => {
            void refreshAll();
        }, 15000);
        return () => window.clearInterval(id);
    }, [sessionId, refreshAll]);

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "m") {
                setCoachMode((current) => {
                    const next = current === "beginner" ? "advanced" : "beginner";
                    localStorage.setItem("trady-coach-mode", next);
                    return next;
                });
            }
        };
        document.addEventListener("keydown", onKeyDown);
        return () => document.removeEventListener("keydown", onKeyDown);
    }, []);

    useEffect(() => {
        return () => {
            if (coachBubbleTimerRef.current) {
                window.clearTimeout(coachBubbleTimerRef.current);
            }
        };
    }, []);

    const loadLivePrice = async () => {
        try {
            const tickData = (await fetch(API.ticks, { cache: "no-store" }).then((r) => r.json())) as TickMap;
            setLatestTicks(tickData || {});
            const tick = tickData[symbol];
            if (!tick || !Number.isFinite(Number(tick.bid))) {
                setFormHint(`Live price unavailable for ${symbol}.`);
                return;
            }
            setEntryPrice(Number(tick.bid).toFixed(symbol.includes("JPY") ? 3 : 5));
            setFormHint(`Live price loaded for ${symbol}.`);
        } catch {
            setFormHint(`Live price unavailable for ${symbol}.`);
        }
    };

    const openTrade = async () => {
        const tradeSize = Number(size || 0);
        const entry = Number(entryPrice || 0);
        if (!entry || entry <= 0 || !tradeSize || tradeSize <= 0) {
            setFormHint("Please provide valid entry price and size.");
            return;
        }

        let snapshot: Record<string, unknown> = {};
        try {
            snapshot = await fetch(API.decision(symbol, timeframe), { cache: "no-store" }).then((r) => r.json());
        } catch {
            snapshot = {};
        }

        const payload = {
            session_id: sessionId,
            symbol,
            side,
            timeframe,
            size: tradeSize,
            entry_price: entry,
            note,
            agent_snapshot: {
                final_signal: snapshot.final_signal || null,
                global_confidence: snapshot.global_confidence || null,
                decision_timestamp: snapshot.decision_timestamp || null,
                fallback_used: snapshot.fallback_used || false,
            },
        };

        try {
            const res = await fetch(API.trades, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                throw new Error(await res.text());
            }

            setNote("");
            setFormHint("Test trade opened successfully.");
            await refreshAll();
        } catch (err) {
            setFormHint(`Failed to open trade: ${String(err)}`);
        }
    };

    const closeTrade = async (tradeId: string, pair: string) => {
        const ticksData = (await fetch(API.ticks, { cache: "no-store" }).then((r) => r.json())) as TickMap;
        setLatestTicks(ticksData || {});

        const tick = ticksData[pair];
        if (!tick || !Number.isFinite(Number(tick.bid))) {
            window.alert(`Cannot close ${pair}. Live price is unavailable.`);
            return;
        }

        const res = await fetch(`${API.trades}/${tradeId}/close`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ close_price: Number(tick.bid) }),
        });

        if (!res.ok) {
            window.alert("Failed to close trade.");
            return;
        }
        await refreshAll();
    };

    const resetSession = async () => {
        const first = window.confirm(
            "Are you sure you want to reset this testing session? This will delete all open and closed simulated trades."
        );
        if (!first) return;

        const typed = window.prompt("Type RESET to confirm this action.");
        if (typed !== "RESET") {
            setFormHint("Reset cancelled.");
            return;
        }

        try {
            const res = await fetch(API.reset, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId }),
            });
            if (!res.ok) {
                throw new Error(await res.text());
            }
            const out = (await res.json()) as { deleted_trades?: number };
            setFormHint(`Session reset complete. Deleted ${out.deleted_trades || 0} trade(s).`);
            await refreshAll();
        } catch (err) {
            setFormHint(`Reset failed: ${String(err)}`);
        }
    };

    return (
        <div className={styles.pageShell}>
            <header className="flex h-14 shrink-0 items-center gap-2 border-b px-6">
                <SidebarTrigger className="-ml-1" />
                <Separator orientation="vertical" className="mr-2 h-4" />
                <h1 className="text-lg font-semibold">Testing</h1>
            </header>

            <main className={styles.page}>
                <section className={styles.hero}>
                    <h1>Testing Mode</h1>
                    <p>
                        Paper-trade in simulation mode. Open BUY or SELL test positions, save your rationale, and
                        review outcomes later to compare your decisions with agent snapshots.
                    </p>
                </section>

                <section className={styles.summaryGrid}>
                    <article className={styles.sumCard}><div className={styles.sumK}>Total Trades</div><div className={styles.sumV}>{summary.total_trades ?? 0}</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Open Trades</div><div className={styles.sumV}>{summary.open_trades ?? 0}</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Closed Trades</div><div className={styles.sumV}>{summary.closed_trades ?? 0}</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Closed Win Rate</div><div className={styles.sumV}>{fmt(summary.win_rate || 0, 2)}%</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Realized PnL</div><div className={styles.sumV}>{fmt(summary.total_pnl || 0, 4)}</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Avg Realized PnL %</div><div className={styles.sumV}>{fmt(summary.avg_pnl_pct || 0, 2)}%</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Unrealized PnL</div><div className={styles.sumV}>{fmt(openLivePnlSum || 0, 4)}</div></article>
                    <article className={styles.sumCard}><div className={styles.sumK}>Open Win Rate</div><div className={styles.sumV}>{fmt(openLiveWinRate || 0, 2)}%</div></article>
                </section>

                <section className={styles.layout}>
                    <div className={styles.leftStack}>
                        <article className={styles.card}>
                            <div className={styles.cardHd}>Open New Test Trade</div>
                            <div className={styles.cardBd}>
                                <div className={styles.formGrid}>
                                    <div className={styles.formRow}>
                                        <label htmlFor="symbol">Symbol</label>
                                        <select id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                                            <option value="EURUSD">EURUSD</option>
                                            <option value="USDJPY">USDJPY</option>
                                            <option value="GBPUSD">GBPUSD</option>
                                            <option value="USDCHF">USDCHF</option>
                                        </select>
                                    </div>
                                    <div className={styles.formRow}>
                                        <label htmlFor="side">Side</label>
                                        <select id="side" value={side} onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}>
                                            <option value="BUY">BUY</option>
                                            <option value="SELL">SELL</option>
                                        </select>
                                    </div>
                                    <div className={styles.formRow}>
                                        <label htmlFor="timeframe">Timeframe</label>
                                        <select id="timeframe" value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                                            <option value="LIVE">LIVE</option>
                                            <option value="1S">1S</option>
                                            <option value="1H">1H</option>
                                            <option value="4H">4H</option>
                                            <option value="1D">1D</option>
                                        </select>
                                    </div>
                                    <div className={styles.formRow}>
                                        <label htmlFor="size">Size</label>
                                        <input id="size" type="number" min="0.01" step="0.01" value={size} onChange={(e) => setSize(e.target.value)} />
                                    </div>
                                    <div className={`${styles.formRow} ${styles.full}`}>
                                        <label htmlFor="entry">Entry Price</label>
                                        <input
                                            id="entry"
                                            type="number"
                                            min="0.00001"
                                            step="0.00001"
                                            placeholder="Use live price or type manually"
                                            value={entryPrice}
                                            onChange={(e) => setEntryPrice(e.target.value)}
                                        />
                                    </div>
                                    <div className={`${styles.formRow} ${styles.full}`}>
                                        <label htmlFor="note">Reason / Notes</label>
                                        <textarea
                                            id="note"
                                            placeholder="Why are you opening this test trade?"
                                            value={note}
                                            onChange={(e) => setNote(e.target.value)}
                                        />
                                    </div>
                                </div>
                                <div className={styles.rowActions} style={{ marginTop: 10 }}>
                                    <button className={styles.btn} type="button" onClick={() => void loadLivePrice()}>Use Live Price</button>
                                    <button className={`${styles.btn} ${styles.primary}`} type="button" onClick={() => void openTrade()}>Open Test Trade</button>
                                    <button className={`${styles.btn} ${styles.danger}`} type="button" onClick={() => void resetSession()}>Reset Testing Session</button>
                                </div>
                                <div className={styles.hint}>{formHint}</div>
                            </div>
                        </article>

                        <aside className={styles.coachCard} aria-live="polite" aria-label="Robot coach panel">
                            <div className={styles.coachHd}>
                                <div>
                                    <div className={styles.coachTitle}>Robot Coach</div>
                                    <div className={styles.coachSub}>
                                        {coachMode === "advanced" ? "Advanced mode - concise alerts" : "Beginner mode - guided prompts"}
                                    </div>
                                </div>
                                <div className={styles.coachSub}>{new Date().toLocaleTimeString()}</div>
                            </div>
                            <div className={styles.coachStage}>
                                <div className={styles.pnlBotWrap}>
                                    <div className={`${styles.pnlBot} ${styles[pnlMood]}`} role="img" aria-label="Robot mood indicator">
                                        <div className={`${styles.botArm} ${styles.left}`}></div>
                                        <div className={`${styles.botArm} ${styles.right}`}></div>
                                        <div className={styles.botBody}></div>
                                        <div className={styles.botFace}>
                                            <div className={styles.botAntenna}></div>
                                            <div className={styles.botEyes}><span className={styles.botEye}></span><span className={styles.botEye}></span></div>
                                            <div className={styles.botMouth}></div>
                                            <div className={styles.botTear}></div>
                                        </div>
                                    </div>
                                    <div className={styles.pnlBotStatus}>{pnlMoodText}</div>
                                </div>
                                <div className={styles.coachBubbleWrap}>
                                    <div className={`${styles.coachBubble} ${styles[coachActionClass(coachBubble.action)]} ${coachBubble.show ? styles.show : ""}`}>
                                        <div className={styles.coachBubbleTitle}>{coachBubble.title}</div>
                                        <div className={styles.coachBubbleBody}>{coachBubble.body}</div>
                                    </div>
                                </div>
                            </div>
                            <div className={styles.coachFeed}>
                                {!coachMessages.length ? (
                                    <div className={styles.coachEmpty}>Open a test trade to receive coaching prompts.</div>
                                ) : (
                                    coachMessages.slice(0, 6).map((msg) => (
                                        <article className={`${styles.coachItem} ${styles[coachActionClass(msg.action)]}`} key={`${msg.tradeId}-${msg.action}`}>
                                            <div className={styles.coachItemHd}>
                                                <div className={styles.coachItemTitle}>{actionLabel(msg.action)} - {msg.symbol}</div>
                                                <div className={styles.coachItemMeta}>{fmt(msg.confidence * 100, 0)}%</div>
                                            </div>
                                            <div className={styles.coachItemBody}>{msg.message || msg.detail}</div>
                                        </article>
                                    ))
                                )}
                            </div>
                        </aside>
                    </div>

                    <section className={styles.tables}>
                        <article className={styles.card}>
                            <div className={styles.cardHd}>Open Positions</div>
                            <div className={styles.tableWrap}>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Pair</th>
                                            <th>Side</th>
                                            <th>Entry</th>
                                            <th>Size</th>
                                            <th>Current</th>
                                            <th>Live PnL</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {!openTrades.length ? (
                                            <tr><td colSpan={7} style={{ color: "#3d5066" }}>No open test trades.</td></tr>
                                        ) : (
                                            openTrades.map((trade) => {
                                                const live = computeLivePnl(trade);
                                                const pnl = Number(live.pnl);
                                                const priceDigits = trade.symbol.includes("JPY") ? 3 : 5;
                                                return (
                                                    <tr key={trade.id}>
                                                        <td>{trade.symbol}</td>
                                                        <td className={`${styles.side} ${trade.side === "BUY" ? styles.buy : styles.sell}`}>{trade.side}</td>
                                                        <td>{fmt(trade.entry_price, priceDigits)}</td>
                                                        <td>{fmt(trade.size, 2)}</td>
                                                        <td>{Number.isFinite(Number(live.price)) ? Number(live.price).toFixed(priceDigits) : "-"}</td>
                                                        <td className={Number.isFinite(pnl) ? (pnl >= 0 ? styles.pnlPos : styles.pnlNeg) : ""}>{Number.isFinite(pnl) ? pnl.toFixed(4) : "-"}</td>
                                                        <td><button className={styles.smallBtn} onClick={() => void closeTrade(trade.id, trade.symbol)}>Close</button></td>
                                                    </tr>
                                                );
                                            })
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </article>

                        <article className={styles.card}>
                            <div className={styles.cardHd}>Closed Positions</div>
                            <div className={styles.tableWrap}>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Pair</th>
                                            <th>Side</th>
                                            <th>Entry</th>
                                            <th>Exit</th>
                                            <th>PnL</th>
                                            <th>PnL %</th>
                                            <th>Opened</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {!closedTrades.length ? (
                                            <tr><td colSpan={7} style={{ color: "#3d5066" }}>No closed trades yet.</td></tr>
                                        ) : (
                                            closedTrades.map((trade) => {
                                                const priceDigits = trade.symbol.includes("JPY") ? 3 : 5;
                                                const pnl = Number(trade.pnl || 0);
                                                const pnlPct = Number(trade.pnl_pct || 0);
                                                return (
                                                    <tr key={trade.id}>
                                                        <td>{trade.symbol}</td>
                                                        <td className={`${styles.side} ${trade.side === "BUY" ? styles.buy : styles.sell}`}>{trade.side}</td>
                                                        <td>{fmt(trade.entry_price, priceDigits)}</td>
                                                        <td>{fmt(trade.close_price, priceDigits)}</td>
                                                        <td className={pnl >= 0 ? styles.pnlPos : styles.pnlNeg}>{fmt(pnl, 4)}</td>
                                                        <td className={pnlPct >= 0 ? styles.pnlPos : styles.pnlNeg}>{fmt(pnlPct, 2)}%</td>
                                                        <td>{clamp(new Date(trade.opened_at).toLocaleString(), 32)}</td>
                                                    </tr>
                                                );
                                            })
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </article>
                    </section>
                </section>
            </main>
        </div>
    );
}

