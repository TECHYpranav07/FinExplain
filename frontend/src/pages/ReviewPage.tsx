import React, { useState } from "react";
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

  const reviewMutation = useMutation({
    mutationFn: async () => {
      if (selectedProducts.length === 0) {
        throw new Error("Please select at least one product to perform a proactive review.");
      }
      return api.review({ product_ids: selectedProducts });
    },
    onSuccess: (data) => {
      setReviewResult(data);
    },
  });

  const handleRunReview = () => {
    reviewMutation.mutate();
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
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
        <ErrorState
          message={
            reviewMutation.error instanceof Error
              ? reviewMutation.error.message
              : "Unable to complete loan review."
          }
          onRetry={handleRunReview}
        />
      )}

      {!reviewResult && !reviewMutation.isPending && !reviewMutation.isError && (
        <EmptyState
          title="No Active Audit Results"
          description="Select a loan product above and click 'Run Proactive Review' to scan for hidden fees, penalty structures, and legal risks."
          icon="fa-shield-halved"
        />
      )}

      {reviewMutation.isPending && (
        <div className="py-16 flex flex-col items-center justify-center gap-3">
          <i className="fa-solid fa-spinner fa-spin text-3xl text-white" />
          <p className="text-sm font-semibold text-white">Scanning document clauses for financial hazards...</p>
          <p className="text-xs text-muted-foreground">Evaluating cost drivers, lock-in terms, and penalty ceilings</p>
        </div>
      )}

      {reviewResult && (
        <div className="space-y-6">
          {/* Executive Overview */}
          <Panel
            title="Proactive Audit Executive Summary"
            subtitle="Synthesized legal and financial risk profile"
          >
            <FormattedMarkdown
              content={
                typeof reviewResult.review === "string"
                  ? reviewResult.review
                  : reviewResult.review_text || ""
              }
            />
          </Panel>

          {/* Cost Drivers */}
          {reviewResult.cost_drivers && reviewResult.cost_drivers.length > 0 && (
            <Panel
              title="Identified Cost Drivers & Fee Structures"
              subtitle="All direct and indirect expenses found in document"
            >
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
                      : cd.amount || "Refer to condition";
                  const conditionText = cd.condition || cd.description || cd.details || "Applicable under document clauses.";
                  const status = cd.status || "CONDITIONAL";

                  return (
                    <div
                      key={idx}
                      className="rounded-lg border border-white/10 bg-surface-2 p-4 flex flex-col justify-between"
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
                      <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between">
                        {cd.page ? (
                          <span className="text-[10px] text-white/50">
                            Page {cd.page} {cd.source_document ? `(${cd.source_document})` : ""}
                          </span>
                        ) : (
                          <span className="text-[10px] text-white/40">Source Verified</span>
                        )}
                        <span className="font-mono text-xs font-semibold text-white">
                          {formattedValue}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}

          {/* Action Checklist */}
          {reviewResult.checklist && reviewResult.checklist.length > 0 && (
            <Panel
              title="Review Action Checklist"
              subtitle="Critical items verified or requiring human sign-off"
            >
              <div className="space-y-3">
                {reviewResult.checklist.map((rawItem: any, idx: number) => {
                  let itemText = "";
                  let itemNote = "";
                  if (typeof rawItem === "string") {
                    itemText = rawItem;
                  } else if (typeof rawItem === "object" && rawItem !== null) {
                    itemText = rawItem.title || rawItem.item || rawItem.action || rawItem.question || Object.values(rawItem)[0] || "";
                    itemNote = rawItem.note || rawItem.reason || rawItem.details || "";
                  }

                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-3 rounded-lg border border-white/10 bg-surface-2 p-3.5"
                    >
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 text-[10px] font-bold text-white mt-0.5">
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-white leading-relaxed">
                          {itemText}
                        </p>
                        {itemNote && (
                          <p className="mt-1 text-[11px] text-muted-foreground">{itemNote}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}
