import React from "react";
import { type ChatMessage } from "@/lib/chatStorage";
import {
  EvidenceBadge,
  CitationChip,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";
import { HitlReviewCard } from "@/components/finex/HitlReviewCard";
import { User, Sparkles } from "lucide-react";

interface ChatMessageItemProps {
  message: ChatMessage;
  onAskQuestion?: (question: string) => void;
  onResolveHitl?: (messageId: string, action: "APPROVED" | "REJECTED", note?: string) => void;
}

export function ChatMessageItem({ message, onAskQuestion, onResolveHitl }: ChatMessageItemProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start gap-3 max-w-3xl ml-auto justify-end my-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%]">
          <div className="rounded-2xl bg-white text-black px-4 py-2.5 text-sm font-medium leading-relaxed shadow-sm break-words [overflow-wrap:anywhere]">
            {message.content}
          </div>
          <span className="text-[10px] text-white/40 font-mono">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <div className="flex h-7 w-7 shrink-0 select-none items-center justify-center rounded-lg bg-white/15 text-white shadow-inner mt-0.5">
          <User className="h-3.5 w-3.5" />
        </div>
      </div>
    );
  }

  // Assistant Response Turn
  const res = message.response;

  return (
    <div className="flex items-start gap-3 max-w-3xl mr-auto my-3 w-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex h-7 w-7 shrink-0 select-none items-center justify-center rounded-lg bg-gradient-to-br from-primary/30 to-white/10 border border-white/15 text-primary-light shadow-inner mt-0.5">
        <Sparkles className="h-3.5 w-3.5" />
      </div>

      <div className="flex-1 min-w-0 space-y-2.5 max-w-full">
        {/* Header with Title, Status & Timestamp */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-white tracking-wide">
              FinExplain AI
            </span>
            {res && (
              <EvidenceBadge status={res.evidence_status || "EXPLICIT"} />
            )}
          </div>
          <span className="text-[10px] text-white/40 font-mono">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {message.isPending && (
          <div className="rounded-2xl border border-white/10 bg-surface-2 p-4 space-y-2.5">
            <div className="flex items-center gap-2.5">
              <i className="fa-solid fa-spinner fa-spin text-xs text-primary-light" />
              <span className="text-xs font-medium text-white/90">
                Auditing agreement clauses & verifying exact terms...
              </span>
            </div>
            <div className="space-y-1.5 pt-1">
              <div className="h-2 w-3/4 rounded bg-white/5 animate-pulse" />
              <div className="h-2 w-1/2 rounded bg-white/5 animate-pulse" />
            </div>
          </div>
        )}

        {res && (
          <div className="space-y-2.5 w-full max-w-full">
            {/* Primary Direct Answer */}
            <div className="rounded-2xl border border-white/10 bg-surface-2 p-4 sm:p-4.5 space-y-2.5 shadow-sm w-full max-w-full overflow-hidden break-words [overflow-wrap:anywhere]">
              <div className="text-sm text-white/95 leading-relaxed break-words overflow-hidden">
                <FormattedMarkdown content={res.answer} />
              </div>

              {/* Direct Evidence Citations Row */}
              {res.citations && res.citations.length > 0 && (
                <div className="pt-2 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mr-1 shrink-0">
                    Verified Sources:
                  </span>
                  {res.citations.map((c, idx) => (
                    <CitationChip
                      key={idx}
                      page={c.page || 1}
                      section={c.section || "General Terms"}
                      verified={c.verified ?? true}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* In-Chat HITL Escalation Review Mini-Card (Placed cleanly at bottom of answer when required) */}
            {res.hitl_required && (
              <HitlReviewCard
                reason={res.hitl_reason}
                type={res.hitl_type}
                status={res.hitl_status || "PENDING"}
                reviewerNote={res.hitl_reviewer_note}
                resolvedAt={res.hitl_resolved_at}
                onResolve={(action, note) => {
                  if (onResolveHitl) {
                    onResolveHitl(message.id, action, note);
                  }
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
