"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { Check, Crown, Sparkles, Star, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type PlanKey = "basic" | "plus" | "pro";

type Plan = {
    id: string;
    plan: PlanKey;
    name: string;
    tagline: string;
    price: string;
    yearly: string;
    image: string;
    badge: string;
    cta: string;
    featured?: boolean;
    accent: "basic" | "plus" | "pro";
    icon: typeof Star;
    features: string[];
    limits: string[];
};

const plans: Plan[] = [
    {
        id: "trady-basic",
        plan: "basic",
        name: "Trady Basic",
        tagline: "Start learning, monitoring, and testing the platform.",
        price: "Free",
        yearly: "No card needed",
        image: "/pricing/trady-basic.png",
        badge: "Current starter plan",
        cta: "Switch to Basic",
        accent: "basic",
        icon: Star,
        features: [
            "Dashboard and news",
            "Basic monitoring access",
            "Text/PDF Strategy Tutor uploads",
            "3 signal generations per month",
        ],
        limits: ["1 tutor document", "No video tutor", "No advanced backtesting"],
    },
    {
        id: "trady-plus",
        plan: "plus",
        name: "Trady Plus",
        tagline: "For active learners who want richer local AI workflows.",
        price: "29 TND",
        yearly: "290 TND yearly",
        image: "/pricing/trady-plus.png",
        badge: "Best upgrade",
        cta: "Upgrade to Plus",
        accent: "plus",
        icon: Zap,
        features: [
            "100 signal generations per month",
            "Text, image, and audio Strategy Tutor",
            "Signal reports access",
            "Backtesting up to 30 days",
        ],
        limits: ["20 tutor documents", "Standard agent monitor", "Basic support"],
    },
    {
        id: "trady-pro",
        plan: "pro",
        name: "Trady Pro",
        tagline: "Flagship multimodal and agentic research.",
        price: "89 TND",
        yearly: "890 TND yearly",
        image: "/pricing/trady-pro.png",
        badge: "Most powerful",
        cta: "Upgrade to Pro",
        featured: true,
        accent: "pro",
        icon: Crown,
        features: [
            "500 signal generations per month",
            "Full multimodal tutor including video",
            "Advanced monitoring and agent workflows",
            "Backtesting up to 1 year",
        ],
        limits: ["100 tutor documents", "Richer reports", "Priority local processing"],
    },
];

const accentStyles = {
    basic: {
        card: "border-brand-blue-500/20 bg-brand-blue-500/[0.04]",
        badge: "border-brand-blue-400/30 bg-brand-blue-500/10 text-brand-blue-700 dark:text-brand-blue-200",
        icon: "bg-brand-blue-500/15 text-brand-blue-600 dark:text-brand-blue-300",
        button: "border-brand-blue-400/30 text-brand-blue-700 hover:bg-brand-blue-500/10 dark:text-brand-blue-100",
    },
    plus: {
        card: "border-amber-400/25 bg-amber-400/[0.05]",
        badge: "border-amber-400/40 bg-amber-400/10 text-amber-700 dark:text-amber-200",
        icon: "bg-amber-400/15 text-amber-700 dark:text-amber-200",
        button: "bg-amber-300 text-slate-950 hover:bg-amber-200",
    },
    pro: {
        card: "border-yellow-300/45 bg-yellow-300/[0.07] shadow-[0_0_45px_rgba(250,204,21,0.16)]",
        badge: "border-yellow-400/50 bg-yellow-300/15 text-yellow-800 dark:text-yellow-100",
        icon: "bg-yellow-300/20 text-yellow-800 dark:text-yellow-100",
        button: "bg-gradient-to-r from-yellow-200 via-amber-300 to-yellow-500 text-slate-950 hover:brightness-110",
    },
} satisfies Record<Plan["accent"], Record<string, string>>;

export default function BillingPage() {
    const [currentPlan, setCurrentPlan] = useState<PlanKey>("basic");
    const [loadingPlan, setLoadingPlan] = useState<PlanKey | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        let active = true;

        async function loadBilling() {
            try {
                const params = new URLSearchParams(window.location.search);
                const checkout = params.get("checkout");
                const sessionId = params.get("session_id");

                if (checkout === "success" && sessionId) {
                    setMessage("Verifying Stripe payment...");
                    const completed = await fetch("/api/billing/complete", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ sessionId }),
                    });
                    // Some failure modes (server crash, hung route, gateway) yield
                    // an empty or non-JSON body. Read once and parse defensively so
                    // we surface a useful message instead of "Unexpected end of
                    // JSON input".
                    const raw = await completed.text();
                    let completedData: { error?: string; subscription?: { plan?: PlanKey } } = {};
                    try {
                        completedData = raw ? JSON.parse(raw) : {};
                    } catch {
                        completedData = {};
                    }
                    if (!completed.ok) {
                        throw new Error(
                            completedData.error
                                || raw.slice(0, 200)
                                || `Stripe payment verification failed (HTTP ${completed.status})`
                        );
                    }
                    if (active && completedData.subscription?.plan) {
                        setCurrentPlan(completedData.subscription.plan);
                        window.dispatchEvent(new CustomEvent("trady:billing-updated", { detail: completedData.subscription }));
                        setMessage(`Payment confirmed. Your account is now on ${plans.find((item) => item.plan === completedData.subscription!.plan)?.name ?? "the selected plan"}.`);
                    }
                    window.history.replaceState(null, "", "/billing");
                    return;
                }

                if (checkout === "cancelled") {
                    setMessage("Checkout cancelled. Your plan was not changed.");
                    window.history.replaceState(null, "", "/billing");
                }

                const response = await fetch("/api/billing/me");
                if (!response.ok) return;
                const data = await response.json();
                if (active && data.subscription?.plan) {
                    setCurrentPlan(data.subscription.plan);
                }
            } catch (error) {
                console.error("Failed to load billing", error);
            }
        }

        void loadBilling();
        return () => {
            active = false;
        };
    }, []);

    async function updatePlan(plan: PlanKey) {
        setLoadingPlan(plan);
        setMessage(null);

        try {
            const endpoint = plan === "basic" ? "/api/billing/subscribe" : "/api/billing/checkout";
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ plan, billingInterval: "monthly" }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Plan update failed");
            }

            if (data.url) {
                window.location.href = data.url;
                return;
            }

            setCurrentPlan(data.subscription.plan);
            window.dispatchEvent(new CustomEvent("trady:billing-updated", { detail: data.subscription }));
            setMessage(`Your account is now on ${plans.find((item) => item.plan === data.subscription.plan)?.name ?? "the selected plan"}.`);
        } catch (error) {
            setMessage(error instanceof Error ? error.message : "Plan update failed");
        } finally {
            setLoadingPlan(null);
        }
    }

    return (
        <main className="min-h-screen bg-background text-foreground">
            <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
                <header className="flex flex-col gap-4 border-b border-border pb-6 lg:flex-row lg:items-end lg:justify-between">
                    <div className="space-y-3">
                        <Badge className="border-brand-green-400/30 bg-brand-green-500/10 text-brand-green-700 dark:text-brand-green-200" variant="outline">
                            Plans & subscriptions
                        </Badge>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Choose your Trady plan</h1>
                            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                                Start free, upgrade to Plus for stronger daily workflows, or unlock the full local multimodal stack with Pro.
                            </p>
                        </div>
                    </div>
                    <div className="rounded-lg border border-border bg-card/75 px-4 py-3 text-sm text-muted-foreground">
                        <span className="font-semibold text-foreground">Current plan:</span>{" "}
                        {plans.find((plan) => plan.plan === currentPlan)?.name ?? "Trady Basic"}
                        <div className="mt-1 text-xs text-slate-500">Stripe checkout charges EUR equivalent.</div>
                    </div>
                </header>

                {message && (
                    <div className="rounded-lg border border-brand-blue-400/25 bg-brand-blue-500/10 px-4 py-3 text-sm text-brand-blue-100">
                        {message}
                    </div>
                )}

                <section className="grid gap-5 lg:grid-cols-3">
                    {plans.map((plan) => {
                        const styles = accentStyles[plan.accent];
                        const Icon = plan.icon;
                        const isCurrent = currentPlan === plan.plan;
                        const isLoading = loadingPlan === plan.plan;

                        return (
                            <article
                                key={plan.id}
                                className={`relative flex min-h-full flex-col overflow-hidden rounded-xl border ${styles.card}`}
                            >
                                {plan.featured && (
                                    <div className="absolute right-4 top-4 z-10 rounded-full border border-yellow-200/40 bg-yellow-300/15 px-3 py-1 text-xs font-semibold text-yellow-100 backdrop-blur">
                                        Best tier
                                    </div>
                                )}

                                <div className="relative aspect-square w-full overflow-hidden bg-black">
                                    <Image
                                        src={plan.image}
                                        alt={`${plan.name} plan artwork`}
                                        fill
                                        priority={plan.featured}
                                        sizes="(min-width: 1024px) 33vw, 100vw"
                                        className="object-cover"
                                    />
                                    <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-slate-950 to-transparent" />
                                </div>

                                <div className="flex flex-1 flex-col gap-5 p-5">
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex items-center gap-3">
                                                <span className={`flex size-10 items-center justify-center rounded-lg ${styles.icon}`}>
                                                    <Icon className="size-5" />
                                                </span>
                                                <div>
                                                    <h2 className="text-xl font-bold text-foreground">{plan.name}</h2>
                                                    <p className="text-xs text-muted-foreground">{plan.tagline}</p>
                                                </div>
                                            </div>
                                        </div>
                                        <Badge className={styles.badge} variant="outline">
                                            {isCurrent ? "Current plan" : plan.badge}
                                        </Badge>
                                    </div>

                                    <div className="flex items-end gap-2">
                                        <span className="text-3xl font-black text-foreground">{plan.price}</span>
                                        {plan.price !== "Free" && <span className="pb-1 text-sm text-muted-foreground">/ month</span>}
                                    </div>
                                    <p className="text-xs text-muted-foreground">{plan.yearly}</p>

                                    <Button
                                        disabled={isCurrent || loadingPlan !== null}
                                        onClick={() => void updatePlan(plan.plan)}
                                        className={`w-full border ${
                                            isCurrent
                                                ? "cursor-default border-white/10 bg-white/[0.04] text-slate-500 opacity-100"
                                                : plan.plan === "basic"
                                                    ? "border-brand-blue-400/40 bg-brand-blue-500/10 text-brand-blue-100 hover:bg-brand-blue-500/20"
                                                    : styles.button
                                        }`}
                                        variant="default"
                                    >
                                        {isLoading
                                            ? plan.plan === "basic" ? "Switching..." : "Opening Stripe..."
                                            : isCurrent
                                                ? "Current plan"
                                                : plan.plan === "basic" ? "Downgrade to Basic" : plan.cta}
                                    </Button>

                                    <div className="space-y-3 pt-2">
                                        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Included</h3>
                                        <ul className="space-y-2">
                                            {plan.features.map((feature) => (
                                                <li key={feature} className="flex gap-2 text-sm text-foreground/85">
                                                    <Check className="mt-0.5 size-4 shrink-0 text-brand-green-300" />
                                                    <span>{feature}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div className="mt-auto rounded-lg border border-border bg-card/65 p-3">
                                        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
                                            <Sparkles className="size-3.5" />
                                            Limits
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {plan.limits.map((limit) => (
                                                <span key={limit} className="rounded-full border border-border px-2 py-1 text-xs text-muted-foreground">
                                                    {limit}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </article>
                        );
                    })}
                </section>
            </div>
        </main>
    );
}
