"use client";

import { useEffect, useMemo, useState } from "react";
import {
    ExternalLink,
    Filter,
    MinusCircle,
    Newspaper,
    RefreshCw,
    Search,
    TrendingDown,
    TrendingUp,
} from "lucide-react";
import { RBCard, RBContent, RBHeader } from "@/components/reactbits";
import { api } from "@/lib/api";

type Classification = "all" | "positive" | "neutral" | "negative";

type NewsArticle = {
    id: string;
    title: string;
    content: string;
    source: string;
    url: string;
    published_at: string | null;
    currencies: string[];
    sentiment_score: number;
    classification: Exclude<Classification, "all">;
};

type NewsResponse = {
    articles: NewsArticle[];
    counts: Record<"positive" | "neutral" | "negative", number>;
    total: number;
    source_table: string;
    generated_at: string;
};

const tabs: Array<{ id: Classification; label: string }> = [
    { id: "all", label: "All" },
    { id: "positive", label: "Positive" },
    { id: "neutral", label: "Neutral" },
    { id: "negative", label: "Negative" },
];

const sentimentMeta = {
    positive: {
        label: "Positive",
        icon: TrendingUp,
        chip: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
        card: "border-emerald-500/20",
    },
    neutral: {
        label: "Neutral",
        icon: MinusCircle,
        chip: "border-slate-500/25 bg-slate-500/10 text-slate-300",
        card: "border-slate-700/70",
    },
    negative: {
        label: "Negative",
        icon: TrendingDown,
        chip: "border-rose-500/25 bg-rose-500/10 text-rose-300",
        card: "border-rose-500/20",
    },
};

function formatPublished(value: string | null) {
    if (!value) return "Unknown time";
    return new Date(value).toLocaleString(undefined, {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function NewsCard({ article }: { article: NewsArticle }) {
    const meta = sentimentMeta[article.classification];
    const Icon = meta.icon;

    return (
        <article className={`rounded-xl border bg-card/75 p-4 transition-colors hover:bg-accent/65 ${meta.card}`}>
            <div className="flex flex-wrap items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${meta.chip}`}>
                    <Icon className="size-3.5" />
                    {meta.label}
                </span>
                <span className="rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                    {article.source || "Unknown source"}
                </span>
                <span className="text-xs text-slate-500">{formatPublished(article.published_at)}</span>
                <span className="ml-auto text-xs font-mono text-slate-500">
                    {article.sentiment_score > 0 ? "+" : ""}
                    {article.sentiment_score.toFixed(2)}
                </span>
            </div>

            <h2 className="mt-3 text-base font-semibold leading-snug text-foreground">{article.title}</h2>
            {article.content && (
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">{article.content}</p>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-2">
                {article.currencies.map((currency) => (
                    <span key={currency} className="rounded-md bg-muted px-2 py-1 text-[11px] font-medium text-muted-foreground">
                        {currency}
                    </span>
                ))}
                {article.url && (
                    <a
                        href={article.url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-blue-300 transition-colors hover:text-brand-blue-200"
                    >
                        Open source
                        <ExternalLink className="size-3.5" />
                    </a>
                )}
            </div>
        </article>
    );
}

export default function NewsPage() {
    const [classification, setClassification] = useState<Classification>("all");
    const [search, setSearch] = useState("");
    const [data, setData] = useState<NewsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");

    const visibleCounts = useMemo(() => {
        const counts = data?.counts ?? { positive: 0, neutral: 0, negative: 0 };
        return {
            all: counts.positive + counts.neutral + counts.negative,
            ...counts,
        };
    }, [data]);

    async function loadNews(nextClassification = classification, nextSearch = search) {
        setLoading(true);
        setError("");
        try {
            const result = await api.recentNews(nextClassification, 50, nextSearch);
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to load news.");
        } finally {
            setLoading(false);
        }
    }

    async function refreshNews() {
        setRefreshing(true);
        setError("");
        try {
            await api.dataIngest.refreshNews();
            await loadNews();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to start news refresh.");
        } finally {
            setRefreshing(false);
        }
    }

    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadNews(classification, search);
        }, 250);
        return () => window.clearTimeout(timer);
    }, [classification, search]);

    return (
        <>
            <RBHeader
                title="News"
                subtitle="Recent market headlines classified as positive, neutral, or negative"
                right={
                    <button
                        type="button"
                        onClick={() => void refreshNews()}
                        disabled={refreshing}
                        className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-accent disabled:opacity-50"
                    >
                        <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
                        Refresh
                    </button>
                }
            />

            <RBContent className="space-y-5">
                <div className="grid gap-3 md:grid-cols-3">
                    {(["positive", "neutral", "negative"] as const).map((key) => {
                        const meta = sentimentMeta[key];
                        const Icon = meta.icon;
                        return (
                            <RBCard key={key} className="p-4">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-xs uppercase tracking-widest text-slate-500">{meta.label}</p>
                                        <p className="mt-2 text-2xl font-semibold text-slate-100">{data?.counts[key] ?? 0}</p>
                                    </div>
                                    <div className={`flex size-10 items-center justify-center rounded-xl border ${meta.chip}`}>
                                        <Icon className="size-5" />
                                    </div>
                                </div>
                            </RBCard>
                        );
                    })}
                </div>

                <RBCard className="p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
                        <div className="flex flex-wrap gap-2">
                            {tabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    type="button"
                                    onClick={() => setClassification(tab.id)}
                                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                                        classification === tab.id
                                            ? "bg-brand-blue-600 text-white"
                                            : "border border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground"
                                    }`}
                                >
                                    <Filter className="size-3.5" />
                                    {tab.label}
                                    <span className="rounded bg-black/15 px-1.5 py-0.5">{visibleCounts[tab.id] ?? 0}</span>
                                </button>
                            ))}
                        </div>

                        <label className="relative ml-auto w-full lg:max-w-sm">
                            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
                            <input
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                placeholder="Search headline, source, or content..."
                                className="h-10 w-full rounded-xl border border-input bg-background/85 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-brand-blue-500/60 focus:outline-none focus:ring-2 focus:ring-brand-blue-500/30"
                            />
                        </label>
                    </div>
                </RBCard>

                {error && (
                    <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                        {error}
                    </div>
                )}

                <div className="grid gap-3">
                    {loading ? (
                        <RBCard className="flex min-h-48 items-center justify-center p-8 text-sm text-slate-500">
                            <RefreshCw className="mr-2 size-4 animate-spin" />
                            Loading news
                        </RBCard>
                    ) : data?.articles.length ? (
                        data.articles.map((article) => <NewsCard key={article.id || article.title} article={article} />)
                    ) : (
                        <RBCard className="flex min-h-64 flex-col items-center justify-center p-8 text-center">
                            <Newspaper className="size-10 text-slate-600" />
                            <p className="mt-3 text-sm font-semibold text-foreground">No recent news found</p>
                            <p className="mt-1 max-w-md text-sm text-slate-500">
                                Try refreshing the news feed or clearing the current filters.
                            </p>
                        </RBCard>
                    )}
                </div>
            </RBContent>
        </>
    );
}
