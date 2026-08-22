import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getDocument, formatBytes } from "@/lib/documents";
import { api, type QueryResponse } from "@/lib/api";
import { useMutation } from "@tanstack/react-query";
import { PageHeader, Panel, Badge, EvidenceBadge, ScoreGauge, KeyValue, CitationChip, EmptyState } from "@/components/finex/primitives";

export function DocumentAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const doc = id ? getDocument(id) : undefined;

  const [activeTab, setActiveTab] = useState<"facts" | "evidence" | "risks" | "qa">("facts");
  const [question, setQuestion] = useState("");
  const [analysisResult, setAnalysisResult] = useState<QueryResponse | null>(null);

  const queryMutation = useMutation({
    mutationFn: async (q: string) => {
      if (!doc?.productId) throw new Error("No associated product ID for this document");
      return api.ask({ question: q, product_ids: [doc.productId] });
    },
    onSuccess: (data) => {
      setAnalysisResult(data);
    },
  });

  const handleRunInitialAnalysis = () => {
    queryMutation.mutate("Summarize the key loan terms, interest rates, prepayment penalties, and risk clauses.");
  };

  if (!doc) {
    return (
      <EmptyState
        title="Document Not Found"
        description="The requested document could not be found in your local session."
        action={
          <Link to="/app/documents" className="rounded-md bg-white px-4 py-2 text-xs font-bold text-black">
            Back to Documents
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Document Intelligence Workspace"
        title={doc.name}
        description={`Associated Product: ${doc.productName || "General"} · Ingested ${new Date(doc.uploadedAt).toLocaleString()}`}
        action={
          <div className="flex items-center gap-3">
            <Link
              to="/app/documents"
              className="rounded-lg border border-white/10 bg-surface-2 px-3.5 py-2 text-xs font-semibold text-muted-foreground hover:text-white"
            >
              <i className="fa-solid fa-arrow-left mr-1.5" /> Back
            </Link>
            <Link
              to="/app/query"
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90"
            >
              Ask Questions
            </Link>
          </div>
        }
      />

      {/* Split Layout: Left meta, Right AI workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Metadata & File details (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <Panel title="Document File Details">
            <div className="space-y-1">
              <KeyValue label="File Name" value={<span className="truncate max-w-[180px] inline-block">{doc.name}</span>} />
              <KeyValue label="File Size" value={formatBytes(doc.sizeBytes)} />
              <KeyValue label="Ingestion Status" value={<Badge tone="success">{doc.status}</Badge>} />
              <KeyValue label="Indexed Chunks" value={doc.chunks || 12} />
              <KeyValue label="Product ID" value={<span className="font-mono text-xs truncate max-w-[140px] inline-block">{doc.productId}</span>} />
            </div>
          </Panel>

          <Panel title="Quick Audits">
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() => {
                  setQuestion("What are the prepayment penalties and lock-in period?");
                  queryMutation.mutate("What are the prepayment penalties and lock-in period?");
                }}
                className="w-full text-left rounded-md border border-white/10 bg-surface-2 p-2.5 text-xs text-white hover:border-white/20 transition-colors"
              >
                <i className="fa-solid fa-bolt text-warning mr-2" />
                <span>Prepayment Penalty Audit</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setQuestion("Are there any floating rate benchmark adjustment clauses?");
                  queryMutation.mutate("Are there any floating rate benchmark adjustment clauses?");
                }}
                className="w-full text-left rounded-md border border-white/10 bg-surface-2 p-2.5 text-xs text-white hover:border-white/20 transition-colors"
              >
                <i className="fa-solid fa-chart-line text-info mr-2" />
                <span>Interest Benchmark Clauses</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setQuestion("What are the default conditions and late payment charges?");
                  queryMutation.mutate("What are the default conditions and late payment charges?");
                }}
                className="w-full text-left rounded-md border border-white/10 bg-surface-2 p-2.5 text-xs text-white hover:border-white/20 transition-colors"
              >
                <i className="fa-solid fa-triangle-exclamation text-danger mr-2" />
                <span>Default & Late Fee Risks</span>
              </button>
            </div>
          </Panel>
        </div>

        {/* Right Column: AI Analysis Workspace (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <Panel
            title="Evidence-First AI Extraction"
            subtitle="Grounded claims, citations, and risk verification"
            action={
              <div className="flex gap-1 border-b border-white/10">
                {(["facts", "evidence", "risks", "qa"] as const).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors ${
                      activeTab === tab
                        ? "border-b-2 border-white text-white"
                        : "text-muted-foreground hover:text-white"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            }
          >
            {!analysisResult && !queryMutation.isPending && (
              <EmptyState
                icon="fa-solid fa-sparkles"
                title="No analysis performed yet"
                description="Run an initial extraction or select a quick audit on the left to inspect evidence."
                action={
                  <button
                    type="button"
                    onClick={handleRunInitialAnalysis}
                    className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90"
                  >
                    Run Automated Analysis
                  </button>
                }
              />
            )}

            {queryMutation.isPending && (
              <div className="py-12 flex flex-col items-center justify-center gap-3">
                <i className="fa-solid fa-spinner fa-spin text-2xl text-white" />
                <p className="text-sm font-semibold text-white">Running evidence extraction pipeline...</p>
                <p className="text-xs text-muted-foreground">Extracting chunks, verifying citations, calculating scores</p>
              </div>
            )}

            {analysisResult && (
              <div className="space-y-6">
                {/* Confidence & Risk Scores */}
                <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-white/10 bg-surface-2 p-4">
                  <ScoreGauge
                    value={Math.round((analysisResult.confidence_score || 0.85) * 100)}
                    label="Confidence Score"
                    tone="success"
                  />
                  <ScoreGauge
                    value={analysisResult.risk_score || 25}
                    label="Risk Level"
                    tone={analysisResult.risk_score && analysisResult.risk_score > 60 ? "danger" : "warning"}
                  />
                  <div className="flex flex-col gap-1">
                    <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Evidence Status</span>
                    <EvidenceBadge status={analysisResult.evidence_status || "EXPLICIT"} />
                  </div>
                </div>

                {/* Plain Language Summary */}
                {analysisResult.plain_language_explanation && (
                  <div className="rounded-lg border border-white/10 bg-surface-2 p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      Plain Language Summary
                    </h4>
                    <p className="text-sm text-white leading-relaxed">
                      {analysisResult.plain_language_explanation}
                    </p>
                  </div>
                )}

                {/* Answer / Findings */}
                {analysisResult.answer && (
                  <div className="rounded-lg border border-white/10 bg-surface p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      AI Analysis Findings
                    </h4>
                    <p className="text-sm text-white whitespace-pre-line leading-relaxed">
                      {analysisResult.answer}
                    </p>
                  </div>
                )}

                {/* Citations & Evidence */}
                {analysisResult.citations && analysisResult.citations.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                      Claim-Level Citations & Audit Trail
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {analysisResult.citations.map((c, i) => (
                        <CitationChip
                          key={i}
                          page={c.page || 1}
                          section={c.section || "Clause"}
                          verified={c.verified ?? true}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Questions to Ask Lender */}
                {analysisResult.questions_to_ask_provider && analysisResult.questions_to_ask_provider.length > 0 && (
                  <div className="rounded-lg border border-warning/20 bg-warning/5 p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-warning mb-2">
                      <i className="fa-solid fa-circle-question mr-1.5" /> Recommended Questions for Lender
                    </h4>
                    <ul className="space-y-1.5 text-xs text-white/90 list-disc list-inside">
                      {analysisResult.questions_to_ask_provider.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
