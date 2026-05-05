"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { usePageAgent } from "@/hooks/use-page-agent";

export function AgentConfirmDialog() {
  const { pendingConfirmation, approveConfirmation, rejectConfirmation } =
    usePageAgent();

  if (!pendingConfirmation) return null;

  const { tool, input } = pendingConfirmation;

  // Human-readable action summary
  const summary =
    typeof input === "object" &&
    input !== null &&
    "action_summary" in input
      ? String((input as { action_summary: string }).action_summary)
      : `Tool: ${tool}`;

  const inputDisplay =
    typeof input === "object" && input !== null
      ? JSON.stringify(input, null, 2)
      : String(input ?? "");

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="agent-confirm-title"
    >
      {/* Dialog */}
      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-amber-500/30 bg-gray-950 shadow-2xl overflow-hidden">
        {/* Header strip */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5 bg-amber-500/10">
          <AlertTriangle className="size-5 text-amber-400 shrink-0" />
          <span
            id="agent-confirm-title"
            className="text-sm font-semibold text-amber-300"
          >
            Agent confirmation required
          </span>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-3">
          <p className="text-sm text-white/80 leading-relaxed">{summary}</p>

          {inputDisplay && (
            <pre className="text-[11px] font-mono text-slate-400 bg-white/5 rounded-lg p-3 overflow-x-auto max-h-32 whitespace-pre-wrap">
              {inputDisplay}
            </pre>
          )}

          <p className="text-xs text-slate-500">
            The AI copilot is requesting permission to perform the action above.
            Approve only if you fully understand the consequences.
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 px-5 pb-5">
          <button
            onClick={rejectConfirmation}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium py-2.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
          >
            <XCircle className="size-4" />
            Reject
          </button>
          <button
            onClick={approveConfirmation}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-sm font-medium py-2.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          >
            <CheckCircle2 className="size-4" />
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
