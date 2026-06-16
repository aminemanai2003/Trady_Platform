"use client";

import { SessionProvider } from "next-auth/react";
import { usePageAgentCore, PageAgentContext } from "@/hooks/use-page-agent";
import { AccessibilityProvider } from "@/components/accessibility-provider";
import { ThemeProvider } from "@/components/theme-provider";

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
            <ThemeProvider>
                <AccessibilityProvider>
                    <PageAgentProvider>
                        {children}
                    </PageAgentProvider>
                </AccessibilityProvider>
            </ThemeProvider>
        </SessionProvider>
    );
}

