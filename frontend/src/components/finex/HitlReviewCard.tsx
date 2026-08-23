import React, { useState } from "react";
import {
  ShieldAlert,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileEdit,
  Clock,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface HitlReviewCardProps {
  reason?: string;
  type?: string;
  status?: "PENDING" | "APPROVED" | "REJECTED";
  reviewerNote?: string;
  resolvedAt?: string;
  onResolve?: (action: "APPROVED" | "REJECTED", note?: string) => void;
}

export function HitlReviewCard({
  reason,
  type = "GENERAL",
  status = "PENDING",
  reviewerNote,
  resolvedAt,
  onResolve,
}: HitlReviewCardProps) {
  const [note, setNote] = useState("");
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const isResolved = status === "APPROVED" || status === "REJECTED";

  const handleAction = (action: "APPROVED" | "REJECTED") => {
    if (onResolve) {
      onResolve(action, note.trim() || undefined);
    }
    setIsEditing(false);
  };

  const typeLabels: Record<string, string> = {
    CONFLICT_REVIEW: "Conflict Review",
    RISK_ACCEPTANCE: "High-Risk Escalation",
    DISCLOSURE_GAP: "Regulatory Disclosure Gap",
    GENERAL: "Human Verification",
  };

  return (
    <div
      className={`rounded-xl border p-3 text-xs transition-all ${
        status === "APPROVED"
          ? "border-emerald-500/30 bg-emerald-500/10"
          : status === "REJECTED"
            ? "border-rose-500/30 bg-rose-500/10"
            : "border-amber-500/30 bg-amber-500/10"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Interactive Shield Hover Popup */}
          <div className="relative group/shield inline-flex items-center">
            <button
              type="button"
              aria-label="HITL Gate Explanation"
              className="p-1 -m-1 rounded-md hover:bg-white/10 transition-colors focus:outline-none focus:ring-1 focus:ring-amber-400/50 cursor-help"
            >
              {status === "APPROVED" ? (
                <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
              ) : status === "REJECTED" ? (
                <XCircle className="h-4 w-4 text-rose-400 shrink-0" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0" />
              )}
            </button>

            {/* Hover Popover Modal Card (Solid Opaque Background) */}
            <div className="absolute left-0 bottom-full mb-2 w-72 sm:w-80 rounded-xl border border-white/20 bg-[#171717] p-3.5 shadow-[0_20px_60px_rgba(0,0,0,0.95)] text-left z-50 transition-all duration-200 pointer-events-none opacity-0 invisible translate-y-1 group-hover/shield:opacity-100 group-hover/shield:visible group-hover/shield:translate-y-0 group-hover/shield:pointer-events-auto">
              <div className="flex items-center gap-1.5 pb-2 border-b border-white/10 text-white font-bold text-xs">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
                <span>Human-In-The-Loop (HITL) Gate</span>
              </div>
              
              <p className="text-[11px] text-white/80 leading-relaxed mt-2">
                Triggered automatically when a clause involves material ambiguity, document contradictions, or high-risk penalty terms requiring human judgment.
              </p>

              <div className="mt-2.5 space-y-2 pt-2 border-t border-white/10 text-[11px]">
                {/* What Approve Does */}
                <div className="flex items-start gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/25 p-2">
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-emerald-300 block">What "Approve" does:</span>
                    <span className="text-white/80 leading-tight block mt-0.5">
                      Accepts and confirms this term as verified, dismissing the warning and saving it as borrower-confirmed in your audit log.
                    </span>
                  </div>
                </div>

                {/* What Dispute / Reject Does */}
                <div className="flex items-start gap-2 rounded-lg bg-rose-500/10 border border-rose-500/25 p-2">
                  <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-rose-300 block">What "Dispute / Reject" does:</span>
                    <span className="text-white/80 leading-tight block mt-0.5">
                      Flags this clause as disputed or inaccurate, marking it as a critical discrepancy to challenge or clarify with your lender.
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Tooltip arrow pointer */}
              <div className="absolute left-3.5 top-full w-2 h-2 -mt-1 bg-[#171717] border-r border-b border-white/20 rotate-45" />
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-white text-xs">
                Human-In-The-Loop Gate:
              </span>
              <span className="text-amber-200 font-medium truncate">
                {typeLabels[type] || "Verification Required"}
              </span>
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase tracking-wider ${
                  status === "APPROVED"
                    ? "bg-emerald-400/20 text-emerald-300"
                    : status === "REJECTED"
                      ? "bg-rose-400/20 text-rose-300"
                      : "bg-amber-400/20 text-amber-300"
                }`}
              >
                {status === "PENDING" ? "Pending Action" : status}
              </span>
            </div>
            <p className="text-[11px] text-white/80 mt-0.5 line-clamp-1">
              {reason || "This clause involves material variance or elevated risk requiring human validation."}
            </p>
          </div>
        </div>

        {/* Action Buttons for Unresolved */}
        {(!isResolved || isEditing) && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => handleAction("APPROVED")}
              className="flex items-center gap-1 rounded-lg bg-emerald-500 text-black px-2.5 py-1 text-xs font-bold hover:bg-emerald-400 transition-all shadow-sm"
            >
              <CheckCircle className="h-3 w-3" />
              <span>Approve</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction("REJECTED")}
              className="flex items-center gap-1 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2.5 py-1 text-xs font-bold hover:bg-rose-500/30 transition-all"
            >
              <XCircle className="h-3 w-3" />
              <span>Dispute</span>
            </button>

            <button
              type="button"
              onClick={() => setShowNoteInput(!showNoteInput)}
              className="text-white/60 hover:text-white p-1"
              title="Add Auditor Note"
            >
              <FileEdit className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Resolved Status */}
        {isResolved && !isEditing && (
          <div className="flex items-center gap-2 text-[11px] text-white/70 shrink-0">
            <span>
              {resolvedAt
                ? new Date(resolvedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "Resolved"}
            </span>
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="text-white/60 hover:text-white underline"
            >
              Edit
            </button>
          </div>
        )}
      </div>

      {/* Collapsible Note Input */}
      {showNoteInput && (!isResolved || isEditing) && (
        <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center gap-2">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add optional auditor note (e.g., Verified with branch manager)..."
            className="flex-1 rounded-lg border border-white/15 bg-black/40 px-2.5 py-1 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-white/30"
          />
        </div>
      )}

      {reviewerNote && isResolved && !isEditing && (
        <div className="mt-2 pt-1.5 border-t border-white/10 text-[11px] text-white/80 italic">
          Note: "{reviewerNote}"
        </div>
      )}
    </div>
  );
}
