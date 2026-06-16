"use client";

import { useRef, useState } from "react";
import { AlertCircle, CheckCircle2, FileText, Loader2, Upload, X } from "lucide-react";
import { RBButton } from "@/components/reactbits";
import { RagBadge } from "@/components/rag/rag-ui";

interface Props {
    onUploaded: () => void;
}

type FileStatus = "pending" | "uploading" | "done" | "error";

interface FileEntry {
    file: File;
    status: FileStatus;
    message: string;
}

const ALLOWED_EXTS = [
    ".pdf", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg",
    ".mp4", ".mov", ".mkv", ".webm", ".avi",
];
const TEXT_EXTS = new Set([".pdf", ".txt", ".md"]);
const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".bmp"]);
const AUDIO_EXTS = new Set([".mp3", ".wav", ".m4a", ".flac", ".ogg"]);
const VIDEO_EXTS = new Set([".mp4", ".mov", ".mkv", ".webm", ".avi"]);

function maxSizeForExt(ext: string) {
    if (TEXT_EXTS.has(ext)) return { bytes: 10 * 1024 * 1024, label: "10 MB" };
    if (IMAGE_EXTS.has(ext)) return { bytes: 15 * 1024 * 1024, label: "15 MB" };
    if (AUDIO_EXTS.has(ext)) return { bytes: 50 * 1024 * 1024, label: "50 MB" };
    if (VIDEO_EXTS.has(ext)) return { bytes: 250 * 1024 * 1024, label: "250 MB" };
    return null;
}

function validateFile(file: File): string | null {
    const ext = "." + file.name.split(".").pop()!.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) return "Supported files: PDF, TXT, MD, images, audio, and video.";
    const limit = maxSizeForExt(ext);
    if (limit && file.size > limit.bytes) return `File exceeds ${limit.label} limit.`;
    return null;
}

export default function DocumentUpload({ onUploaded }: Props) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [entries, setEntries] = useState<FileEntry[]>([]);
    const [topic, setTopic] = useState("");
    const [drag, setDrag] = useState(false);
    const [busy, setBusy] = useState(false);

    function addFiles(fileList: FileList | null) {
        if (!fileList) return;
        const next: FileEntry[] = [];
        for (const file of Array.from(fileList)) {
            const error = validateFile(file);
            next.push({ file, status: error ? "error" : "pending", message: error ?? "" });
        }
        setEntries((prev) => [...prev, ...next]);
    }

    function removeEntry(index: number) {
        setEntries((prev) => prev.filter((_, i) => i !== index));
    }

    function onDrop(event: React.DragEvent) {
        event.preventDefault();
        setDrag(false);
        addFiles(event.dataTransfer.files);
    }

    async function handleUpload() {
        const pending = entries.filter((entry) => entry.status === "pending");
        if (!pending.length) return;
        setBusy(true);

        for (const entry of pending) {
            setEntries((prev) =>
                prev.map((item) =>
                    item.file === entry.file ? { ...item, status: "uploading", message: "" } : item
                )
            );

            const formData = new FormData();
            formData.append("file", entry.file);
            formData.append("topic", topic);

            try {
                const response = await fetch("/api/rag/upload", { method: "POST", body: formData });
                const data = await response.json();

                if (!response.ok) {
                    setEntries((prev) =>
                        prev.map((item) =>
                            item.file === entry.file
                                ? { ...item, status: "error", message: data.error ?? "Upload failed." }
                                : item
                        )
                    );
                } else {
                    setEntries((prev) =>
                        prev.map((item) =>
                            item.file === entry.file
                                ? {
                                    ...item,
                                    status: "done",
                                    message: `${data.modality ?? "document"} - ${data.chunk_count} chunks indexed`,
                                }
                                : item
                        )
                    );
                    onUploaded();
                }
            } catch {
                setEntries((prev) =>
                    prev.map((item) =>
                        item.file === entry.file
                            ? { ...item, status: "error", message: "Network error." }
                            : item
                    )
                );
            }
        }

        setBusy(false);
        if (inputRef.current) inputRef.current.value = "";
        setTopic("");
    }

    const pendingCount = entries.filter((entry) => entry.status === "pending").length;
    const hasAnyEntries = entries.length > 0;

    return (
        <div className="space-y-4">
            <div
                onDragOver={(event) => { event.preventDefault(); setDrag(true); }}
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
                    accept={ALLOWED_EXTS.join(",")}
                    multiple
                    className="hidden"
                    onChange={(event) => addFiles(event.target.files)}
                />
                <Upload className="size-9 text-slate-500" />
                <div className="text-center">
                    <p className="text-sm text-foreground">
                        Drop files here or <span className="text-sky-400 underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                        PDF/TXT 10 MB, images 15 MB, audio 50 MB, video 250 MB
                    </p>
                    <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                        <RagBadge modality="text" />
                        <RagBadge modality="image" />
                        <RagBadge modality="audio" />
                        <RagBadge modality="video" />
                    </div>
                </div>
            </div>

            {hasAnyEntries && (
                <div className="space-y-2">
                    {entries.map((entry, index) => (
                        <div
                            key={`${entry.file.name}-${index}`}
                            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm border ${
                                entry.status === "done" ? "bg-emerald-500/10 border-emerald-500/20" :
                                entry.status === "error" ? "bg-rose-500/10 border-rose-500/20" :
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
                                <FileText className="size-4 text-muted-foreground shrink-0" />
                            )}

                            <div className="flex-1 min-w-0">
                                <p className="truncate text-foreground font-medium">{entry.file.name}</p>
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
                                    onClick={() => removeEntry(index)}
                                    className="text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                                    title="Remove file"
                                >
                                    <X className="size-4" />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {pendingCount > 0 && (
                <input
                    type="text"
                    value={topic}
                    onChange={(event) => setTopic(event.target.value)}
                    placeholder="Topic / label (optional, applies to all)"
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
            )}

            {pendingCount > 0 && (
                <RBButton className="w-full" onClick={handleUpload} disabled={busy}>
                    {busy ? (
                        <><Loader2 className="size-4 animate-spin" /> Uploading...</>
                    ) : (
                        <><Upload className="size-4" /> Upload {pendingCount} file{pendingCount > 1 ? "s" : ""}</>
                    )}
                </RBButton>
            )}
        </div>
    );
}
