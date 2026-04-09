"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { RBButton } from "@/components/reactbits";

interface Props {
    onUploaded: () => void;
}

type FileStatus = "pending" | "uploading" | "done" | "error";

interface FileEntry {
    file:    File;
    status:  FileStatus;
    message: string;
}

const ALLOWED_EXTS  = [".pdf", ".txt"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;

function validateFile(f: File): string | null {
    const ext = "." + f.name.split(".").pop()!.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) return "Only PDF and TXT files are supported.";
    if (f.size > MAX_SIZE_BYTES) return "File exceeds 10 MB limit.";
    return null;
}

export default function DocumentUpload({ onUploaded }: Props) {
    const inputRef            = useRef<HTMLInputElement>(null);
    const [entries, setEntries] = useState<FileEntry[]>([]);
    const [topic,   setTopic]   = useState("");
    const [drag,    setDrag]    = useState(false);
    const [busy,    setBusy]    = useState(false);

    function addFiles(fileList: FileList | null) {
        if (!fileList) return;
        const next: FileEntry[] = [];
        for (const f of Array.from(fileList)) {
            const err = validateFile(f);
            next.push({ file: f, status: err ? "error" : "pending", message: err ?? "" });
        }
        setEntries((prev) => [...prev, ...next]);
    }

    function removeEntry(idx: number) {
        setEntries((prev) => prev.filter((_, i) => i !== idx));
    }

    function onDrop(e: React.DragEvent) {
        e.preventDefault();
        setDrag(false);
        addFiles(e.dataTransfer.files);
    }

    async function handleUpload() {
        const pending = entries.filter((e) => e.status === "pending");
        if (!pending.length) return;
        setBusy(true);

        for (const entry of pending) {
            // Mark as uploading
            setEntries((prev) =>
                prev.map((e) =>
                    e.file === entry.file ? { ...e, status: "uploading", message: "" } : e
                )
            );

            const fd = new FormData();
            fd.append("file",  entry.file);
            fd.append("topic", topic);

            try {
                const res  = await fetch("/api/rag/upload", { method: "POST", body: fd });
                const data = await res.json();

                if (!res.ok) {
                    setEntries((prev) =>
                        prev.map((e) =>
                            e.file === entry.file
                                ? { ...e, status: "error", message: data.error ?? "Upload failed." }
                                : e
                        )
                    );
                } else {
                    setEntries((prev) =>
                        prev.map((e) =>
                            e.file === entry.file
                                ? { ...e, status: "done", message: `${data.chunk_count} chunks indexed` }
                                : e
                        )
                    );
                    onUploaded();
                }
            } catch {
                setEntries((prev) =>
                    prev.map((e) =>
                        e.file === entry.file
                            ? { ...e, status: "error", message: "Network error." }
                            : e
                    )
                );
            }
        }

        setBusy(false);
        if (inputRef.current) inputRef.current.value = "";
        setTopic("");
    }

    const pendingCount  = entries.filter((e) => e.status === "pending").length;
    const hasAnyEntries = entries.length > 0;

    return (
        <div className="space-y-4">
            {/* Drop zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`
                    relative flex flex-col items-center justify-center gap-3
                    rounded-xl border-2 border-dashed p-8 cursor-pointer
                    transition-colors duration-150
                    ${drag
                        ? "border-sky-500 bg-sky-500/10"
                        : hasAnyEntries
                        ? "border-emerald-500/50 bg-emerald-500/5"
                        : "border-slate-600 bg-slate-800/40 hover:border-sky-500/60 hover:bg-sky-500/5"
                    }
                `}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,.txt"
                    multiple
                    className="hidden"
                    onChange={(e) => addFiles(e.target.files)}
                />
                <Upload className="size-9 text-slate-500" />
                <div className="text-center">
                    <p className="text-sm text-slate-300">
                        Drop files here or <span className="text-sky-400 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">PDF or TXT · max 10 MB each · multiple files supported</p>
                </div>
            </div>

            {/* File list */}
            {hasAnyEntries && (
                <div className="space-y-2">
                    {entries.map((entry, idx) => (
                        <div
                            key={idx}
                            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm border ${
                                entry.status === "done"      ? "bg-emerald-500/10 border-emerald-500/20" :
                                entry.status === "error"     ? "bg-rose-500/10 border-rose-500/20" :
                                entry.status === "uploading" ? "bg-sky-500/10 border-sky-500/20" :
                                "bg-slate-800/60 border-slate-700/50"
                            }`}
                        >
                            {entry.status === "uploading" ? (
                                <Loader2 className="size-4 animate-spin text-sky-400 shrink-0" />
                            ) : entry.status === "done" ? (
                                <CheckCircle2 className="size-4 text-emerald-400 shrink-0" />
                            ) : entry.status === "error" ? (
                                <AlertCircle className="size-4 text-rose-400 shrink-0" />
                            ) : (
                                <FileText className="size-4 text-slate-400 shrink-0" />
                            )}

                            <div className="flex-1 min-w-0">
                                <p className="truncate text-slate-200 font-medium">{entry.file.name}</p>
                                {entry.message && (
                                    <p className={`text-xs mt-0.5 ${entry.status === "error" ? "text-rose-400" : "text-emerald-400"}`}>
                                        {entry.message}
                                    </p>
                                )}
                            </div>

                            <span className="text-xs text-slate-500 shrink-0">
                                {(entry.file.size / 1024).toFixed(0)} KB
                            </span>

                            {entry.status !== "uploading" && (
                                <button
                                    type="button"
                                    onClick={() => removeEntry(idx)}
                                    className="text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                                >
                                    <X className="size-4" />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Optional topic */}
            {pendingCount > 0 && (
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Topic / label (optional, applies to all)"
                    className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
            )}

            {/* Upload button */}
            {pendingCount > 0 && (
                <RBButton
                    className="w-full"
                    onClick={handleUpload}
                    disabled={busy}
                >
                    {busy ? (
                        <><Loader2 className="size-4 animate-spin" /> Uploading…</>
                    ) : (
                        <><Upload className="size-4" /> Upload {pendingCount} file{pendingCount > 1 ? "s" : ""}</>
                    )}
                </RBButton>
            )}
        </div>
    );
}
