"use client";

import { SessionProvider } from "next-auth/react";
import { createContext, useMemo } from "react";
import { usePageAgentCore, PageAgentContext } from "@/hooks/use-page-agent";

/**
 * PageAgentProvider — initialises the PageAgent hook and exposes its state
 * via PageAgentContext to all descendants.
 */
function PageAgentProvider({ children }: { children: React.ReactNode }) {
    const pageAgentState = usePageAgentCore();
    return (
        <PageAgentContext.Provider value={pageAgentState}>
            {children}
        </PageAgentContext.Provider>
    );
}

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            <PageAgentProvider>
                {children}
            </PageAgentProvider>
        </SessionProvider>
    );
}

