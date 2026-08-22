import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, type BeforeConfirmationResponse } from "@/lib/api";
import { ProductPicker } from "@/components/finex/ProductSelect";
import {
  PageHeader,
  Panel,
  Badge,
  SeverityBadge,
  EmptyState,
  ErrorState,
} from "@/components/finex/primitives";

export function BeforeConfirmationPage() {
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);
  const [result, setResult] = useState<BeforeConfirmationResponse | null>(null);

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (selectedProducts.length === 0) {
        throw new Error("Select at least one loan product.");
      }
      return api.beforeConfirmation({ product_ids: selectedProducts });
    },
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const handleGenerate = () => {
    confirmMutation.mutate();
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Decision Support"
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

      {/* Target Products */}
      <Panel title="Select Loan Products" subtitle="Pick product(s) to generate pre-confirmation checklist for">
        <ProductPicker
          selected={selectedProducts}
          onChange={setSelectedProducts}
          multiple={true}
        />
      </Panel>

      {confirmMutation.isError && (
        <ErrorState
          message={(confirmMutation.error as any)?.message || "Failed to generate checklist."}
          onRetry={handleGenerate}
        />
      )}

      {!result && !confirmMutation.isPending && (
        <EmptyState
          icon="fa-regular fa-circle-check"
          title="No pre-confirmation checklist generated"
          description="Select loan products above to generate a prioritized confirmation checklist with recommended lender inquiries."
          action={
            <button
              type="button"
              disabled={selectedProducts.length === 0}
              onClick={handleGenerate}
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40"
            >
              Analyze Products
            </button>
          }
        />
      )}

      {confirmMutation.isPending && (
        <div className="py-16 flex flex-col items-center justify-center gap-3">
          <i className="fa-solid fa-spinner fa-spin text-3xl text-white" />
          <p className="text-sm font-semibold text-white">Synthesizing pre-confirmation verification checklist...</p>
          <p className="text-xs text-muted-foreground">Checking prepayment caps, interest resets, and default penalties</p>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Executive Checklist Summary */}
          {result.checklist_text && (
            <Panel title="Executive Guidance & Strategic Considerations">
              <div className="text-sm text-white whitespace-pre-line leading-relaxed">
                {result.checklist_text}
              </div>
            </Panel>
          )}

          {/* Itemized Action Checklist */}
          {result.checklist && result.checklist.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Prioritized Action Items ({result.checklist.length})
              </h3>

              {result.checklist.map((item: any, idx: number) => {
                const title = typeof item === "string" ? item : item.title || item.item || item.text || `Item #${idx + 1}`;
                const risk = typeof item === "object" ? item.risk || item.severity || "MEDIUM" : "MEDIUM";
                const reason = typeof item === "object" ? item.reason || item.description : null;
                const question = typeof item === "object" ? item.suggested_question || item.question : null;

                return (
                  <div
                    key={idx}
                    className="rounded-xl border border-white/10 bg-surface p-5 transition-all hover:border-white/20"
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex items-center gap-3">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-3 font-mono text-xs font-bold text-white">
                          {(idx + 1).toString().padStart(2, "0")}
                        </span>
                        <h4 className="text-sm font-semibold text-white">{title}</h4>
                      </div>
                      <SeverityBadge level={risk} />
                    </div>

                    {reason && (
                      <p className="mt-2 text-xs text-muted-foreground pl-10 leading-relaxed">
                        <strong className="text-white/80">Audit Rationale:</strong> {reason}
                      </p>
                    )}

                    {question && (
                      <div className="mt-3 ml-10 rounded-lg border border-warning/20 bg-warning/5 p-3 text-xs text-white">
                        <div className="flex items-start gap-2">
                          <i className="fa-solid fa-comment-dots text-warning mt-0.5" />
                          <div>
                            <span className="font-semibold text-warning block mb-0.5">
                              Recommended Question for Lender:
                            </span>
                            <span className="italic">"{question}"</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
