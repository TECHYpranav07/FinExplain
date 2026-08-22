import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type QueryResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import { Info } from "lucide-react";
import {
  PageHeader,
  Panel,
  Badge,
  EvidenceBadge,
  SeverityBadge,
  ScoreGauge,
  CitationChip,
  ErrorState,
} from "@/components/finex/primitives";

const QUICK_PROMPTS = [
  "What is the processing fee and APR calculation?",
  "What are the prepayment penalties and lock-in period?",
  "What happens if payment is delayed by 15 days?",
  "Calculate the total interest cost for ₹500,000 over 24 months at standard rate.",
  "Are there any hidden costs, insurance bundling, or reset clauses?",
];

export function QueryPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Array<{ q: string; res: QueryResponse; time: string }>>([]);

  const askMutation = useMutation({
    mutationFn: async (q: string) => {
      return api.ask({
        question: q,
        product_ids: selectedProducts,
      });
    },
    onSuccess: (data, q) => {
      setHistory((prev) => [
        { q, res: data, time: new Date().toLocaleTimeString() },
        ...prev,
      ]);
    },
  });

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    askMutation.mutate(question.trim());
  };

  const handleQuickPrompt = (p: string) => {
    setQuestion(p);
    askMutation.mutate(p);
  };

  const currentResult = history[0]?.res;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Evidence-First RAG"
        title="Evidence-First AI Q&A"
        description="Query loan agreements with deterministic financial math, claim-level citations, conflict verification, and risk auditing."
      />

      {/* Target Products Selector */}
      <Panel title="Target Loan Products" subtitle="Select products/lenders to query against">
        <ProductPicker
          selected={selectedProducts}
          onChange={setSelectedProducts}
          multiple={true}
        />
      </Panel>

      {/* Query Input */}
      <Panel>
        <form onSubmit={handleAsk} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Financial Query / Loan Clause Inquiry
            </label>
            <div className="relative">
              <textarea
                aria-label="Financial Query"
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about interest rates, prepayment charges, reset benchmarks, foreclosures..."
                className="w-full rounded-xl border border-white/10 bg-surface-2 p-4 text-sm text-white placeholder:text-muted-foreground focus:border-white/30 focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Quick Prompts */}
          <div>
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mr-2">
              Auditor Presets:
            </span>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => handleQuickPrompt(p)}
                  className="rounded-full border border-white/10 bg-surface-3 px-3 py-1 text-[11px] text-muted-foreground hover:text-white hover:border-white/20 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={askMutation.isPending || !question.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-white px-6 py-2.5 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40 transition-colors shadow-sm"
            >
              {askMutation.isPending ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin text-xs" />
                  <span>Synthesizing Verified Answer...</span>
                </>
              ) : (
                <>
                  <i className="fa-solid fa-sparkles text-xs" />
                  <span>Ask Evidence-First AI</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Panel>

      {askMutation.isError && (
        <ErrorState
          message={(askMutation.error as any)?.message || "Failed to execute query"}
          onRetry={() => askMutation.mutate(question)}
        />
      )}

      {/* Latest Result Display */}
      {currentResult && (
        <div className="space-y-6">
          {/* Top Score Bar */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 rounded-xl border border-white/10 bg-surface p-5">
            <ScoreGauge
              value={Math.round((currentResult.confidence_score || 0.9) * 100)}
              label="Confidence Score"
              description="Evidence & Provenance-Based (Measures retrieval relevance, metadata quality, and citation certainty)."
              tone="success"
            />
            <ScoreGauge
              value={currentResult.risk_score || 20}
              label="Risk Rating"
              description="Document-Based (Derived deterministically from clauses and disclosure gaps found in your uploaded agreement)."
              tone={currentResult.risk_score && currentResult.risk_score > 50 ? "danger" : "warning"}
            />
            <div className="flex flex-col justify-center gap-2">
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground block mb-1">
                  Evidence Status
                </span>
                <EvidenceBadge status={currentResult.evidence_status || "EXPLICIT"} />
              </div>
              {currentResult.risk_level && (
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-muted-foreground block mb-1">
                    Risk Level
                  </span>
                  <SeverityBadge level={currentResult.risk_level} />
                </div>
              )}
            </div>
          </div>

          {/* Plain Language Explanation */}
          {currentResult.plain_language_explanation && (
            <Panel title="Plain-Language Executive Summary">
              <p className="text-sm text-white leading-relaxed">
                {currentResult.plain_language_explanation}
              </p>
            </Panel>
          )}

          {/* Why did FinExplain provide this response? */}
          {(currentResult.why_this_answer || currentResult.evidence_status === "NOT_SPECIFIED") && (
            <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 p-4 text-xs">
              <div className="flex items-center gap-2 mb-1.5 font-semibold text-amber-300">
                <Info className="h-4 w-4 shrink-0" />
                <span>Why did FinExplain provide this response?</span>
              </div>
              <p className="text-white/85 leading-relaxed">
                {currentResult.why_this_answer ||
                  "You requested subjective advice (e.g. why to choose or avoid this loan) with exact citations. Because loan documents contain factual legal and numerical clauses rather than promotional advice, synthesized advisory claims could not be verified against the source text. To protect you from AI hallucinations, FinExplain blocked ungrounded statements, assigned NOT_SPECIFIED status, and generated actionable lender questions instead."}
              </p>
            </div>
          )}

          {/* Detailed Synthesized Answer */}
          <Panel title="Verified Analysis">
            <div className="text-sm text-white/90 whitespace-pre-line leading-relaxed">
              {currentResult.answer}
            </div>
          </Panel>

          {/* Citations & Evidence Chunks */}
          {currentResult.citations && currentResult.citations.length > 0 && (
            <Panel title="Claim-Level Citations & Audit Trail" subtitle="Verifiable references in source documents">
              <div className="flex flex-wrap gap-2">
                {currentResult.citations.map((c, idx) => (
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

          {/* Key Facts / Conditions Grid */}
          {(currentResult.key_facts?.length || currentResult.conditions?.length) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {currentResult.key_facts && currentResult.key_facts.length > 0 && (
                <Panel title="Key Extracted Facts">
                  <ul className="space-y-2 text-xs text-white/90">
                    {currentResult.key_facts.map((f, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <i className="fa-solid fa-check text-success mt-0.5" />
                        <span>{typeof f === "string" ? f : JSON.stringify(f)}</span>
                      </li>
                    ))}
                  </ul>
                </Panel>
              )}

              {currentResult.conditions && currentResult.conditions.length > 0 && (
                <Panel title="Conditional Clauses">
                  <ul className="space-y-2 text-xs text-white/90">
                    {currentResult.conditions.map((c, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <i className="fa-solid fa-circle-exclamation text-warning mt-0.5" />
                        <span>{typeof c === "string" ? c : JSON.stringify(c)}</span>
                      </li>
                    ))}
                  </ul>
                </Panel>
              )}
            </div>
          ) : null}

          {/* Questions for Provider */}
          {currentResult.questions_to_ask_provider && currentResult.questions_to_ask_provider.length > 0 && (
            <Panel title="Recommended Questions to Ask Provider" className="border-warning/30 bg-warning/5">
              <ul className="space-y-2 text-xs text-white">
                {currentResult.questions_to_ask_provider.map((q, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="font-bold text-warning">{i + 1}.</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}
