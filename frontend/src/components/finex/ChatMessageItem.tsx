import React, { useState } from "react";
import { type ChatMessage } from "@/lib/chatStorage";
import {
  Panel,
  ScoreGauge,
  EvidenceBadge,
  SeverityBadge,
  CitationChip,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";
import { StructuredFactCard } from "@/components/finex/StructuredFactCard";
import { HitlReviewCard } from "@/components/finex/HitlReviewCard";
import { User, Sparkles, ChevronDown, ChevronUp, ArrowRight, ShieldCheck } from "lucide-react";

interface ChatMessageItemProps {
  message: ChatMessage;
  onAskQuestion?: (question: string) => void;
  onResolveHitl?: (messageId: string, action: "APPROVED" | "REJECTED", note?: string) => void;
}

export function ChatMessageItem({ message, onAskQuestion, onResolveHitl }: ChatMessageItemProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start gap-3.5 max-w-3xl ml-auto justify-end my-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%]">
          <div className="rounded-2xl bg-white text-black px-4 py-2.5 text-sm font-medium leading-relaxed shadow-sm">
            {message.content}
          </div>
          <span className="text-[10px] text-white/40 font-mono">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-white/15 text-white shadow-inner">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  // Assistant Response Turn
  const res = message.response;
  const hasExtraFacts = (res?.key_facts?.length || 0) > 0 || (res?.conditions?.length || 0) > 0;

  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto my-4 w-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-gradient-to-br from-primary/30 to-white/10 border border-white/15 text-primary-light shadow-inner mt-1">
        <Sparkles className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0 space-y-3">
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
          <div className="rounded-2xl border border-white/10 bg-surface p-4 space-y-2.5">
            <div className="flex items-center gap-2.5">
              <i className="fa-solid fa-spinner fa-spin text-xs text-primary-light" />
              <span className="text-xs font-medium text-white/90">
                Verifying loan agreement clauses & calculating exact terms...
              </span>
            </div>
            <div className="space-y-1.5 pt-1">
              <div className="h-2.5 w-3/4 rounded bg-white/5 animate-pulse" />
              <div className="h-2.5 w-1/2 rounded bg-white/5 animate-pulse" />
            </div>
          </div>
        )}

        {res && (
          <div className="space-y-3">
            {/* Primary Direct Answer */}
            <div className="rounded-2xl border border-white/10 bg-surface p-4.5 space-y-3 shadow-sm">
              <div className="prose prose-invert max-w-none text-sm text-white/95 leading-relaxed">
                <FormattedMarkdown content={res.answer} />
              </div>

              {/* Direct Evidence Citations Row */}
              {res.citations && res.citations.length > 0 && (
                <div className="pt-2 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mr-1">
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

            {/* In-Chat HITL Escalation Review Mini-Card (Placed cleanly at bottom of answer) */}
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

            {/* Optional / Collapsible Technical Audit & Deep Evidence (Collapsed by Default) */}
            {hasExtraFacts && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-[11px] font-medium text-white/70 hover:text-white hover:bg-surface-2 transition-colors"
                >
                  <ShieldCheck className="h-3.5 w-3.5 text-primary-light" />
                  <span>
                    {showTechnicalDetails
                      ? "Hide Technical Audit Details"
                      : `View Technical Audit Evidence (${res.key_facts?.length || 0} terms verified)`}
                  </span>
                  {showTechnicalDetails ? (
                    <ChevronUp className="h-3 w-3 ml-0.5" />
                  ) : (
                    <ChevronDown className="h-3 w-3 ml-0.5" />
                  )}
                </button>

                {showTechnicalDetails && (
                  <div className="mt-3 space-y-4 rounded-xl border border-white/10 bg-surface-2/40 p-4 animate-in fade-in duration-200">
                    {/* Metrics Bar */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <ScoreGauge
                        value={Math.round((res.confidence_score || 0.9) * 100)}
                        label="Confidence Score"
                        description="Measures retrieval relevance & citation certainty."
                        tone="success"
                      />
                      <ScoreGauge
                        value={res.risk_score || 20}
                        label="Risk Rating"
                        description="Derived deterministically from operative clauses."
                        tone={res.risk_score && res.risk_score > 50 ? "danger" : "warning"}
                      />
                    </div>

                    {/* Key Facts & Conditions Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      {res.key_facts && res.key_facts.length > 0 && (
                        <Panel
                          title="Key Extracted Facts"
                          subtitle={`${res.key_facts.length} verified terms`}
                        >
                          <div className="grid grid-cols-1 gap-2">
                            {res.key_facts.map((f, i) => (
                              <StructuredFactCard key={i} fact={f} isCondition={false} />
                            ))}
                          </div>
                        </Panel>
                      )}

                      {res.conditions && res.conditions.length > 0 && (
                        <Panel
                          title="Conditional Clauses"
                          subtitle={`${res.conditions.length} active conditions`}
                        >
                          <div className="grid grid-cols-1 gap-2">
                            {res.conditions.map((c, i) => (
                              <StructuredFactCard key={i} fact={c} isCondition={true} />
                            ))}
                          </div>
                        </Panel>
                      )}
                    </div>

                    {/* Recommended Questions to Ask Provider */}
                    {res.questions_to_ask_provider && res.questions_to_ask_provider.length > 0 && (
                      <div className="rounded-xl border border-warning/30 bg-warning/5 p-3.5 space-y-2">
                        <span className="text-[11px] font-semibold text-white uppercase tracking-wider block">
                          Recommended Follow-up Inquiries:
                        </span>
                        <div className="grid grid-cols-1 gap-1.5">
                          {res.questions_to_ask_provider.map((q, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => onAskQuestion && onAskQuestion(q)}
                              className="group flex items-center justify-between gap-2 text-left rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/90 hover:bg-white/10 transition-all"
                            >
                              <span className="leading-snug truncate">{q}</span>
                              <ArrowRight className="h-3 w-3 text-muted-foreground group-hover:text-white shrink-0" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
