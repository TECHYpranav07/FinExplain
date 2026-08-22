import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, type BeforeConfirmationResponse, type ChecklistItem } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  PageHeader,
  Panel,
  Badge,
  SeverityBadge,
  EvidenceBadge,
  EmptyState,
  ErrorState,
} from "@/components/finex/primitives";
import { FormattedMarkdown } from "@/components/finex/FormattedMarkdown";

export function BeforeConfirmationPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [result, setResult] = useState<BeforeConfirmationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"guide" | "checklist" | "questions" | "risks">("guide");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "VERIFIED" | "CAUTION" | "MISSING" | "CONFLICT">("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({});
  const [copiedBrief, setCopiedBrief] = useState(false);
  const [copiedQuestionIdx, setCopiedQuestionIdx] = useState<number | null>(null);

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (selectedProducts.length === 0) {
        throw new Error("Select at least one loan product to generate a pre-signing verification checklist.");
      }
      return api.beforeConfirmation({ product_ids: selectedProducts });
    },
    onSuccess: (data) => {
      setResult(data);
      setActiveTab("guide");
      setCheckedItems({});
    },
  });

  const handleGenerate = () => {
    confirmMutation.mutate();
  };

  const toggleCheckItem = (idx: number) => {
    setCheckedItems((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const getGuideMarkdown = (): string => {
    if (!result) return "";
    return result.checklist_text || "Pre-confirmation verification checklist compiled.";
  };

  const handleCopyBrief = async () => {
    const text = getGuideMarkdown();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedBrief(true);
      setTimeout(() => setCopiedBrief(false), 2000);
    } catch {
      // ignore clipboard error
    }
  };

  const handleCopySingleQuestion = async (q: string, idx: number) => {
    if (!q) return;
    try {
      await navigator.clipboard.writeText(q);
      setCopiedQuestionIdx(idx);
      setTimeout(() => setCopiedQuestionIdx(null), 2000);
    } catch {
      // ignore
    }
  };

  const handleDownloadBrief = () => {
    const text = getGuideMarkdown();
    if (!text) return;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `FinExplain_PreConfirmation_Checklist_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const checklist: ChecklistItem[] = result?.checklist || [];
  const totalItems = checklist.length;
  const verifiedCount = result?.summary?.verified_items ?? checklist.filter((i) => i.marker === "✓").length;
  const cautionCount = result?.summary?.caution_items ?? checklist.filter((i) => i.marker === "⚠").length;
  const missingCount = result?.summary?.missing_items ?? checklist.filter((i) => i.marker === "?").length;
  const conflictCount = result?.summary?.conflict_items ?? checklist.filter((i) => i.marker === "🚨").length;
  const checkedCount = Object.values(checkedItems).filter(Boolean).length;
  const progressPercent = totalItems > 0 ? Math.round((checkedCount / totalItems) * 100) : 0;

  // Extract unique categories for filter
  const categories = Array.from(
    new Set(
      checklist
        .map((i) => i.category)
        .filter((c): c is string => Boolean(c))
    )
  );

  // Filtered items for interactive checklist
  const filteredChecklist = checklist.map((item, originalIdx) => ({ item, originalIdx })).filter(({ item }) => {
    // Status filter
    if (statusFilter === "VERIFIED" && item.marker !== "✓") return false;
    if (statusFilter === "CAUTION" && item.marker !== "⚠") return false;
    if (statusFilter === "MISSING" && item.marker !== "?") return false;
    if (statusFilter === "CONFLICT" && item.marker !== "🚨") return false;

    // Category filter
    if (categoryFilter !== "ALL" && item.category !== categoryFilter) return false;

    return true;
  });

  // Questions extraction
  const questionItems = checklist
    .map((item, originalIdx) => ({ item, originalIdx }))
    .filter(({ item }) => Boolean(item.suggested_question));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Decision Support & Borrower Protection"
        title="Before You Confirm"
        description="A prioritized, actionable checklist of non-negotiable verifications, floating rate risks, and lender-facing questions before contract execution."
        action={
          <button
            type="button"
            onClick={handleGenerate}
            disabled={confirmMutation.isPending || selectedProducts.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40 transition-colors shadow-sm"
          >
            {confirmMutation.isPending ? (
              <>
                <i className="fa-solid fa-spinner fa-spin text-xs" />
                <span>Compiling Checklist...</span>
              </>
            ) : (
              <>
                <i className="fa-regular fa-circle-check text-xs" />
                <span>Generate Checklist</span>
              </>
            )}
          </button>
        }
      />

      {/* Target Products Picker */}
      <Panel
        title="Select Target Loan Product"
        subtitle="Choose which credit agreement to audit before confirmation and signing"
      >
        <ProductPicker
          selected={selectedProducts}
          onChange={setSelectedProducts}
          multiple={false}
        />
      </Panel>

      {confirmMutation.isError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 space-y-3.5">
          <div className="flex items-start gap-3">
            <i className="fa-solid fa-circle-exclamation text-rose-400 text-lg mt-0.5" />
            <div className="space-y-1 flex-1">
              <h4 className="text-sm font-semibold text-rose-300">Document Upload Required</h4>
              <p className="text-xs text-white/80 leading-relaxed">
                {confirmMutation.error instanceof Error
                  ? confirmMutation.error.message
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
              onClick={handleGenerate}
              className="rounded-lg border border-white/10 bg-surface px-4 py-2 text-xs font-medium text-white/80 hover:text-white hover:bg-surface-2 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {!result && !confirmMutation.isPending && !confirmMutation.isError && (
        <EmptyState
          icon="fa-regular fa-circle-check"
          title="No Pre-Confirmation Checklist Generated"
          description="Select a registered loan product above and click 'Generate Action Checklist' to inspect all contractual parameters, traps, and lender questions before signing."
        />
      )}

      {confirmMutation.isPending && (
        <div className="py-20 flex flex-col items-center justify-center gap-4 text-center">
          <div className="relative flex items-center justify-center">
            <div className="h-16 w-16 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            <i className="fa-solid fa-file-signature absolute text-lg text-white" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-white">Synthesizing pre-signing verification brief...</p>
            <p className="text-xs text-muted-foreground">Evaluating rate locks, net disbursement deductions, and exit penalty rules</p>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Quick Metrics & Verification Progress Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Total Items
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {totalItems}
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Verified Clear
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold text-emerald-400">
                  {verifiedCount}
                </span>
                <Badge tone="success">✓ Verified</Badge>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Caution & Conditions
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold text-amber-400">
                  {cautionCount}
                </span>
                {cautionCount > 0 && <Badge tone="warning">⚠ Caution</Badge>}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Missing Disclosures
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold text-rose-400">
                  {missingCount}
                </span>
                {missingCount > 0 && <Badge tone="danger">? Omissions</Badge>}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Your Verification
              </span>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold text-white">
                  {progressPercent}%
                </span>
                <span className="text-[11px] text-muted-foreground">({checkedCount}/{totalItems})</span>
              </div>
            </div>
          </div>

          {/* Progress Indicator */}
          <div className="rounded-xl border border-white/10 bg-surface p-4">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="font-semibold text-white">
                <i className="fa-solid fa-list-check text-emerald-400 mr-2" />
                Borrower Pre-Signing Verification Checklist Progress
              </span>
              <span className="text-muted-foreground font-mono">
                {checkedCount} of {totalItems} verified ({progressPercent}%)
              </span>
            </div>
            <div className="w-full bg-surface-3 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Tab Navigation & Export Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
            {/* Tabs */}
            <div className="flex items-center gap-1 bg-surface p-1 rounded-xl border border-white/10 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("guide")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "guide"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-shield-halved mr-1.5" />
                Pre-Signing Brief
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
                <i className="fa-solid fa-square-check mr-1.5" />
                Interactive Checklist ({totalItems})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("questions")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "questions"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-comment-dots mr-1.5" />
                Lender Questions ({questionItems.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("risks")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "risks"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-triangle-exclamation mr-1.5" />
                Traps & Disclosures ({cautionCount + missingCount + conflictCount})
              </button>
            </div>

            {/* Export Actions */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyBrief}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white hover:border-white/20 transition-colors"
              >
                <i className={`fa-solid ${copiedBrief ? "fa-check text-emerald-400" : "fa-copy"} text-[11px]`} />
                <span>{copiedBrief ? "Copied!" : "Copy Brief"}</span>
              </button>
              <button
                type="button"
                onClick={handleDownloadBrief}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white/80 hover:text-white hover:border-white/20 transition-colors"
              >
                <i className="fa-solid fa-download text-[11px]" />
                <span>Download .MD</span>
              </button>
            </div>
          </div>

          {/* TAB 1: EXECUTIVE PRE-SIGNING BRIEF */}
          {activeTab === "guide" && (
            <Panel
              title="Pre-Signing Verification Brief"
              subtitle="Evidence-grounded contract analysis generated by FinExplain RAG Engine"
            >
              <div className="prose prose-invert max-w-none">
                <FormattedMarkdown content={getGuideMarkdown()} />
              </div>
            </Panel>
          )}

          {/* TAB 2: INTERACTIVE CHECKLIST */}
          {activeTab === "checklist" && (
            <div className="space-y-5">
              {/* Filter Sub-bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-surface p-3 rounded-xl border border-white/10">
                {/* Status Filters */}
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  <span className="text-muted-foreground mr-1">Status:</span>
                  <button
                    type="button"
                    onClick={() => setStatusFilter("ALL")}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      statusFilter === "ALL"
                        ? "bg-white text-black font-semibold"
                        : "bg-surface-2 text-white/70 hover:text-white"
                    }`}
                  >
                    All ({totalItems})
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatusFilter("VERIFIED")}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      statusFilter === "VERIFIED"
                        ? "bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30"
                        : "bg-surface-2 text-white/70 hover:text-white"
                    }`}
                  >
                    ✓ Verified ({verifiedCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatusFilter("CAUTION")}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      statusFilter === "CAUTION"
                        ? "bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30"
                        : "bg-surface-2 text-white/70 hover:text-white"
                    }`}
                  >
                    ⚠ Caution ({cautionCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => setStatusFilter("MISSING")}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      statusFilter === "MISSING"
                        ? "bg-rose-500/20 text-rose-300 font-semibold border border-rose-500/30"
                        : "bg-surface-2 text-white/70 hover:text-white"
                    }`}
                  >
                    ? Omissions ({missingCount})
                  </button>
                </div>

                {/* Category Filter Dropdown */}
                {categories.length > 0 && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Category:</span>
                    <select
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                      className="rounded-lg border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-white focus:outline-none focus:border-white/30"
                    >
                      <option value="ALL">All Categories</option>
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Checklist Items List */}
              <div className="space-y-3.5">
                {filteredChecklist.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-surface p-8 text-center text-muted-foreground text-xs">
                    No checklist items match the selected filter criteria.
                  </div>
                ) : (
                  filteredChecklist.map(({ item, originalIdx }) => {
                    const isChecked = Boolean(checkedItems[originalIdx]);
                    const title = item.title || item.item || `Verification Item #${originalIdx + 1}`;
                    const category = item.category || "General";
                    const priority = item.priority || "MEDIUM";
                    const condition = item.condition;
                    const action = item.action_guidance;
                    const question = item.suggested_question;
                    const evidence = item.evidence;

                    return (
                      <div
                        key={originalIdx}
                        className={`rounded-xl border p-4.5 transition-all ${
                          isChecked
                            ? "border-emerald-500/30 bg-emerald-950/10 opacity-80"
                            : "border-white/10 bg-surface hover:border-white/20"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-3.5 flex-1">
                            {/* Checkbox Button */}
                            <button
                              type="button"
                              onClick={() => toggleCheckItem(originalIdx)}
                              className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border transition-colors ${
                                isChecked
                                  ? "border-emerald-500 bg-emerald-500 text-black"
                                  : "border-white/30 bg-surface-2 hover:border-white"
                              }`}
                              title={isChecked ? "Mark as unverified" : "Mark as verified with lender"}
                            >
                              {isChecked && <i className="fa-solid fa-check text-xs font-bold" />}
                            </button>

                            <div className="space-y-1.5 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={`text-sm font-semibold ${isChecked ? "text-white/70 line-through" : "text-white"}`}>
                                  {title}
                                </span>
                                {item.value && item.value !== "Not Specified" && (
                                  <span className="font-mono text-xs text-white/90 bg-surface-3 px-2 py-0.5 rounded border border-white/10">
                                    {item.value}
                                  </span>
                                )}
                                <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground bg-surface-2 px-2 py-0.5 rounded border border-white/5">
                                  {category}
                                </span>
                                {item.marker === "✓" && (
                                  <Badge tone="success">✓ Verified</Badge>
                                )}
                                {item.marker === "⚠" && (
                                  <Badge tone="warning">⚠ Caution</Badge>
                                )}
                                {item.marker === "?" && (
                                  <Badge tone="danger">? Omission</Badge>
                                )}
                                {item.marker === "🚨" && (
                                  <Badge tone="solid">🚨 Conflict</Badge>
                                )}
                                <SeverityBadge level={priority} />
                              </div>

                              {/* Action Guidance */}
                              {action && (
                                <p className="text-xs text-white/90 leading-relaxed">
                                  <strong className="text-emerald-400">Action:</strong> {action}
                                </p>
                              )}

                              {/* Condition details if any */}
                              {condition && (
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                  <strong className="text-amber-400">Clause Terms:</strong> {condition}
                                </p>
                              )}

                              {/* Evidence Citation */}
                              {evidence && (evidence.document || evidence.page) && (
                                <div className="flex items-center gap-2 pt-1">
                                  <EvidenceBadge status={item.status || "EXPLICIT"} />
                                  <span className="text-[11px] text-muted-foreground font-mono">
                                    Source: {evidence.document || "Document"} {evidence.page ? `• Page ${evidence.page}` : ""}
                                  </span>
                                </div>
                              )}

                              {/* Suggested Question Box */}
                              {question && (
                                <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2.5 text-xs">
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="flex items-start gap-2">
                                      <i className="fa-solid fa-comment-dots text-amber-400 mt-0.5" />
                                      <div>
                                        <span className="font-semibold text-amber-300 block mb-0.5">
                                          Ask Lender in Writing:
                                        </span>
                                        <span className="text-white/90 italic">"{question}"</span>
                                      </div>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => handleCopySingleQuestion(question, originalIdx)}
                                      className="flex-shrink-0 text-[11px] text-amber-400/80 hover:text-amber-300 px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 transition-colors"
                                      title="Copy question text"
                                    >
                                      {copiedQuestionIdx === originalIdx ? (
                                        <span className="text-emerald-400 font-bold">✓ Copied</span>
                                      ) : (
                                        <span>Copy</span>
                                      )}
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB 3: LENDER QUESTIONS SCRIPT */}
          {activeTab === "questions" && (
            <Panel
              title="Official Lender Inquiries & Clarification Script"
              subtitle="Demand explicit written confirmations from your relationship manager on these specific items before contract execution"
            >
              {questionItems.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground text-xs">
                  No specific lender inquiries generated.
                </div>
              ) : (
                <div className="space-y-4">
                  {questionItems.map(({ item, originalIdx }, qIdx) => (
                    <div
                      key={originalIdx}
                      className="rounded-xl border border-white/10 bg-surface-2 p-4.5 transition-all hover:border-white/20"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-surface-3 font-mono text-xs font-bold text-white">
                              {(qIdx + 1).toString().padStart(2, "0")}
                            </span>
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Regarding {item.title || item.category || "Loan Clause"}
                            </h4>
                            <SeverityBadge level={item.priority || "MEDIUM"} />
                          </div>

                          <p className="text-sm font-medium text-white pl-8 leading-relaxed italic">
                            "{item.suggested_question}"
                          </p>

                          {item.action_guidance && (
                            <p className="text-xs text-muted-foreground pl-8">
                              <strong className="text-white/70">Why this matters:</strong> {item.action_guidance}
                            </p>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => handleCopySingleQuestion(item.suggested_question || "", originalIdx)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 text-xs font-medium text-white hover:bg-white/10 transition-colors flex-shrink-0"
                        >
                          <i className={`fa-solid ${copiedQuestionIdx === originalIdx ? "fa-check text-emerald-400" : "fa-copy"} text-[11px]`} />
                          <span>{copiedQuestionIdx === originalIdx ? "Copied!" : "Copy Question"}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          )}

          {/* TAB 4: TRAPS & DISCLOSURE GAPS */}
          {activeTab === "risks" && (
            <div className="space-y-5">
              {/* Caution & Conditional Items */}
              <Panel
                title="Conditional Traps & Cost Escalations"
                subtitle="Clauses where charges or interest rates can escalate based on external triggers or lender discretion"
              >
                {checklist.filter((i) => i.marker === "⚠").length === 0 ? (
                  <p className="text-xs text-muted-foreground">No aggressive conditional clauses detected.</p>
                ) : (
                  <div className="space-y-3">
                    {checklist
                      .filter((i) => i.marker === "⚠")
                      .map((item, idx) => (
                        <div key={idx} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-amber-300">
                              {item.title || item.item}
                            </span>
                            <Badge tone="warning">⚠ Conditional</Badge>
                          </div>
                          {item.condition && (
                            <p className="text-xs text-white/80 leading-relaxed">
                              {item.condition}
                            </p>
                          )}
                          {item.action_guidance && (
                            <p className="text-xs text-muted-foreground">
                              <strong className="text-white/60">Guidance:</strong> {item.action_guidance}
                            </p>
                          )}
                        </div>
                      ))}
                  </div>
                )}
              </Panel>

              {/* Missing Information */}
              <Panel
                title="Material Disclosures & Omissions"
                subtitle="Required statutory terms not explicitly disclosed in the reviewed documentation"
              >
                {checklist.filter((i) => i.marker === "?").length === 0 ? (
                  <p className="text-xs text-muted-foreground">No material disclosures missing.</p>
                ) : (
                  <div className="space-y-3">
                    {checklist
                      .filter((i) => i.marker === "?")
                      .map((item, idx) => (
                        <div key={idx} className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-rose-300">
                              {item.title || item.item}
                            </span>
                            <Badge tone="danger">? Not Disclosed</Badge>
                          </div>
                          {item.condition && (
                            <p className="text-xs text-white/80 leading-relaxed">
                              {item.condition}
                            </p>
                          )}
                          {item.action_guidance && (
                            <p className="text-xs text-muted-foreground">
                              <strong className="text-white/60">Recommended Action:</strong> {item.action_guidance}
                            </p>
                          )}
                        </div>
                      ))}
                  </div>
                )}
              </Panel>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
