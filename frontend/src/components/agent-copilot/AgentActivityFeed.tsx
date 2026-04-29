"use client";

import { useEffect, useRef } from "react";
import {
  Brain,
  Zap,
  CheckCircle2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import type { AgentActivity } from "@page-agent/core";

interface Props {
  activities: AgentActivity[];
}

export function AgentActivityFeed({ activities }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest entry
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activities]);

  if (activities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2 text-slate-600">
        <Brain className="size-8 opacity-40" />
        <span className="text-xs">Awaiting your command…</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10">
      {activities.map((activity, i) => (
        <ActivityRow key={i} activity={activity} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function ActivityRow({ activity }: { activity: AgentActivity }) {
  switch (activity.type) {
    case "thinking":
      return (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/[0.03]">
          <Brain className="size-3.5 text-brand-blue-400 animate-pulse shrink-0" />
          <span className="text-[11px] text-slate-400 italic">Thinking…</span>
        </div>
      );

    case "executing":
      return (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-brand-blue-900/20 border border-brand-blue-800/30">
          <Zap className="size-3.5 text-brand-blue-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <span className="text-[11px] text-brand-blue-300 font-medium">
              {formatToolName(activity.tool)}
            </span>
            {activity.input !== undefined && (
              <div className="text-[10px] text-slate-500 font-mono truncate mt-0.5">
                {formatInput(activity.input)}
              </div>
            )}
          </div>
        </div>
      );

    case "executed": {
      // Special render for "done" tool — full Q&A answer, no truncation
      if (activity.tool === "done") {
        return (
          <div className="flex items-start gap-2 px-2 py-2.5 rounded-xl bg-emerald-900/15 border border-emerald-700/25">
            <CheckCircle2 className="size-3.5 text-emerald-400 mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wide block mb-1.5">
                Answer
              </span>
              <p className="text-[11px] text-slate-200 leading-relaxed whitespace-pre-line">
                {String(activity.output ?? "")}
              </p>
            </div>
          </div>
        );
      }
      // Default executed render
      return (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-emerald-900/10 border border-emerald-800/20">
          <CheckCircle2 className="size-3.5 text-emerald-400 mt-0.5 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] text-emerald-300 font-medium">
                {formatToolName(activity.tool)}
              </span>
              <span className="text-[10px] text-slate-600 shrink-0">
                {activity.duration}ms
              </span>
            </div>
            {activity.output && (
              <div className="text-[10px] text-slate-500 truncate mt-0.5">
                {String(activity.output).slice(0, 100)}
              </div>
            )}
          </div>
        </div>
      );
    } // end case "executed"

    case "retrying":
      return (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-amber-900/10 border border-amber-700/20">
          <RefreshCw className="size-3.5 text-amber-400 animate-spin shrink-0" />
          <span className="text-[11px] text-amber-300">
            Retrying… ({activity.attempt}/{activity.maxAttempts})
          </span>
        </div>
      );

    case "error":
      return (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-red-900/10 border border-red-700/20">
          <AlertCircle className="size-3.5 text-red-400 mt-0.5 shrink-0" />
          <span className="text-[11px] text-red-300">
            {activity.message?.slice(0, 120) ?? "Unknown error"}
          </span>
        </div>
      );

    default:
      return null;
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatToolName(tool: string): string {
  return tool
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatInput(input: unknown): string {
  if (typeof input === "string") return input.slice(0, 80);
  try {
    return JSON.stringify(input).slice(0, 80);
  } catch {
    return "";
  }
}
