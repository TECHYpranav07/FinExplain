import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type LoanReviewResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  PageHeader,
  Panel,
  Badge,
  SeverityBadge,
  EmptyState,
  ErrorState,
} from "@/components/finex/primitives";

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
                <span>Auditing Agreement...</span>
              </>
            ) : (
              <>
                <i className="fa-solid fa-shield-halved text-xs" />
                <span>Run Proactive Review</span>
              </>
            )}
          </button>
        }
      />

      {/* Target Products */}
      <Panel title="Select Loan Products to Audit" subtitle="Pick one or more products to cross-examine">
        <ProductPicker
          selected={selectedProducts}
          onChange={setSelectedProducts}
          multiple={true}
        />
      </Panel>

      {reviewMutation.isError && (
        <ErrorState
          message={(reviewMutation.error as any)?.message || "Failed to execute proactive review."}
          onRetry={handleRunReview}
        />
      )}

      {!reviewResult && !reviewMutation.isPending && (
        <EmptyState
          icon="fa-solid fa-shield-halved"
          title="No review generated yet"
          description="Select a loan product above and click 'Run Proactive Review' to scan for hidden fees, penalty structures, and legal risks."
          action={
            <button
              type="button"
              disabled={selectedProducts.length === 0}
              onClick={handleRunReview}
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40"
            >
              Analyze Selected Products
            </button>
          }
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
            <div className="text-sm text-white whitespace-pre-line leading-relaxed">
              {reviewResult.review_text || JSON.stringify(reviewResult.review, null, 2)}
            </div>
          </Panel>

          {/* Cost Drivers */}
          {reviewResult.cost_drivers && reviewResult.cost_drivers.length > 0 && (
            <Panel
              title="Identified Cost Drivers & Fee Structures"
              subtitle="All direct and indirect expenses found in document"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {reviewResult.cost_drivers.map((cd: any, idx: number) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-white/10 bg-surface-2 p-4 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-white">
                          {cd.name || cd.fee_name || `Cost Factor #${idx + 1}`}
                        </span>
                        <Badge tone="warning">{cd.type || "Fee"}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {cd.description || cd.details || JSON.stringify(cd)}
                      </p>
                    </div>
                    {cd.amount && (
                      <div className="mt-3 pt-2 border-t border-white/5 text-right font-mono text-xs text-white">
                        {cd.amount}
                      </div>
                    )}
                  </div>
                ))}
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
                {reviewResult.checklist.map((item: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 rounded-lg border border-white/10 bg-surface-2 p-3.5"
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 text-[10px] font-bold text-white mt-0.5">
                      {idx + 1}
                    </span>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-white">
                        {typeof item === "string" ? item : item.title || item.item || JSON.stringify(item)}
                      </p>
                      {item.note && (
                        <p className="mt-1 text-[11px] text-muted-foreground">{item.note}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}
    </div>
  );
}
