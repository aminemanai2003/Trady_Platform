"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { GraduationCap, BookOpen, Upload } from "lucide-react";
import { RBContent, RBHeader } from "@/components/reactbits";
import DocumentUpload from "@/components/rag/DocumentUpload";
import DocumentList   from "@/components/rag/DocumentList";
import QueryChat      from "@/components/rag/QueryChat";

type Tab = "chat" | "upload";

export default function StrategyTutorPage() {
    const { data: session } = useSession();
    const isAuthenticated = Boolean(session?.user?.email);

    const [tab,        setTab]        = useState<Tab>("chat");
    const [refreshKey, setRefreshKey] = useState(0);
    const [documentCount, setDocumentCount] = useState(0);

    function onDocUploaded() {
        setRefreshKey((k) => k + 1);
        setDocumentCount((count) => Math.max(count, 1));
        setTab("chat");
    }

    return (
        <>
            <RBHeader
                title="Strategy Tutor"
                subtitle="Ask questions about your uploaded trading documents — powered by Gemini AI"
                right={
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-800/60 border border-slate-700/50 rounded-lg px-3 py-1.5">
                        <GraduationCap className="size-3.5 text-violet-400" />
                        Educational use only · Not financial advice
                    </div>
                }
            />

            <RBContent>
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-full">

                    {/* ── Left panel: documents ───────────────────────────── */}
                    <div className="xl:col-span-1 flex flex-col gap-4">
                        {/* Tabs */}
                        <div className="flex rounded-xl bg-slate-800/60 border border-slate-700/50 p-1 gap-1">
                            <button
                                type="button"
                                onClick={() => setTab("upload")}
                                className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-medium transition-colors ${
                                    tab === "upload"
                                        ? "bg-sky-600 text-white"
                                        : "text-slate-400 hover:text-slate-200"
                                }`}
                            >
                                <Upload className="size-3.5" />
                                Upload
                            </button>
                            <button
                                type="button"
                                onClick={() => setTab("chat")}
                                className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-xs font-medium transition-colors ${
                                    tab === "chat"
                                        ? "bg-violet-600 text-white"
                                        : "text-slate-400 hover:text-slate-200"
                                }`}
                            >
                                <BookOpen className="size-3.5" />
                                My Docs
                            </button>
                        </div>

                        {/* Panel content */}
                        <div className="rounded-2xl bg-slate-900/60 border border-slate-700/50 p-5 flex-1">
                            {tab === "upload" ? (
                                <>
                                    <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                                        <Upload className="size-4 text-sky-400" />
                                        Upload Document
                                    </h3>
                                    {isAuthenticated ? (
                                        <DocumentUpload
                                            onUploaded={onDocUploaded}
                                        />
                                    ) : (
                                        <p className="text-sm text-slate-500">
                                            Please log in to upload documents.
                                        </p>
                                    )}
                                </>
                            ) : (
                                <DocumentList
                                    refreshKey={refreshKey}
                                    onDocumentsChange={setDocumentCount}
                                />
                            )}
                        </div>
                    </div>

                    {/* ── Right panel: chat ───────────────────────────────── */}
                    <div className="xl:col-span-2 rounded-2xl bg-slate-900/60 border border-slate-700/50 p-5 flex flex-col">
                        <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2 shrink-0">
                            <GraduationCap className="size-4 text-violet-400" />
                            Ask Your Documents
                        </h3>
                        {isAuthenticated ? (
                            <QueryChat
                                hasDocs={documentCount > 0}
                            />
                        ) : (
                            <p className="text-sm text-slate-500">
                                Please log in to use the Strategy Tutor.
                            </p>
                        )}
                    </div>
                </div>
            </RBContent>
        </>
    );
}
