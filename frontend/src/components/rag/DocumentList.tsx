"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, FileType2, Loader2, RefreshCw } from "lucide-react";
import { RagDocument, RagDocumentCard, RagKnowledgeStats } from "@/components/rag/rag-ui";

const PAGE_SIZE = 20;

interface Props {
    refreshKey: number;
    onDocumentsChange?: (count: number) => void;
}

export default function DocumentList({ refreshKey, onDocumentsChange }: Props) {
    const [docs, setDocs] = useState<RagDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [deleting, setDeleting] = useState<string | null>(null);
    const [page, setPage] = useState(1);

    const totalPages = Math.max(1, Math.ceil(docs.length / PAGE_SIZE));
    const visibleDocs = docs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    const loadDocs = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const res = await fetch("/api/rag/documents");
            const data = await res.json();
            if (!res.ok) {
                setError(data.error ?? "Failed to load documents.");
            } else {
                const documents = data.documents ?? [];
                setDocs(documents);
                setPage(1);
                onDocumentsChange?.(documents.length);
            }
        } catch {
            setError("Network error loading documents.");
        } finally {
            setLoading(false);
        }
    }, [onDocumentsChange]);

    useEffect(() => {
        void loadDocs();
    }, [loadDocs, refreshKey]);

    async function handleDelete(doc: RagDocument) {
        if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
        setDeleting(doc.id);
        try {
            const res = await fetch("/api/rag/documents", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ doc_id: doc.id }),
            });
            const data = await res.json();
            if (data.deleted) {
                const next = docs.filter((d) => d.id !== doc.id);
                setDocs(next);
                onDocumentsChange?.(next.length);
                const newTotal = Math.max(1, Math.ceil(next.length / PAGE_SIZE));
                setPage((p) => Math.min(p, newTotal));
            } else {
                setError(data.error ?? "Delete failed.");
            }
        } catch {
            setError("Network error deleting document.");
        } finally {
            setDeleting(null);
        }
    }

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">Knowledge base</h3>
                <button
                    type="button"
                    onClick={() => void loadDocs()}
                    className="text-slate-500 hover:text-sky-400 transition-colors"
                    title="Refresh"
                >
                    <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
                </button>
            </div>

            {error && (
                <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
                    {error}
                </p>
            )}

            {docs.length > 0 && <RagKnowledgeStats docs={docs} />}

            {loading && docs.length === 0 && (
                <div className="flex items-center gap-2 text-sm text-slate-500 py-4 justify-center">
                    <Loader2 className="size-4 animate-spin" />
                    Loading documents...
                </div>
            )}

            {!loading && docs.length === 0 && !error && (
                <div className="text-center py-6 text-slate-600 text-sm">
                    <FileType2 className="size-8 mx-auto mb-2 opacity-40" />
                    No documents yet. Upload a PDF, image, audio, video, or TXT/MD file to get started.
                </div>
            )}

            <ul className="space-y-2">
                {visibleDocs.map((doc) => (
                    <RagDocumentCard
                        key={doc.id}
                        doc={doc}
                        deleting={deleting === doc.id}
                        onDelete={() => void handleDelete(doc)}
                    />
                ))}
            </ul>

            {totalPages > 1 && (
                <div className="flex items-center justify-between pt-1">
                    <button
                        type="button"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        <ChevronLeft className="size-3.5" /> Prev
                    </button>
                    <span className="text-xs text-slate-600">
                        {page} / {totalPages}
                    </span>
                    <button
                        type="button"
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="flex items-center gap-1 text-xs text-slate-500 hover:text-sky-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        Next <ChevronRight className="size-3.5" />
                    </button>
                </div>
            )}
        </div>
    );
}
