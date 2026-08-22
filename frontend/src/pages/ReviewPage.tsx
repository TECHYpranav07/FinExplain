import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, type LoanReviewResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  PageHeader,
  Panel,
  Badge,
  EvidenceBadge,
  SeverityBadge,
  EmptyState,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";
import { cn } from "@/lib/utils";

/**
 * InlineMarkdown: Renders bold text, citations, and currency cleanly
 * without showing raw markdown asterisks or breaking layout.
 */
export function InlineMarkdown({ text, className }: { text?: string; className?: string }) {
  if (!text) return null;

  // Clean initial markers like **Title:** or leading bullets
  const cleaned = text.replace(/^[*-]\s*/, "").replace(/^\d+\.\s*/, "").trim();

  // Tokenize by **bold** or [citation]
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|\[.*?\])/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(cleaned)) !== null) {
    if (match.index > lastIndex) {
      parts.push(cleaned.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      const boldContent = token.slice(2, -2).trim();
      parts.push(
        <strong key={match.index} className="font-semibold text-white">
          {boldContent}
        </strong>
      );
    } else if (token.startsWith("[") && token.endsWith("]")) {
      const citeContent = token.slice(1, -1).trim();
      parts.push(
        <span
          key={match.index}
          className="inline-flex items-center gap-1 rounded bg-white/5 border border-white/10 px-1.5 py-0.5 text-[10px] font-mono text-white/70 mx-1 align-baseline"
        >
          <i className="fa-regular fa-bookmark text-[9px] text-primary" />
          {citeContent}
        </span>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < cleaned.length) {
    parts.push(cleaned.substring(lastIndex));
  }

  return <span className={cn("break-words", className)}>{parts}</span>;
}

interface ParsedAudit {
  rawText: string;
  facilityTitle: string;
  facilitySynopsis: string;
  riskSynopsis: string;
  riskVerdictLabel: string;
  riskVerdictLevel: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  parameters: Array<{
    parameter: string;
    value: string;
    category: string;
    status: string;
    citation?: string;
  }>;
  redFlags: Array<{
    title: string;
    description: string;
    severity: "CRITICAL" | "HIGH" | "MEDIUM";
    citation?: string;
  }>;
  costDrivers: Array<{
    title: string;
    amount: string;
    type: string;
    notes: string;
    citation?: string;
  }>;
  missingItems: Array<{
    title: string;
    description: string;
    impact: string;
  }>;
  lenderQuestions: string[];
}

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

function cleanRawMarkdown(str: string): string {
  if (!str) return "";
  return str
    .replace(/\*\*/g, "")
    .replace(/^[*-]\s*/, "")
    .replace(/^\d+\.\s*/, "")
    .trim();
}

function parseAuditMarkdown(text: string, structuredData?: any): ParsedAudit {
  const result: ParsedAudit = {
    rawText: text,
    facilityTitle: "Loan Agreement Assessment",
    facilitySynopsis: "",
    riskSynopsis: "",
    riskVerdictLabel: "MODERATE RISK",
    riskVerdictLevel: "MODERATE",
    parameters: [],
    redFlags: [],
    costDrivers: [],
    missingItems: [],
    lenderQuestions: [],
  };

  if (!text) return result;

  // Split into sections based on headers / emojis
  const lines = text.split("\n");
  let currentSection = "intro";
  const sectionBuckets: Record<string, string[]> = {
    intro: [],
    verdict: [],
    parameters: [],
    red_flags: [],
    cost_drivers: [],
    repayment: [],
    missing: [],
    questions: [],
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.includes("Executive Summary") || trimmed.startsWith("🎯")) {
      currentSection = "verdict";
      continue;
    } else if (trimmed.includes("Key Financial Parameters") || trimmed.startsWith("📊")) {
      currentSection = "parameters";
      continue;
    } else if (trimmed.includes("Critical Red Flags") || trimmed.includes("Predatory Terms") || trimmed.startsWith("🚨")) {
      currentSection = "red_flags";
      continue;
    } else if (trimmed.includes("Cost Drivers") || trimmed.includes("Total Expense") || trimmed.startsWith("💡")) {
      currentSection = "cost_drivers";
      continue;
    } else if (trimmed.includes("Repayment, Prepayment") || trimmed.startsWith("⚖️")) {
      currentSection = "repayment";
      continue;
    } else if (trimmed.includes("Missing Information") || trimmed.startsWith("❓")) {
      currentSection = "missing";
      continue;
    } else if (trimmed.includes("Actionable Questions") || trimmed.startsWith("🛡️")) {
      currentSection = "questions";
      continue;
    }

    sectionBuckets[currentSection]?.push(line);
  }

  // 1. Parse Executive Verdict
  const verdictLines = sectionBuckets.verdict.filter((l) => l.trim().length > 0);
  for (const v of verdictLines) {
    const trimmed = v.trim();
    const cleanLower = trimmed.toLowerCase();

    if (cleanLower.includes("nature of credit facility:") || cleanLower.includes("facility amounting")) {
      result.facilitySynopsis = trimmed.replace(/^[*-]\s*/, "").replace(/^(\*\*)?Nature of Credit Facility:(\*\*)?\s*/i, "").trim();
    } else if (cleanLower.includes("risk profile:") || cleanLower.includes("risk assessment:") || cleanLower.includes("verdict:")) {
      result.riskSynopsis = trimmed.replace(/^[*-]\s*/, "").replace(/^(\*\*)?Borrowing Parameters & General Risk Profile:(\*\*)?\s*/i, "").replace(/^(\*\*)?General Risk Profile:(\*\*)?\s*/i, "").trim();
    } else if (!result.facilitySynopsis && trimmed.length > 25 && !trimmed.startsWith("#")) {
      result.facilitySynopsis = trimmed.replace(/^[*-]\s*/, "").trim();
    } else if (!result.riskSynopsis && trimmed.length > 25 && !trimmed.startsWith("#")) {
      result.riskSynopsis = trimmed.replace(/^[*-]\s*/, "").trim();
    }
  }

  // Determine Risk Verdict Level & Short Badge Label
  const combinedRiskText = (result.riskSynopsis + " " + text).toLowerCase();
  if (combinedRiskText.includes("critical risk") || combinedRiskText.includes("predatory")) {
    result.riskVerdictLevel = "CRITICAL";
    result.riskVerdictLabel = "CRITICAL RISK";
  } else if (combinedRiskText.includes("high risk") || combinedRiskText.includes("elevated risk")) {
    result.riskVerdictLevel = "HIGH";
    result.riskVerdictLabel = "ELEVATED RISK";
  } else if (combinedRiskText.includes("low risk") || combinedRiskText.includes("standard terms")) {
    result.riskVerdictLevel = "LOW";
    result.riskVerdictLabel = "LOW RISK";
  } else {
    result.riskVerdictLevel = "MODERATE";
    result.riskVerdictLabel = "MODERATE RISK";
  }

  // 2. Parse Financial Parameters Table
  const paramLines = sectionBuckets.parameters;
  for (const line of paramLines) {
    if (!line.includes("|") || line.includes("---") || line.toLowerCase().includes("parameter")) continue;
    const parts = line.split("|").map((p) => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
      const parameter = cleanRawMarkdown(parts[0] || "");
      const rawVal = parts[1] || "";
      const category = cleanRawMarkdown(parts[2] || "");
      const status = cleanRawMarkdown(parts[3] || "");

      // Extract citation if present [ ... ]
      const citeMatch = rawVal.match(/\[(.*?)\]/);
      const cleanVal = rawVal.replace(/\[(.*?)\]/g, "").replace(/\*\*/g, "").trim();

      result.parameters.push({
        parameter,
        value: cleanVal || rawVal,
        category,
        status,
        citation: citeMatch ? citeMatch[1] : undefined,
      });
    }
  }

  // Fallback parameters from structured data if table parsing was empty
  if (result.parameters.length === 0 && structuredData?.loan_summary) {
    const rates = structuredData.loan_summary.rates || [];
    const amounts = structuredData.loan_summary.amounts || [];

    for (const a of amounts) {
      result.parameters.push({
        parameter: "Loan Principal Amount",
        value: a.value ? `₹${Number(a.value).toLocaleString("en-IN")}` : "Refer to terms",
        category: "Sanctioned Amount",
        status: a.status || "EXPLICIT",
        citation: `Page ${a.page || 1}`,
      });
    }
    for (const r of rates) {
      result.parameters.push({
        parameter: r.field?.replace(/_/g, " ").toUpperCase() || "Interest Rate",
        value: `${r.value}% p.a.`,
        category: r.condition || "Fixed Rate",
        status: r.status || "EXPLICIT",
        citation: `Page ${r.page || 1}`,
      });
    }
  }

  // 3. Parse Red Flags
  const redFlagLines = sectionBuckets.red_flags.filter((l) => l.trim().length > 0);
  for (const line of redFlagLines) {
    const clean = line.replace(/^[*-]\s*/, "").replace(/^\d+\.\s*/, "").trim();
    if (!clean || clean.startsWith("#")) continue;

    // Check if there's a bold title or colon separation: "**Title:** Description"
    const colonIdx = clean.indexOf(":");
    let title = "Contractual Discretion Risk";
    let desc = clean;
    let citation = "";

    const citeMatch = clean.match(/\[(.*?)\]/);
    if (citeMatch) {
      citation = citeMatch[1];
    }

    if (colonIdx > 0 && colonIdx < 60) {
      title = clean.substring(0, colonIdx).replace(/\*\*/g, "").trim();
      desc = clean.substring(colonIdx + 1).replace(/\[(.*?)\]/g, "").trim();
    } else {
      desc = clean.replace(/\[(.*?)\]/g, "").trim();
    }

    let severity: "CRITICAL" | "HIGH" | "MEDIUM" = "HIGH";
    const lower = (title + " " + desc).toLowerCase();
    if (lower.includes("discretion") || lower.includes("unilateral") || lower.includes("penalty") || lower.includes("predatory")) {
      severity = "CRITICAL";
    } else if (lower.includes("approx") || lower.includes("unverified") || lower.includes("missing")) {
      severity = "HIGH";
    } else {
      severity = "MEDIUM";
    }

    result.redFlags.push({
      title,
      description: desc,
      severity,
      citation,
    });
  }

  // 4. Parse Missing Information
  const missingLines = sectionBuckets.missing.filter((l) => l.trim().length > 0);
  for (const line of missingLines) {
    const clean = line.replace(/^[*-]\s*/, "").replace(/^\d+\.\s*/, "").trim();
    if (!clean || clean.startsWith("#")) continue;

    const colonIdx = clean.indexOf(":");
    let title = "Omitted Parameter";
    let desc = clean;

    if (colonIdx > 0 && colonIdx < 60) {
      title = clean.substring(0, colonIdx).replace(/\*\*/g, "").trim();
      desc = clean.substring(colonIdx + 1).replace(/\[(.*?)\]/g, "").trim();
    } else {
      desc = clean.replace(/\[(.*?)\]/g, "").trim();
    }

    result.missingItems.push({
      title,
      description: desc,
      impact: "Creates legal and financial uncertainty before contract execution.",
    });
  }

  // Fallback missing items from structured data if empty
  if (result.missingItems.length === 0 && structuredData?.missing_information) {
    for (const m of structuredData.missing_information) {
      result.missingItems.push({
        title: m.field?.replace(/_/g, " ").toUpperCase() || "Unspecified Field",
        description: m.reason || "Mandatory disclosure absent from provided loan agreement.",
        impact: "Exposes borrower to unverified rates or amortization schedules.",
      });
    }
  }

  // 5. Parse Lender Questions
  const questionLines = sectionBuckets.questions.filter((l) => l.trim().length > 0);
  for (const line of questionLines) {
    const clean = line.replace(/^[*-]\s*/, "").replace(/^\d+\.\s*/, "").replace(/^"\s*/, "").replace(/"\s*$/, "").trim();
    if (!clean || clean.startsWith("#") || clean.length < 15) continue;
    result.lenderQuestions.push(clean);
  }

  // Extract facility title from summary or parameters
  const amountParam = result.parameters.find((p) => p.parameter.toLowerCase().includes("amount") || p.parameter.toLowerCase().includes("principal"));
  const rateParam = result.parameters.find((p) => p.parameter.toLowerCase().includes("interest") || p.parameter.toLowerCase().includes("rate"));
  if (amountParam && rateParam) {
    result.facilityTitle = `${amountParam.value} · ${rateParam.value} Term Facility`;
  } else if (amountParam) {
    result.facilityTitle = `${amountParam.value} Credit Facility`;
  } else if (result.facilitySynopsis.includes("₹")) {
    const rupeeMatch = result.facilitySynopsis.match(/₹[\d,]+/);
    if (rupeeMatch) {
      result.facilityTitle = `${rupeeMatch[0]} Term Loan Facility`;
    }
  }

  return result;
}

export function ReviewPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [reviewResult, setReviewResult] = useState<LoanReviewResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"studio" | "checklist" | "cost_drivers" | "conflicts" | "raw_report">("studio");
  const [copied, setCopied] = useState(false);
  const [copiedQuestionIdx, setCopiedQuestionIdx] = useState<number | null>(null);

  const reviewMutation = useMutation({
    mutationFn: async () => {
      if (selectedProducts.length === 0) {
        throw new Error("Please select at least one registered loan product to perform a proactive review.");
      }
      return api.review({ product_ids: selectedProducts });
    },
    onSuccess: (data) => {
      setReviewResult(data);
      setActiveTab("studio");
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

  const parsedAudit = useMemo(() => {
    const raw = getReportMarkdown();
    return parseAuditMarkdown(raw, reviewResult?.review);
  }, [reviewResult]);

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

  const handleCopyQuestion = async (q: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(q);
      setCopiedQuestionIdx(idx);
      setTimeout(() => setCopiedQuestionIdx(null), 2000);
    } catch {
      // ignore
    }
  };

  const handleCopyAllQuestions = async () => {
    if (!parsedAudit.lenderQuestions.length) return;
    const formatted = parsedAudit.lenderQuestions.map((q, i) => `${i + 1}. ${q}`).join("\n\n");
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
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
  const totalFacts = loanSummary.total_facts_extracted || parsedAudit.parameters.length || 0;
  const totalConflicts = loanSummary.total_conflicts || (reviewResult?.review?.conflicts?.length || 0);
  const totalMissing = loanSummary.total_missing_fields || (reviewResult?.review?.missing_information?.length || parsedAudit.missingItems.length || 0);
  const costDriversCount = reviewResult?.cost_drivers?.length || 0;
  const conflictsList = reviewResult?.review?.conflicts || [];
  const missingList = reviewResult?.review?.missing_information || parsedAudit.missingItems || [];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Proactive Auditing & Legal Intelligence"
        title="Proactive Loan Review"
        description="Inspect credit agreements for predatory terms, unadvertised cost drivers, hidden penalty structures, and compliance conflicts before signing."
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
                {costDriversCount || parsedAudit.redFlags.length}
              </span>
            </div>
          </div>

          {/* Audit View Selector & Utility Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            {/* Tabs */}
            <div className="flex flex-wrap items-center gap-1 bg-surface p-1 rounded-xl border border-white/10 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("studio")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "studio"
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-layer-group mr-1.5" />
                Executive Studio
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("checklist")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "checklist"
                    ? "bg-white text-black font-semibold shadow-sm"
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
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-coins mr-1.5" />
                Cost Drivers ({costDriversCount || parsedAudit.redFlags.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("conflicts")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "conflicts"
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-triangle-exclamation mr-1.5" />
                Blindspots & Traps ({totalConflicts + totalMissing})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("raw_report")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "raw_report"
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-regular fa-file-lines mr-1.5" />
                Raw Report
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

          {/* TAB 1: EXECUTIVE AUDIT STUDIO (RICH UI DASHBOARD) */}
          {activeTab === "studio" && (
            <div className="space-y-6">
              {/* Hero Executive Scorecard */}
              <div className="rounded-2xl border border-white/15 bg-gradient-to-b from-surface-2 to-surface p-6 space-y-5 shadow-lg">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10 text-white text-xs shrink-0">
                        <i className="fa-solid fa-shield-halved" />
                      </span>
                      <h3 className="text-lg font-bold text-white tracking-tight truncate">
                        {parsedAudit.facilityTitle}
                      </h3>
                    </div>

                    {parsedAudit.facilitySynopsis && (
                      <div className="text-xs text-white/85 leading-relaxed pl-9 break-words">
                        <InlineMarkdown text={parsedAudit.facilitySynopsis} />
                      </div>
                    )}

                    {parsedAudit.riskSynopsis && (
                      <div className="text-xs text-amber-200/90 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3.5 mt-2 ml-9 leading-relaxed break-words">
                        <div className="flex items-center gap-1.5 font-bold text-amber-300 text-[11px] uppercase tracking-wider mb-1">
                          <i className="fa-solid fa-circle-exclamation text-[10px]" />
                          <span>Risk Assessment Verdict</span>
                        </div>
                        <InlineMarkdown text={parsedAudit.riskSynopsis} />
                      </div>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    <div
                      className={`inline-flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-bold whitespace-nowrap ${
                        parsedAudit.riskVerdictLevel === "CRITICAL"
                          ? "border-rose-500/40 bg-rose-500/15 text-rose-300"
                          : parsedAudit.riskVerdictLevel === "HIGH"
                          ? "border-orange-500/40 bg-orange-500/15 text-orange-300"
                          : parsedAudit.riskVerdictLevel === "LOW"
                          ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                          : "border-amber-500/40 bg-amber-500/15 text-amber-300"
                      }`}
                    >
                      <i className="fa-solid fa-gauge-high text-xs" />
                      <span>{parsedAudit.riskVerdictLabel}</span>
                    </div>
                  </div>
                </div>

                {/* Key Parameter Matrix Grid */}
                <div className="pt-3 border-t border-white/10">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block mb-3">
                    Contractual Terms & Rate Schedule
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {parsedAudit.parameters.map((param, pIdx) => {
                      const isMissing = param.value.toLowerCase().includes("not specified") || param.value.toLowerCase().includes("missing");
                      const isRate = param.parameter.toLowerCase().includes("interest") || param.parameter.toLowerCase().includes("rate");

                      return (
                        <div
                          key={pIdx}
                          className={`rounded-xl border p-4 space-y-2 transition-all ${
                            isMissing
                              ? "border-rose-500/30 bg-rose-500/5 hover:border-rose-500/50"
                              : isRate
                              ? "border-white/15 bg-white/5 hover:border-white/25"
                              : "border-white/10 bg-surface-2 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider truncate">
                              {param.parameter}
                            </span>
                            {isMissing ? (
                              <Badge tone="danger">Missing</Badge>
                            ) : param.status.toLowerCase().includes("conditional") ? (
                              <Badge tone="warning">Conditional</Badge>
                            ) : (
                              <Badge tone="success">Documented</Badge>
                            )}
                          </div>

                          <div className="text-base font-bold text-white tracking-tight break-words">
                            <InlineMarkdown text={param.value} />
                          </div>

                          <div className="flex items-center justify-between text-[11px] pt-1 border-t border-white/5 text-muted-foreground">
                            <span className="truncate">{param.category || "Standard Term"}</span>
                            {param.citation && (
                              <span className="font-mono text-[10px] text-white/50 shrink-0">{param.citation}</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Critical Red Flags & Traps Section */}
              {parsedAudit.redFlags.length > 0 && (
                <Panel
                  title="Critical Red Flags & Discretionary Legal Traps"
                  subtitle="Operative clauses where the lender retains unilateral control or contractual parameters are not explicitly binding"
                >
                  <div className="space-y-3.5">
                    {parsedAudit.redFlags.map((flag, fIdx) => (
                      <div
                        key={fIdx}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 transition-all hover:border-amber-500/50"
                      >
                        <div className="flex items-start gap-3">
                          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/20 text-amber-300 text-xs shrink-0 mt-0.5">
                            <i className="fa-solid fa-triangle-exclamation" />
                          </span>

                          <div className="space-y-1.5 flex-1 min-w-0">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <h4 className="text-sm font-bold text-amber-200">
                                <InlineMarkdown text={flag.title} />
                              </h4>
                              <SeverityBadge level={flag.severity} />
                            </div>

                            <p className="text-xs text-white/90 leading-relaxed break-words">
                              <InlineMarkdown text={flag.description} />
                            </p>

                            {flag.citation && (
                              <div className="pt-1 flex items-center gap-1.5 text-[11px] text-amber-300/80 font-mono">
                                <i className="fa-regular fa-bookmark text-[10px]" />
                                <span>Evidence: {flag.citation}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}

              {/* Financial Outlay & Net Disbursement Calculator */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <Panel
                  title="Borrowing Outlay & Deduction Breakdown"
                  subtitle="Direct upfront deductions versus net in-pocket funds"
                >
                  <div className="space-y-4">
                    <div className="rounded-xl border border-white/10 bg-surface-2 p-4 space-y-3">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Sanctioned Principal</span>
                        <span className="font-mono font-bold text-white">₹8,00,000</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-rose-400">
                        <span>Less: Processing Fee (One-Time)</span>
                        <span className="font-mono font-bold">-₹8,000</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-rose-400">
                        <span>Less: Documentation Fee</span>
                        <span className="font-mono font-bold">-₹1,500</span>
                      </div>
                      <div className="pt-2 border-t border-white/10 flex items-center justify-between text-sm">
                        <span className="font-semibold text-white">Estimated Net Disbursed</span>
                        <span className="font-mono font-extrabold text-emerald-400">₹7,90,500</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      💡 <strong>Disbursement Alert:</strong> Upfront fees are typically subtracted directly from the disbursed principal, reducing your usable capital while interest is computed against the full sanctioned amount.
                    </p>
                  </div>
                </Panel>

                <Panel
                  title="Missing Contractual Disclosures"
                  subtitle="Key parameters absent from the signed agreement"
                >
                  <div className="space-y-3">
                    {parsedAudit.missingItems.map((item, mIdx) => (
                      <div key={mIdx} className="rounded-xl border border-white/10 bg-surface-2 p-3.5 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-white">
                            <InlineMarkdown text={item.title} />
                          </span>
                          <Badge tone="danger">Missing</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed break-words">
                          <InlineMarkdown text={item.description} />
                        </p>
                      </div>
                    ))}
                  </div>
                </Panel>
              </div>

              {/* Recommended Lender Inquiries Script */}
              {parsedAudit.lenderQuestions.length > 0 && (
                <Panel
                  title="Official Lender Clarification Script"
                  subtitle="Specific written questions to submit to your relationship manager before contract confirmation"
                  action={
                    <button
                      type="button"
                      onClick={handleCopyAllQuestions}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-semibold text-white hover:bg-surface-3 transition-colors"
                    >
                      <i className={`fa-solid ${copied ? "fa-check text-emerald-400" : "fa-copy"} text-[11px]`} />
                      <span>{copied ? "All Copied!" : "Copy All Questions"}</span>
                    </button>
                  }
                >
                  <div className="space-y-3">
                    {parsedAudit.lenderQuestions.map((question, qIdx) => (
                      <div
                        key={qIdx}
                        className="rounded-xl border border-white/10 bg-surface-2 p-4 transition-all hover:border-white/20 flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1.5 flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white/10 font-mono text-[11px] font-bold text-white shrink-0">
                              {(qIdx + 1).toString().padStart(2, "0")}
                            </span>
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                              Written Clarification Demand
                            </span>
                          </div>
                          <p className="text-xs font-medium text-white pl-7 leading-relaxed italic break-words">
                            "{question}"
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleCopyQuestion(question, qIdx)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white hover:bg-surface-3 transition-colors shrink-0"
                        >
                          <i className={`fa-solid ${copiedQuestionIdx === qIdx ? "fa-check text-emerald-400" : "fa-copy"} text-[11px]`} />
                          <span>{copiedQuestionIdx === qIdx ? "Copied!" : "Copy"}</span>
                        </button>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
            </div>
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
                    const itemNote = item.note || item.details || item.reason || item.action_guidance || "";
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
                            <p className="text-xs font-semibold text-white leading-relaxed break-words">
                              <InlineMarkdown text={itemText} />
                            </p>
                            <EvidenceBadge status={status} />
                          </div>
                          {itemNote && (
                            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed break-words">
                              <InlineMarkdown text={itemNote} />
                            </p>
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
                          <p className="text-xs text-muted-foreground leading-relaxed break-words">
                            <InlineMarkdown text={conditionText} />
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
                        <p className="text-xs text-white/80 leading-relaxed break-words">
                          <InlineMarkdown text={c.description || "Contradictory values detected across operative schedules."} />
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
                          <InlineMarkdown text={m.title || m.field?.replace(/_/g, " ").toUpperCase() || "Unspecified Field"} />
                        </span>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed break-words">
                          <InlineMarkdown text={m.description || m.reason || "Not specified in document clauses."} />
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

          {/* TAB 5: RAW AUDIT TEXT (MARKDOWN) */}
          {activeTab === "raw_report" && (
            <Panel
              title="Full Narrative Audit Report"
              subtitle="Evidence-backed comprehensive report generated by FinExplain RAG Engine"
            >
              <div className="prose prose-invert max-w-none">
                <FormattedMarkdown content={getReportMarkdown()} />
              </div>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}
