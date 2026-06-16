"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { GraduationCap, Upload } from "lucide-react";
import { RBContent, RBHeader } from "@/components/reactbits";
import DocumentUpload from "@/components/rag/DocumentUpload";
import DocumentList from "@/components/rag/DocumentList";
import QueryChat from "@/components/rag/QueryChat";

export default function StrategyTutorPage() {
    const { data: session } = useSession();
    const isAuthenticated = Boolean(session?.user?.email);

    const [refreshKey, setRefreshKey] = useState(0);
    const [documentCount, setDocumentCount] = useState(0);

    function onDocUploaded() {
        setRefreshKey((k) => k + 1);
        setDocumentCount((count) => Math.max(count, 1));
    }

    return (
        <>
            <RBHeader
                title="Strategy Tutor"
                subtitle="Ask questions about your uploaded trading documents across text, images, audio, and video"
                right={
                    <div className="flex items-center gap-1.5 rounded-lg border border-border bg-muted/65 px-3 py-1.5 text-xs text-muted-foreground">
                        <GraduationCap className="size-3.5 text-brand-blue-400" />
                        Educational use only - Not financial advice
                    </div>
                }
            />

            <RBContent>
                <div className="grid h-full grid-cols-1 gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
                    <div className="flex min-h-0 flex-col gap-4">
                        <div className="rounded-2xl border border-border bg-card/70 p-5">
                            <div className="mb-4 flex items-start gap-3">
                                <div>
                                    <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                                        <Upload className="size-4 text-sky-400" />
                                        Add knowledge
                                    </h3>
                                    <p className="mt-1 text-xs leading-5 text-muted-foreground">
                                        Drop multimodal evidence into your strategy knowledge base.
                                    </p>
                                </div>
                            </div>
                            {isAuthenticated ? (
                                <DocumentUpload onUploaded={onDocUploaded} />
                            ) : (
                                <p className="text-sm text-muted-foreground">Please log in to upload documents.</p>
                            )}
                        </div>

                        <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-border bg-card/70 p-5">
                            <DocumentList
                                refreshKey={refreshKey}
                                onDocumentsChange={setDocumentCount}
                            />
                        </div>
                    </div>

                    <div className="flex min-h-[720px] flex-col rounded-2xl border border-border bg-card/65 p-5">
                        <div className="mb-4 flex shrink-0 items-center justify-between gap-3">
                            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                            <GraduationCap className="size-4 text-violet-400" />
                            Ask Your Documents
                            </h3>
                            <div className="hidden items-center gap-2 md:flex">
                                <span className="rounded-full border border-border bg-muted/70 px-2.5 py-1 text-xs text-muted-foreground">
                                    {documentCount} indexed file{documentCount === 1 ? "" : "s"}
                                </span>
                            </div>
                        </div>
                        {isAuthenticated ? (
                            <QueryChat hasDocs={documentCount > 0} />
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                Please log in to use the Strategy Tutor.
                            </p>
                        )}
                    </div>
                </div>
            </RBContent>
        </>
    );
}
