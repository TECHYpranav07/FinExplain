import React, { useState } from "react";
import { type ChatMessage } from "@/lib/chatStorage";
import {
  EvidenceBadge,
  CitationChip,
  ScoreGauge,
  SeverityBadge,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";
import { HitlReviewCard } from "@/components/finex/HitlReviewCard";
import {
  User,
  Sparkles,
  ShieldAlert,
  Gauge,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  AlertCircle,
} from "lucide-react";

interface ChatMessageItemProps {
  message: ChatMessage;
  onAskQuestion?: (question: string) => void;
  onResolveHitl?: (messageId: string, action: "APPROVED" | "REJECTED", note?: string) => void;
}

export function ChatMessageItem({ message, onAskQuestion, onResolveHitl }: ChatMessageItemProps) {
  const isUser = message.role === "user";
  const res = message.response;

  // Only auto-expand audit metrics if the user EXPLICITLY asked for risk/confidence scores
  const isExplicitRiskQuery = React.useMemo(() => {
    const q = (message.content || "").toLowerCase();
    return (
      q.includes("risk factor") ||
      q.includes("risk score") ||
      q.includes("confidence score") ||
      q.includes("risk rating") ||
      q.includes("how risky") ||
      q.includes("quality score") ||
      (q.includes("risk") && (q.includes("score") || q.includes("factor")))
    );
  }, [message.content]);

  const [expandedMetrics, setExpandedMetrics] = useState(false);
  const showMetrics = isExplicitRiskQuery || expandedMetrics;

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

  const confidenceValue = res?.evidence_score ?? Math.round((res?.confidence_score || 0.9) * 100);
  const riskValue = res?.risk_score ?? 20;
  const hasRiskFactors = Boolean(res?.risk_factors && res.risk_factors.length > 0);

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
            {/* Primary Direct Answer Box */}
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

            {/* Document Audit Metrics & Risk Breakdown — Rendered ONLY when explicitly asked or toggled */}
            {showMetrics && (
              <div className="rounded-2xl border border-white/10 bg-surface-3/50 p-4 space-y-4 animate-in fade-in duration-200">
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-white uppercase tracking-wider">
                    <Gauge className="h-3.5 w-3.5 text-primary-light" />
                    <span>Document Audit & Risk Metrics</span>
                  </div>
                  {!isExplicitRiskQuery && (
                    <button
                      type="button"
                      onClick={() => setExpandedMetrics(false)}
                      className="text-[11px] text-muted-foreground hover:text-white flex items-center gap-1"
                    >
                      <span>Hide</span>
                      <ChevronUp className="h-3 w-3" />
                    </button>
                  )}
                </div>

                {/* Score Gauges Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="rounded-xl border border-white/10 bg-surface-2/70 p-3.5">
                    <ScoreGauge
                      value={confidenceValue}
                      label="Confidence Score"
                      description="Retrieval relevance & citation provenance certainty."
                      tone="info"
                    />
                  </div>
                  <div className="rounded-xl border border-white/10 bg-surface-2/70 p-3.5">
                    <ScoreGauge
                      value={riskValue}
                      label="Risk Rating"
                      description="Calculated deterministically from clauses & fee traps."
                      tone={riskValue > 50 ? "danger" : "warning"}
                    />
                  </div>
                </div>

                {/* Risk Factors Breakdown */}
                {hasRiskFactors && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
                      <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
                      <span>Identified Risk Factors ({res.risk_factors.length})</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {res.risk_factors.map((rf: any, idx: number) => (
                        <div
                          key={idx}
                          className="rounded-xl border border-white/10 bg-surface-2/60 p-3 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-white">
                              {rf.factor || rf.name || "Risk Item"}
                            </span>
                            <SeverityBadge level={rf.severity || "MEDIUM"} />
                          </div>
                          {rf.description && (
                            <p className="text-white/80 leading-relaxed text-[11px]">
                              {rf.description}
                            </p>
                          )}
                          {rf.impact && (
                            <p className="text-amber-300/90 text-[11px] font-medium pt-0.5">
                              Impact: {rf.impact}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Missing Disclosures Notice */}
                {res.missing_information && res.missing_information.length > 0 && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-amber-300 font-semibold text-[11px]">
                      <AlertCircle className="h-3.5 w-3.5" />
                      <span>Missing Mandatory Disclosures:</span>
                    </div>
                    <p className="text-white/80 text-[11px] leading-relaxed">
                      {res.missing_information
                        .map((m: any) => m.field?.replace("_", " ").toUpperCase())
                        .join(", ")}{" "}
                      not found in agreement documents.
                    </p>
                  </div>
                )}

                {/* Inquiries to Ask Lender */}
                {res.questions_to_ask_provider && res.questions_to_ask_provider.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                      Recommended Questions for Lender:
                    </span>
                    <div className="grid grid-cols-1 gap-1.5">
                      {res.questions_to_ask_provider.slice(0, 3).map((q: string, i: number) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => onAskQuestion && onAskQuestion(q)}
                          className="group flex items-center justify-between gap-2 text-left rounded-lg border border-white/10 bg-surface-2/60 px-3 py-2 text-xs text-white/90 hover:bg-white/10 transition-all"
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
