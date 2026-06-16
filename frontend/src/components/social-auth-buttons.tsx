"use client";

import { useEffect, useState } from "react";
import { getProviders, signIn } from "next-auth/react";
import type { ClientSafeProvider } from "next-auth/react";
import { Github } from "lucide-react";

type ProviderMap = Record<string, ClientSafeProvider>;

const providerLabels: Record<string, string> = {
    google: "Continue with Google",
    github: "Continue with GitHub",
};

const desiredProviders = ["google", "github"] as const;

function GoogleMark() {
    return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="size-4">
            <path fill="#4285F4" d="M22.6 12.2c0-.8-.1-1.5-.2-2.2H12v4.2h5.9c-.3 1.3-1 2.4-2.1 3.1v2.6h3.4c2-1.8 3.1-4.5 3.1-7.7z" />
            <path fill="#34A853" d="M12 23c2.8 0 5.2-.9 6.9-2.5l-3.4-2.6c-.9.6-2.1 1-3.5 1-2.7 0-5-1.8-5.8-4.3H2.7v2.7C4.4 20.6 7.8 23 12 23z" />
            <path fill="#FBBC05" d="M6.2 14.6c-.2-.6-.3-1.3-.3-2s.1-1.4.3-2V7.9H2.7C1.9 9.3 1.5 10.6 1.5 12s.4 2.7 1.2 4z" />
            <path fill="#EA4335" d="M12 5.4c1.5 0 2.9.5 4 1.6l3-3C17.2 2.3 14.8 1 12 1 7.8 1 4.4 3.4 2.7 7.9l3.5 2.7C7 7.2 9.3 5.4 12 5.4z" />
        </svg>
    );
}

export function SocialAuthButtons({ mode }: { mode: "login" | "register" }) {
    const [providers, setProviders] = useState<ClientSafeProvider[]>([]);
    const [loadingProvider, setLoadingProvider] = useState<string | null>(null);

    useEffect(() => {
        let mounted = true;
        void getProviders().then((result: ProviderMap | null) => {
            if (!mounted) return;
            setProviders(Object.values(result ?? {}).filter((provider) => provider.id !== "credentials"));
        });
        return () => {
            mounted = false;
        };
    }, []);

    const providerById = Object.fromEntries(providers.map((provider) => [provider.id, provider]));

    return (
        <div className="space-y-3">
            <div className="relative">
                <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-800/80" />
                </div>
                <div className="relative flex justify-center text-xs">
                    <span className="bg-slate-950 px-2 text-slate-500">
                        {mode === "login" ? "or sign in with" : "or continue with"}
                    </span>
                </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
                {desiredProviders.map((providerId) => {
                    const provider = providerById[providerId];
                    const enabled = Boolean(provider);
                    return (
                        <button
                            key={providerId}
                            type="button"
                            onClick={() => {
                                if (!provider) return;
                                setLoadingProvider(provider.id);
                                void signIn(provider.id, { callbackUrl: "/dashboard" });
                            }}
                            disabled={!enabled || loadingProvider !== null}
                            title={enabled ? providerLabels[providerId] : `${providerLabels[providerId]} needs provider keys configured`}
                            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900/70 px-3 text-sm font-semibold text-slate-100 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-45"
                        >
                            {providerId === "google" ? <GoogleMark /> : <Github className="size-4" />}
                            {loadingProvider === providerId ? "Opening..." : providerLabels[providerId]}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
