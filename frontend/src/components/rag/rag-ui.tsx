"use client";

import type { ReactNode } from "react";
import {
    Bot,
    Check,
    Clipboard,
    FileText,
    Image as ImageIcon,
    Mic,
    RotateCcw,
    Sparkles,
    User,
    Video,
    X,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type RagModality = "text" | "image" | "audio" | "video" | string;

export type RagSource = {
    filename: string;
    modality?: RagModality;
    page_number?: number | null;
    timestamp_start?: number | null;
    timestamp_end?: number | null;
};

export type RagDocument = {
    id: string;
    filename: string;
    file_type: string;
    modality: RagModality;
    topic: string;
    chunk_count: number;
    uploaded_at: string;
};

export function modalityMeta(modality?: RagModality) {
    switch ((modality ?? "text").toLowerCase()) {
        case "image":
            return {
                label: "Image",
                icon: ImageIcon,
                chip: "border-fuchsia-400/25 bg-fuchsia-400/10 text-fuchsia-200",
                iconTone: "text-fuchsia-300 bg-fuchsia-400/10 border-fuchsia-400/20",
            };
        case "audio":
            return {
                label: "Audio",
                icon: Mic,
                chip: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
                iconTone: "text-emerald-300 bg-emerald-400/10 border-emerald-400/20",
            };
        case "video":
            return {
                label: "Video",
                icon: Video,
                chip: "border-amber-400/25 bg-amber-400/10 text-amber-200",
                iconTone: "text-amber-300 bg-amber-400/10 border-amber-400/20",
            };
        default:
            return {
                label: "Text",
                icon: FileText,
                chip: "border-sky-400/25 bg-sky-400/10 text-sky-200",
                iconTone: "text-sky-300 bg-sky-400/10 border-sky-400/20",
            };
    }
}

export function formatRagSource(src: RagSource) {
    const parts = [src.filename];
    if (src.modality) parts.push(modalityMeta(src.modality).label.toLowerCase());
    if (typeof src.page_number === "number") parts.push(`page ${src.page_number}`);
    if (typeof src.timestamp_start === "number" && typeof src.timestamp_end === "number") {
        parts.push(`${src.timestamp_start.toFixed(1)}s-${src.timestamp_end.toFixed(1)}s`);
    }
    return parts.join(" - ");
}

export function RagBadge({ modality, className }: { modality?: RagModality; className?: string }) {
    const meta = modalityMeta(modality);
    const Icon = meta.icon;
    return (
        <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium", meta.chip, className)}>
            <Icon className="size-3" />
            {meta.label}
        </span>
    );
}

export function RagThread({ children, className }: { children: ReactNode; className?: string }) {
    return (
        <div className={cn("flex-1 overflow-y-auto scroll-smooth px-1 pb-4", className)}>
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">{children}</div>
        </div>
    );
}

export function RagMessage({
    role,
    children,
    streaming,
    error,
    actions,
}: {
    role: "user" | "assistant";
    children: ReactNode;
    streaming?: boolean;
    error?: boolean;
    actions?: ReactNode;
}) {
    const isUser = role === "user";
    const Avatar = isUser ? User : Bot;
    return (
        <div className={cn("group flex gap-3", isUser && "justify-end")}>
            {!isUser && (
                <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-lg border border-violet-400/20 bg-violet-400/10 text-violet-200">
                    <Avatar className="size-4" />
                </div>
            )}
            <div className={cn("min-w-0 max-w-[min(780px,88%)]", isUser && "order-first")}>
                <div
                    className={cn(
                        "rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-sm",
                        isUser
                            ? "rounded-br-md border-sky-500/20 bg-sky-600 text-white"
                            : error
                            ? "rounded-bl-md border-rose-500/25 bg-rose-500/10 text-rose-200"
                            : "rounded-bl-md border-border bg-card/90 text-card-foreground"
                    )}
                >
                    {!isUser && !error && (
                        <div className="mb-2 flex items-center gap-2 text-xs font-medium text-violet-300">
                            <Sparkles className="size-3.5" />
                            Strategy Tutor
                        </div>
                    )}
                    {children}
                </div>
                {actions && <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">{actions}</div>}
            </div>
            {isUser && (
                <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-lg border border-sky-400/20 bg-sky-400/10 text-sky-100">
                    <Avatar className="size-4" />
                </div>
            )}
        </div>
    );
}

export function RagSourceList({ sources }: { sources: RagSource[] }) {
    if (!sources.length) return null;
    const grouped = sources.reduce<Record<string, RagSource[]>>((acc, src) => {
        const key = src.modality ?? "text";
        acc[key] = acc[key] ?? [];
        acc[key].push(src);
        return acc;
    }, {});

    return (
        <div className="mt-3 border-t border-border pt-3">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <FileText className="size-3.5" />
                Sources
            </div>
            <div className="flex flex-col gap-2">
                {Object.entries(grouped).map(([modality, items]) => (
                    <div key={modality} className="flex flex-wrap items-center gap-1.5">
                        <RagBadge modality={modality} />
                        {items.map((src) => (
                            <span
                                key={`${src.filename}-${src.modality ?? "text"}-${src.page_number ?? "na"}-${src.timestamp_start ?? "na"}-${src.timestamp_end ?? "na"}`}
                                className="max-w-full truncate rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                                title={formatRagSource(src)}
                            >
                                {formatRagSource(src)}
                            </span>
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
}

export function RagThinkingDots() {
    return (
        <div className="flex items-center gap-1.5 py-1" aria-label="Thinking">
            {[0, 1, 2].map((idx) => (
                <span
                    key={idx}
                    className="size-1.5 animate-bounce rounded-full bg-foreground/80 shadow-[0_0_12px_currentColor]"
                    style={{ animationDelay: `${idx * 130}ms`, animationDuration: "900ms" }}
                />
            ))}
        </div>
    );
}

export function RagMessageAction({
    label,
    icon,
    onClick,
}: {
    label: string;
    icon: "copy" | "regenerate" | "clear" | "check";
    onClick: () => void;
}) {
    const Icon = icon === "copy" ? Clipboard : icon === "regenerate" ? RotateCcw : icon === "clear" ? X : Check;
    return (
        <button
            type="button"
            onClick={onClick}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            title={label}
        >
            <Icon className="size-3" />
            {label}
        </button>
    );
}

export function RagComposer({
    value,
    onChange,
    onSubmit,
    disabled,
    busy,
    placeholder,
    left,
}: {
    value: string;
    onChange: (value: string) => void;
    onSubmit: () => void;
    disabled?: boolean;
    busy?: boolean;
    placeholder: string;
    left?: ReactNode;
}) {
    function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
        }
    }

    return (
        <div className="sticky bottom-0 bg-gradient-to-t from-background via-background/95 to-transparent pt-4">
            <div className="mx-auto max-w-4xl rounded-2xl border border-border bg-card/95 p-2 shadow-[0_16px_40px_rgba(15,23,42,0.14)] dark:shadow-[0_18px_50px_rgba(2,6,23,0.55)]">
                {left}
                <div className="flex items-end gap-2">
                    <textarea
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        onKeyDown={handleKey}
                        disabled={disabled}
                        placeholder={placeholder}
                        rows={2}
                        className="min-h-[52px] flex-1 resize-none bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                    />
                    <button
                        type="button"
                        onClick={onSubmit}
                        disabled={disabled || busy || !value.trim()}
                        className="mb-1 inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-sky-600 text-white transition-all hover:bg-sky-500 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
                        title="Send"
                    >
                        {busy ? <span className="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <Sparkles className="size-4" />}
                    </button>
                </div>
            </div>
        </div>
    );
}

export function RagSuggestedPrompts({
    prompts,
    onSelect,
}: {
    prompts: string[];
    onSelect: (prompt: string) => void;
}) {
    return (
        <div className="flex flex-wrap justify-center gap-2">
            {prompts.map((prompt) => (
                <button
                    key={prompt}
                    type="button"
                    onClick={() => onSelect(prompt)}
                    className="rounded-full border border-border bg-card/75 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-sky-500/40 hover:bg-sky-500/10 hover:text-sky-600 dark:hover:text-sky-200"
                >
                    {prompt}
                </button>
            ))}
        </div>
    );
}

export function RagDocumentCard({
    doc,
    deleting,
    onDelete,
}: {
    doc: RagDocument;
    deleting?: boolean;
    onDelete: () => void;
}) {
    const meta = modalityMeta(doc.modality);
    const Icon = meta.icon;
    const date = new Date(doc.uploaded_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });

    return (
        <li className="flex items-start gap-3 rounded-xl border border-border bg-card/75 px-3 py-3">
            <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", meta.iconTone)}>
                <Icon className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{doc.filename}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <RagBadge modality={doc.modality} />
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">{doc.chunk_count} chunks</span>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">{date}</span>
                </div>
                {doc.topic && <p className="mt-1 truncate text-xs text-slate-500">{doc.topic}</p>}
            </div>
            <button
                type="button"
                onClick={onDelete}
                disabled={deleting}
                className="rounded-md p-1 text-slate-600 transition-colors hover:bg-rose-500/10 hover:text-rose-300 disabled:opacity-40"
                title="Delete document"
            >
                {deleting ? <span className="block size-4 animate-spin rounded-full border-2 border-slate-500/30 border-t-slate-300" /> : <X className="size-4" />}
            </button>
        </li>
    );
}

export function RagKnowledgeStats({ docs }: { docs: RagDocument[] }) {
    const counts = docs.reduce<Record<string, number>>((acc, doc) => {
        const key = doc.modality || "text";
        acc[key] = (acc[key] ?? 0) + 1;
        return acc;
    }, {});
    const modalities = ["text", "image", "audio", "video"];

    return (
        <div className="rounded-xl border border-border bg-card/70 p-3">
            <div className="mb-2 flex items-center justify-between">
                <p className="text-xs font-medium text-muted-foreground">Indexed knowledge</p>
                <span className="text-xs text-muted-foreground">{docs.length} files</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
                {modalities.map((modality) => {
                    const meta = modalityMeta(modality);
                    const Icon = meta.icon;
                    return (
                        <div key={modality} className="flex items-center gap-2 rounded-lg bg-muted/70 px-2 py-2">
                            <Icon className={cn("size-3.5", meta.iconTone.split(" ")[0])} />
                            <span className="text-xs text-muted-foreground">{meta.label}</span>
                            <span className="ml-auto text-xs font-semibold text-foreground">{counts[modality] ?? 0}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
