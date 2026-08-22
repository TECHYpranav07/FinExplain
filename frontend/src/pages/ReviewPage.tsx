import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, type LoanReviewResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  PageHeader,
  Panel,
  Badge,
  EvidenceBadge,
  EmptyState,
  ErrorState,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";

function parseCostDriver(cd: any) {
  if (typeof cd === "string") {
    try {
      return JSON.parse(cd);
    } catch {
      return { description: cd };
    }
  }
  return cd || {};
}

export function ReviewPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [reviewResult, setReviewResult] = useState<LoanReviewResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"report" | "checklist" | "cost_drivers" | "conflicts">("report");
  const [copied, setCopied] = useState(false);

  const reviewMutation = useMutation({
    mutationFn: async () => {
      if (selectedProducts.length === 0) {
        throw new Error("Please select at least one registered loan product to perform a proactive review.");
      }
      return api.review({ product_ids: selectedProducts });
    },
    onSuccess: (data) => {
      setReviewResult(data);
      setActiveTab("report");
    },
  });

  const handleRunReview = () => {
    reviewMutation.mutate();
  };

  const getReportMarkdown = (): string => {
    if (!reviewResult) return "";
    if (typeof reviewResult.review === "string") return reviewResult.review;
    if (reviewResult.review_text) return reviewResult.review_text;
    return "Proactive loan audit completed.";
  };

  const handleCopyReport = async () => {
    const text = getReportMarkdown();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard error
    }
  };

  const handleDownloadReport = () => {
    const text = getReportMarkdown();
    if (!text) return;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `FinExplain_Audit_Report_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const loanSummary = reviewResult?.review?.loan_summary || {};
  const totalFacts = loanSummary.total_facts_extracted || 0;
  const totalConflicts = loanSummary.total_conflicts || (reviewResult?.review?.conflicts?.length || 0);
  const totalMissing = loanSummary.total_missing_fields || (reviewResult?.review?.missing_information?.length || 0);
  const costDriversCount = reviewResult?.cost_drivers?.length || 0;
  const conflictsList = reviewResult?.review?.conflicts || [];
  const missingList = reviewResult?.review?.missing_information || [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Proactive Auditing"
        title="Proactive Loan Review"
        description="Automatically inspect agreements for predatory terms, unadvertised cost drivers, hidden penalties, and compliance conflicts before signing."
        action={
          <button
            type="button"
            onClick={handleRunReview}
            disabled={reviewMutation.isPending || selectedProducts.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40 transition-colors shadow-sm"
          >
            {reviewMutation.isPending ? (
              <>
                <i className="fa-solid fa-spinner fa-spin text-xs" />
                Auditing Agreement...
              </>
            ) : (
              <>
                <i className="fa-solid fa-bolt text-xs" />
                Run Proactive Review
              </>
            )}
          </button>
        }
      />

      {/* Product Selection */}
      <Panel
        title="Select Target Loan Product"
        subtitle="Choose which registered credit facility to audit"
      >
        <ProductPicker
          selected={selectedProducts}
          onChange={setSelectedProducts}
          multiple={false}
        />
      </Panel>

      {/* Review Output Area */}
      {reviewMutation.isError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 space-y-3.5">
          <div className="flex items-start gap-3">
            <i className="fa-solid fa-circle-exclamation text-rose-400 text-lg mt-0.5" />
            <div className="space-y-1 flex-1">
              <h4 className="text-sm font-semibold text-rose-300">Document Upload Required</h4>
              <p className="text-xs text-white/80 leading-relaxed">
                {reviewMutation.error instanceof Error
                  ? reviewMutation.error.message
                  : "No document clauses found for the selected loan product."}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-rose-500/20">
            <Link
              to="/app/documents"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90 transition-colors shadow-sm"
            >
              <i className="fa-regular fa-file-lines text-xs" />
              <span>Go to Documents & Upload PDF</span>
            </Link>
            <button
              type="button"
              onClick={handleRunReview}
              className="rounded-lg border border-white/10 bg-surface px-4 py-2 text-xs font-medium text-white/80 hover:text-white hover:bg-surface-2 transition-colors"
            >
              Retry Audit
            </button>
          </div>
        </div>
      )}

      {!reviewResult && !reviewMutation.isPending && !reviewMutation.isError && (
        <EmptyState
          title="No Active Audit Results"
          description="Select a loan product above and click 'Run Proactive Review' to scan for hidden fees, penalty structures, and legal risks."
          icon="fa-shield-halved"
        />
      )}

      {reviewMutation.isPending && (
        <div className="py-20 flex flex-col items-center justify-center gap-4 text-center">
          <div className="relative flex items-center justify-center">
            <div className="h-16 w-16 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            <i className="fa-solid fa-shield-halved absolute text-lg text-white" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-white">Scanning document clauses for financial hazards...</p>
            <p className="text-xs text-muted-foreground">Evaluating cost drivers, lock-in terms, and penalty ceilings</p>
          </div>
        </div>
      )}

      {reviewResult && (
        <div className="space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Audited Clauses
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {totalFacts}
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Contractual Conflicts
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-2xl font-bold ${totalConflicts > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                  {totalConflicts}
                </span>
                {totalConflicts > 0 && <Badge tone="warning">Attention</Badge>}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Missing Disclosures
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {totalMissing}
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Cost Drivers
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {costDriversCount}
              </span>
            </div>
          </div>

          {/* Audit View Selector & Utility Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            {/* Tabs */}
            <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-white/10 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("report")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "report"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-file-contract mr-1.5" />
                Audit Report
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("checklist")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "checklist"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-list-check mr-1.5" />
                Checklist ({reviewResult.checklist?.length || 0})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("cost_drivers")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "cost_drivers"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-coins mr-1.5" />
                Cost Drivers ({costDriversCount})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("conflicts")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "conflicts"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-triangle-exclamation mr-1.5" />
                Conflicts & Omissions ({totalConflicts + totalMissing})
              </button>
            </div>

            {/* Export Actions */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyReport}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white hover:border-white/20 transition-colors"
              >
                <i className={`fa-solid ${copied ? "fa-check text-emerald-400" : "fa-copy"} text-[11px]`} />
                <span>{copied ? "Copied!" : "Copy Report"}</span>
              </button>
              <button
                type="button"
                onClick={handleDownloadReport}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white hover:border-white/20 transition-colors"
              >
                <i className="fa-solid fa-download text-[11px]" />
                <span>Download .MD</span>
              </button>
            </div>
          </div>

          {/* TAB 1: EXECUTIVE AUDIT REPORT */}
          {activeTab === "report" && (
            <Panel
              title="Proactive Audit Executive Summary"
              subtitle="Evidence-backed legal and financial risk profile generated by FinExplain RAG Engine"
            >
              <div className="prose prose-invert max-w-none">
                <FormattedMarkdown content={getReportMarkdown()} />
              </div>
            </Panel>
          )}

          {/* TAB 2: ACTIONABLE CHECKLIST */}
          {activeTab === "checklist" && (
            <Panel
              title="Decision Verification Checklist"
              subtitle="Prioritized verification items: ✓ Confirmed, ⚠ Conditional/Caution, ? Missing from document"
            >
              {reviewResult.checklist && reviewResult.checklist.length > 0 ? (
                <div className="space-y-3">
                  {reviewResult.checklist.map((item: any, idx: number) => {
                    const marker = item.marker || (item.status === "EXPLICIT" ? "✓" : item.status === "MISSING" ? "?" : "⚠");
                    const itemText = item.item || item.title || item.action || item.question || (typeof item === "string" ? item : "Clause check");
                    const itemNote = item.note || item.details || item.reason || "";
                    const status = item.status || (marker === "✓" ? "EXPLICIT" : marker === "?" ? "MISSING" : "CONDITIONAL");

                    return (
                      <div
                        key={idx}
                        className="flex items-start gap-3.5 rounded-xl border border-white/10 bg-surface-2 p-4 transition-colors hover:border-white/20"
                      >
                        <span
                          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                            marker === "✓"
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                              : marker === "⚠"
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                          }`}
                        >
                          {marker}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs font-semibold text-white leading-relaxed">
                              {itemText}
                            </p>
                            <EvidenceBadge status={status} />
                          </div>
                          {itemNote && (
                            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">{itemNote}</p>
                          )}
                          {item.evidence && (
                            <div className="mt-2 text-[11px] text-white/50 font-mono">
                              Source: Page {item.evidence.page_number || "Doc"} {item.evidence.section_title ? `· ${item.evidence.section_title}` : ""}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No Checklist Items"
                  description="All contractual terms and conditions are summarized in the main audit report."
                  icon="fa-list-check"
                />
              )}
            </Panel>
          )}

          {/* TAB 3: COST DRIVERS */}
          {activeTab === "cost_drivers" && (
            <Panel
              title="Identified Cost Drivers & Fee Structures"
              subtitle="All direct, indirect, and penalty expenses identified in operative clauses"
            >
              {reviewResult.cost_drivers && reviewResult.cost_drivers.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {reviewResult.cost_drivers.map((rawCd: any, idx: number) => {
                    const cd = parseCostDriver(rawCd);
                    const title =
                      cd.field
                        ? cd.field.replace(/_/g, " ").replace(/\b\w/g, (l: string) => l.toUpperCase())
                        : cd.name || cd.category?.toUpperCase() || `Cost Factor #${idx + 1}`;
                    const formattedValue =
                      cd.value !== undefined && cd.value !== null && cd.value !== ""
                        ? `${cd.value}${cd.unit === "percent" || String(cd.value).includes("%") ? "%" : cd.currency ? " " + cd.currency : ""}`
                        : cd.amount || "Refer to terms";
                    const conditionText = cd.condition || cd.description || cd.details || "Applicable under document clauses.";
                    const status = cd.status || "CONDITIONAL";

                    return (
                      <div
                        key={idx}
                        className="rounded-xl border border-white/10 bg-surface-2 p-4 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2 gap-2">
                            <span className="text-xs font-semibold text-white truncate" title={title}>
                              {title}
                            </span>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {cd.priority === "HIGH" && <Badge tone="danger">HIGH PRIORITY</Badge>}
                              <EvidenceBadge status={status} />
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {conditionText}
                          </p>
                        </div>
                        <div className="mt-4 pt-2.5 border-t border-white/5 flex items-center justify-between">
                          {cd.page ? (
                            <span className="text-[10px] text-white/50">
                              Page {cd.page} {cd.source_document ? `(${cd.source_document})` : ""}
                            </span>
                          ) : (
                            <span className="text-[10px] text-white/40">Source Verified</span>
                          )}
                          <span className="font-mono text-xs font-bold text-white bg-white/5 px-2 py-0.5 rounded border border-white/10">
                            {formattedValue}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No Cost Drivers Detected"
                  description="No explicit fee schedules were detected in the analyzed clauses."
                  icon="fa-coins"
                />
              )}
            </Panel>
          )}

          {/* TAB 4: CONFLICTS & OMISSIONS */}
          {activeTab === "conflicts" && (
            <div className="space-y-6">
              <Panel
                title="Contractual Conflicts & Discrepancies"
                subtitle="Inconsistencies detected between summary sheets (KFS) and operative loan agreements"
              >
                {conflictsList.length > 0 ? (
                  <div className="space-y-3">
                    {conflictsList.map((c: any, idx: number) => (
                      <div key={idx} className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-rose-300">
                            Conflict in {c.field || "Contract Clause"}
                          </span>
                          <Badge tone="danger">HIGH RISK</Badge>
                        </div>
                        <p className="text-xs text-white/80 leading-relaxed">
                          {c.description || "Contradictory values detected across operative schedules."}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-center">
                    <i className="fa-solid fa-circle-check text-emerald-400 text-xl mb-1.5 block" />
                    <p className="text-xs font-semibold text-emerald-300">No Direct Contractual Conflicts Found</p>
                    <p className="text-[11px] text-emerald-400/70 mt-0.5">Operative schedules and summary statements match consistently.</p>
                  </div>
                )}
              </Panel>

              <Panel
                title="Missing Information & Blindspots"
                subtitle="Mandatory or critical disclosures absent from provided documentation"
              >
                {missingList.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    {missingList.map((m: any, idx: number) => (
                      <div key={idx} className="rounded-xl border border-white/10 bg-surface-2 p-3.5">
                        <span className="text-xs font-semibold text-white block">
                          {m.field?.replace(/_/g, " ").toUpperCase() || "Unspecified Field"}
                        </span>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {m.reason || "Not specified in document clauses."}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    title="All Standard Fields Accounted For"
                    description="No major disclosure omissions identified in the document."
                    icon="fa-shield-halved"
                  />
                )}
              </Panel>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

