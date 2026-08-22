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
  const [isEditing, setIsEditing] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const isResolved = status === "APPROVED" || status === "REJECTED";

  const handleAction = (action: "APPROVED" | "REJECTED") => {
    if (onResolve) {
      onResolve(action, note.trim() || undefined);
    }
    setIsEditing(false);
  };

  const typeLabels: Record<string, string> = {
    CONFLICT_REVIEW: "Cross-Document Conflict Review",
    RISK_ACCEPTANCE: "High-Risk Clause Escalation",
    DISCLOSURE_GAP: "Regulatory Disclosure Gap",
    GENERAL: "Human Auditor Verification",
  };

  return (
    <div
      className={`rounded-2xl border transition-all duration-300 overflow-hidden ${
        status === "APPROVED"
          ? "border-emerald-500/40 bg-emerald-500/10"
          : status === "REJECTED"
            ? "border-rose-500/40 bg-rose-500/10"
            : "border-amber-500/40 bg-amber-500/10 shadow-lg shadow-amber-500/5"
      }`}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-white/10">
        <div className="flex items-center gap-2.5">
          {status === "APPROVED" ? (
            <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
          ) : status === "REJECTED" ? (
            <XCircle className="h-5 w-5 text-rose-400 shrink-0" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 animate-pulse" />
          )}

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white tracking-wide">
                Human-In-The-Loop (HITL) Gate
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold uppercase tracking-wider ${
                  status === "APPROVED"
                    ? "bg-emerald-400/20 text-emerald-300 border border-emerald-400/30"
                    : status === "REJECTED"
                      ? "bg-rose-400/20 text-rose-300 border border-rose-400/30"
                      : "bg-amber-400/20 text-amber-300 border border-amber-400/30"
                }`}
              >
                {status === "PENDING" ? "Review Pending" : status}
              </span>
            </div>
            <p className="text-[11px] text-white/70 mt-0.5">
              {typeLabels[type] || "Auditor Review Required"}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="p-1 rounded-lg text-white/60 hover:text-white hover:bg-white/5 transition-colors"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Body */}
      {expanded && (
        <div className="p-4 space-y-3.5 text-xs">
          {/* Reason message */}
          <div className="text-white/90 leading-relaxed bg-black/20 rounded-xl p-3 border border-white/5">
            <p className="font-medium flex items-start gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>{reason || "This clause involves material variance or elevated risk requiring human validation."}</span>
            </p>
          </div>

          {/* Pending Decision Form */}
          {(!isResolved || isEditing) && (
            <div className="space-y-3 pt-1">
              <div>
                <label className="block text-[11px] font-semibold text-white/80 mb-1 flex items-center gap-1">
                  <FileEdit className="h-3 w-3 text-muted-foreground" />
                  <span>Reviewer / Auditor Note (Optional):</span>
                </label>
                <textarea
                  rows={2}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Verified with lender branch manager that KFS 3% rate governs; or Flagged for dispute before signing..."
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-xs text-white placeholder:text-muted-foreground focus:outline-none focus:border-white/30 transition-colors"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => handleAction("APPROVED")}
                  className="flex items-center gap-1.5 rounded-xl bg-emerald-500 text-black px-3.5 py-2 font-bold hover:bg-emerald-400 transition-all shadow-sm"
                >
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>Approve Term (Accept Risk)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleAction("REJECTED")}
                  className="flex items-center gap-1.5 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 px-3.5 py-2 font-bold hover:bg-rose-500/30 transition-all"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  <span>Flag for Lender Dispute</span>
                </button>

                {isEditing && (
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="text-[11px] text-white/60 hover:text-white ml-auto underline"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Resolved State Display */}
          {isResolved && !isEditing && (
            <div className="space-y-2 pt-1 border-t border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[11px] text-white/70">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>
                    Resolution recorded{" "}
                    {resolvedAt
                      ? new Date(resolvedAt).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "just now"}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setNote(reviewerNote || "");
                    setIsEditing(true);
                  }}
                  className="text-[11px] text-white/60 hover:text-white underline transition-colors"
                >
                  Change Decision
                </button>
              </div>

              {reviewerNote && (
                <div className="bg-black/30 rounded-lg p-2.5 border border-white/5 text-[11px] text-white/90">
                  <span className="text-muted-foreground font-semibold block mb-0.5">Reviewer Note:</span>
                  <p className="italic">"{reviewerNote}"</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
