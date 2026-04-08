"use client";

import { useRef, useState } from "react";
import { Upload, FileText, X, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { RBButton } from "@/components/reactbits";

interface Props {
    onUploaded: () => void;
}

type UploadState = "idle" | "uploading" | "success" | "error";

const ALLOWED_EXTS  = [".pdf", ".txt"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;

export default function DocumentUpload({ onUploaded }: Props) {
    const inputRef              = useRef<HTMLInputElement>(null);
    const [file, setFile]       = useState<File | null>(null);
    const [topic, setTopic]     = useState("");
    const [state, setState]     = useState<UploadState>("idle");
    const [message, setMessage] = useState("");
    const [drag, setDrag]       = useState(false);

    function pickFile(picked: File | null) {
        if (!picked) return;
        const ext = "." + picked.name.split(".").pop()!.toLowerCase();
        if (!ALLOWED_EXTS.includes(ext)) {
            setMessage("Only PDF and TXT files are supported.");
            setState("error");
            return;
        }
        if (picked.size > MAX_SIZE_BYTES) {
            setMessage("File exceeds 10 MB limit.");
            setState("error");
            return;
        }
        setFile(picked);
        setState("idle");
        setMessage("");
    }

    function onDrop(e: React.DragEvent) {
        e.preventDefault();
        setDrag(false);
        pickFile(e.dataTransfer.files[0] ?? null);
    }

    async function handleUpload() {
        if (!file) return;
        setState("uploading");
        setMessage("");

        const fd = new FormData();
        fd.append("file",       file);
        fd.append("topic",      topic);

        try {
            const res  = await fetch("/api/rag/upload", { method: "POST", body: fd });
            const data = await res.json();

            if (!res.ok) {
                setMessage(data.error ?? "Upload failed. Please try again.");
                setState("error");
            } else {
                setMessage(`"${data.filename}" ingested — ${data.chunk_count} chunks indexed.`);
                setState("success");
                setFile(null);
                setTopic("");
                if (inputRef.current) inputRef.current.value = "";
                onUploaded();
            }
        } catch {
            setMessage("Network error. Could not reach the server.");
            setState("error");
        }
    }

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
                        : file
                        ? "border-emerald-500/50 bg-emerald-500/5"
                        : "border-slate-600 bg-slate-800/40 hover:border-sky-500/60 hover:bg-sky-500/5"
                    }
                `}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf,.txt"
                    className="hidden"
                    onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                />

                {file ? (
                    <>
                        <FileText className="size-9 text-emerald-400" />
                        <div className="text-center">
                            <p className="text-sm font-medium text-slate-200">{file.name}</p>
                            <p className="text-xs text-slate-500">
                                {(file.size / 1024).toFixed(1)} KB · click to change
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setFile(null); setState("idle"); }}
                            className="absolute top-3 right-3 text-slate-500 hover:text-rose-400 transition-colors"
                        >
                            <X className="size-4" />
                        </button>
                    </>
                ) : (
                    <>
                        <Upload className="size-9 text-slate-500" />
                        <div className="text-center">
                            <p className="text-sm text-slate-300">
                                Drop a file here or <span className="text-sky-400 underline">browse</span>
                            </p>
                            <p className="text-xs text-slate-500 mt-1">PDF or TXT · max 10 MB</p>
                        </div>
                    </>
                )}
            </div>

            {/* Optional topic */}
            {file && (
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Topic / label (optional)"
                    className="w-full rounded-lg bg-slate-800 border border-slate-600 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
            )}

            {/* Status message */}
            {message && (
                <div className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${
                    state === "error"   ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" :
                    state === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                    "bg-slate-700/40 text-slate-300"
                }`}>
                    {state === "error"   ? <AlertCircle className="size-4 shrink-0 mt-0.5" /> :
                     state === "success" ? <CheckCircle2 className="size-4 shrink-0 mt-0.5" /> : null}
                    <span>{message}</span>
                </div>
            )}

            {/* Upload button */}
            <RBButton
                className="w-full"
                onClick={handleUpload}
                disabled={!file || state === "uploading"}
            >
                {state === "uploading" ? (
                    <><Loader2 className="size-4 animate-spin" /> Processing &amp; indexing…</>
                ) : (
                    <><Upload className="size-4" /> Upload &amp; Index Document</>
                )}
            </RBButton>
        </div>
    );
}
