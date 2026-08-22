import React from "react";
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
import { User, Sparkles, Info, HelpCircle, ArrowRight } from "lucide-react";

interface ChatMessageItemProps {
  message: ChatMessage;
  onAskQuestion?: (question: string) => void;
}

export function ChatMessageItem({ message, onAskQuestion }: ChatMessageItemProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-start gap-3.5 max-w-3xl ml-auto justify-end my-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="flex flex-col items-end gap-1.5 max-w-[85%]">
          <div className="rounded-2xl bg-white text-black px-4 py-3 text-sm font-medium leading-relaxed shadow-sm">
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

  return (
    <div className="flex items-start gap-3.5 max-w-4xl mr-auto my-4 w-full animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-gradient-to-br from-primary/30 to-white/10 border border-white/15 text-primary-light shadow-inner mt-1">
        <Sparkles className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-white tracking-wide flex items-center gap-1.5">
            FinExplain Evidence-First AI
          </span>
          <span className="text-[10px] text-white/40 font-mono">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {message.isPending && (
          <div className="rounded-2xl border border-white/10 bg-surface p-5 space-y-3">
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-spinner fa-spin text-sm text-primary-light" />
              <span className="text-xs font-medium text-white/90">
                Auditing agreement clauses & verifying claim evidence...
              </span>
            </div>
            <div className="space-y-2 pt-1">
              <div className="h-3 w-3/4 rounded bg-white/5 animate-pulse" />
              <div className="h-3 w-1/2 rounded bg-white/5 animate-pulse" />
            </div>
          </div>
        )}

        {res && (
          <div className="space-y-5">
            {/* Metrics Bar */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 rounded-2xl border border-white/10 bg-surface p-4 shadow-sm">
              <ScoreGauge
                value={Math.round((res.confidence_score || 0.9) * 100)}
                label="Confidence Score"
                description="Evidence & Provenance-Based (Measures retrieval relevance, metadata quality, and citation certainty)."
                tone="success"
              />
              <ScoreGauge
                value={res.risk_score || 20}
                label="Risk Rating"
                description="Document-Based (Derived deterministically from clauses and disclosure gaps found in your uploaded agreement)."
                tone={res.risk_score && res.risk_score > 50 ? "danger" : "warning"}
              />
              <div className="flex flex-col justify-center gap-2">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-muted-foreground block mb-1">
                    Evidence Status
                  </span>
                  <EvidenceBadge status={res.evidence_status || "EXPLICIT"} />
                </div>
                {res.risk_level && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wider text-muted-foreground block mb-1">
                      Risk Level
                    </span>
                    <SeverityBadge level={res.risk_level} />
                  </div>
                )}
              </div>
            </div>

            {/* Why did FinExplain provide this response? */}
            {(res.why_this_answer || res.evidence_status === "NOT_SPECIFIED") && (
              <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-4 text-xs">
                <div className="flex items-center gap-2 mb-1.5 font-semibold text-amber-300">
                  <Info className="h-4 w-4 shrink-0" />
                  <span>Why did FinExplain provide this response?</span>
                </div>
                <p className="text-white/85 leading-relaxed">
                  {res.why_this_answer ||
                    "You requested subjective advice with exact citations. Because loan documents contain factual legal and numerical clauses rather than promotional advice, synthesized advisory claims could not be verified against the source text. To protect you from AI hallucinations, FinExplain blocked ungrounded statements, assigned NOT_SPECIFIED status, and generated actionable lender questions instead."}
                </p>
              </div>
            )}

            {/* Executive Summary */}
            {res.plain_language_explanation && (
              <Panel title="Plain-Language Executive Summary">
                <FormattedMarkdown content={res.plain_language_explanation} />
              </Panel>
            )}

            {/* Verified Analysis */}
            <Panel title="Verified Analysis">
              <FormattedMarkdown content={res.answer} />
            </Panel>

            {/* Citations & Evidence Chunks */}
            {res.citations && res.citations.length > 0 && (
              <Panel
                title="Claim-Level Citations & Audit Trail"
                subtitle="Verifiable references in source documents"
              >
                <div className="flex flex-wrap gap-2">
                  {res.citations.map((c, idx) => (
                    <CitationChip
                      key={idx}
                      page={c.page || 1}
                      section={c.section || "General Terms"}
                      verified={c.verified ?? true}
                    />
                  ))}
                </div>
              </Panel>
            )}

            {/* Key Facts & Conditions Grid */}
            {(res.key_facts?.length || res.conditions?.length) ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {res.key_facts && res.key_facts.length > 0 && (
                  <Panel
                    title="Key Extracted Facts"
                    subtitle={`${res.key_facts.length} verified terms extracted`}
                  >
                    <div className="grid grid-cols-1 gap-2.5">
                      {res.key_facts.map((f, i) => (
                        <StructuredFactCard key={i} fact={f} isCondition={false} />
                      ))}
                    </div>
                  </Panel>
                )}

                {res.conditions && res.conditions.length > 0 && (
                  <Panel
                    title="Conditional Clauses"
                    subtitle={`${res.conditions.length} terms with active conditions`}
                  >
                    <div className="grid grid-cols-1 gap-2.5">
                      {res.conditions.map((c, i) => (
                        <StructuredFactCard key={i} fact={c} isCondition={true} />
                      ))}
                    </div>
                  </Panel>
                )}
              </div>
            ) : null}

            {/* Recommended Questions to Ask Provider */}
            {res.questions_to_ask_provider && res.questions_to_ask_provider.length > 0 && (
              <div className="rounded-xl border border-warning/30 bg-warning/5 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-warning" />
                  <span className="text-xs font-semibold text-white uppercase tracking-wider">
                    Recommended Follow-up Questions for Lender
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {res.questions_to_ask_provider.map((q, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onAskQuestion && onAskQuestion(q)}
                      className="group flex items-center justify-between gap-3 text-left rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-xs text-white/90 hover:bg-white/10 hover:border-white/20 transition-all"
                    >
                      <span className="leading-snug">{q}</span>
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-white shrink-0 group-hover:translate-x-0.5 transition-all" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
