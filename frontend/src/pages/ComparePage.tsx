import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, type Product, type LoanCompareResponse, type ComparisonFieldItem } from "@/lib/api";
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

export function ComparePage() {
  const { data: products = [], isLoading: productsLoading } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: api.listProducts,
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<"report" | "matrix" | "scenario" | "risks">("report");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [compareResult, setCompareResult] = useState<LoanCompareResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Scenario Simulator State
  const [scenarioPrincipal, setScenarioPrincipal] = useState<number>(500000);
  const [scenarioTenure, setScenarioTenure] = useState<number>(12);
  const [scenarioPrepayMonth, setScenarioPrepayMonth] = useState<number>(6);

  const compareMutation = useMutation({
    mutationFn: async () => {
      if (selectedIds.length < 2) {
        throw new Error("Please select at least 2 loan products to perform a side-by-side comparative analysis.");
      }
      return api.compare({
        product_ids: selectedIds,
        scenario: {
          loan_amount: scenarioPrincipal,
          tenure_months: scenarioTenure,
          prepayment_month: scenarioPrepayMonth,
        },
      });
    },
    onSuccess: (data) => {
      setCompareResult(data);
      setActiveTab("report");
    },
  });

  const handleRunComparison = () => {
    compareMutation.mutate();
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === products.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(products.map((p) => p.id));
    }
  };

  const getReportMarkdown = (): string => {
    if (!compareResult) return "";
    return compareResult.comparison_text || "Comparative benchmark analysis completed.";
  };

  const handleCopyReport = async () => {
    const text = getReportMarkdown();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
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
    a.download = `FinExplain_Comparative_Benchmark_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const selectedProducts = products.filter((p) => selectedIds.includes(p.id));
  const comparedProducts = compareResult?.products || selectedProducts;
  const fieldComparisons = compareResult?.field_comparisons || [];

  // Helper to categorize fields
  const categorizeField = (fieldName: string): string => {
    const f = fieldName.toLowerCase();
    if (f.includes("interest") || f.includes("rate") || f.includes("apr")) return "Interest & Rates";
    if (f.includes("fee") || f.includes("processing") || f.includes("documentation") || f.includes("charge")) return "Fees & Deductions";
    if (f.includes("prepay") || f.includes("foreclosure") || f.includes("early") || f.includes("waiver")) return "Prepayment & Exit";
    if (f.includes("late") || f.includes("penalty") || f.includes("default") || f.includes("bounce")) return "Penalties & Default";
    return "Tenure & Terms";
  };

  // Unique categories
  const categories = Array.from(
    new Set(fieldComparisons.map((fc) => categorizeField(fc.field)))
  );

  // Filtered fields
  const filteredFields = fieldComparisons.filter((fc) => {
    if (categoryFilter !== "ALL" && categorizeField(fc.field) !== categoryFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Comparative Lending Intelligence"
        title="Product & Loan Comparison"
        description="Benchmark contractual rates, upfront deductions, prepayment penalties, and total borrowing liability side-by-side across financial institutions."
        action={
          <button
            type="button"
            onClick={handleRunComparison}
            disabled={compareMutation.isPending || selectedIds.length < 2}
            className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40 transition-colors shadow-sm"
          >
            {compareMutation.isPending ? (
              <>
                <i className="fa-solid fa-spinner fa-spin text-xs" />
                <span>Benchmarking Contracts...</span>
              </>
            ) : (
              <>
                <i className="fa-solid fa-code-compare text-xs" />
                <span>Run Comparative Benchmark ({selectedIds.length})</span>
              </>
            )}
          </button>
        }
      />

      {/* Multi-Product Selection Panel */}
      <Panel
        title="Select Products to Compare"
        subtitle="Choose 2 or more credit facilities to generate side-by-side benchmark matrix"
        action={
          products.length > 0 && (
            <button
              type="button"
              onClick={handleSelectAll}
              className="text-xs text-muted-foreground hover:text-white transition-colors"
            >
              {selectedIds.length === products.length ? "Deselect All" : "Select All Products"}
            </button>
          )
        }
      >
        {productsLoading ? (
          <div className="py-6 flex justify-center">
            <i className="fa-solid fa-spinner fa-spin text-muted-foreground text-xl" />
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            title="No registered products found"
            description="Upload loan documents in Document Management to create product catalogs for comparison."
          />
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {products.map((p) => {
                const active = selectedIds.includes(p.id);
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => toggleSelect(p.id)}
                    className={`rounded-xl border p-4 text-left transition-all flex items-start justify-between gap-3 ${
                      active
                        ? "border-white bg-white/10 shadow-sm"
                        : "border-white/10 bg-surface-2 hover:border-white/25"
                    }`}
                  >
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{p.name}</span>
                        {active && (
                          <Badge tone="success">Selected</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{p.issuer}</p>
                      {p.effective_date && (
                        <p className="text-[11px] text-muted-foreground/70 font-mono">
                          Schedule: {p.effective_date}
                        </p>
                      )}
                    </div>
                    <div
                      className={`h-5 w-5 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors ${
                        active
                          ? "border-white bg-white text-black font-bold"
                          : "border-white/20 bg-surface-3"
                      }`}
                    >
                      {active && <i className="fa-solid fa-check text-xs" />}
                    </div>
                  </button>
                );
              })}
            </div>

            {selectedIds.length < 2 && (
              <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-xs text-amber-300 flex items-center gap-2">
                <i className="fa-solid fa-circle-info text-amber-400" />
                <span>Please select at least <strong>2 products</strong> above to activate comparative benchmarking.</span>
              </div>
            )}
          </div>
        )}
      </Panel>

      {compareMutation.isError && (
        <ErrorState
          message={
            compareMutation.error instanceof Error
              ? compareMutation.error.message
              : "Failed to generate comparative benchmark."
          }
          onRetry={handleRunComparison}
        />
      )}

      {!compareResult && !compareMutation.isPending && (
        <EmptyState
          icon="fa-solid fa-code-compare"
          title="Ready for Comparative Evaluation"
          description="Select 2 or more products above and click 'Run Comparative Benchmark' to extract side-by-side interest rates, fees, lock-ins, and cost simulations."
        />
      )}

      {compareMutation.isPending && (
        <div className="py-20 flex flex-col items-center justify-center gap-4 text-center">
          <div className="relative flex items-center justify-center">
            <div className="h-16 w-16 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            <i className="fa-solid fa-scale-balanced absolute text-lg text-white" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-white">Cross-referencing contractual terms across loan products...</p>
            <p className="text-xs text-muted-foreground">Evaluating interest spreads, prepayment caps, and total borrowing liability</p>
          </div>
        </div>
      )}

      {compareResult && (
        <div className="space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Compared Products
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {comparedProducts.length} Facilities
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Matched Parameters
              </span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {fieldComparisons.length} Terms
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Product A Facility
              </span>
              <span className="text-sm font-bold text-emerald-400 mt-1.5 block truncate">
                {comparedProducts[0]?.name || "Product A"}
              </span>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-2 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
                Product B Facility
              </span>
              <span className="text-sm font-bold text-blue-400 mt-1.5 block truncate">
                {comparedProducts[1]?.name || "Product B"}
              </span>
            </div>
          </div>

          {/* Tab Selector & Export Bar */}
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
                Benchmark Brief
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("matrix")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "matrix"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-table-columns mr-1.5" />
                Side-by-Side Matrix ({fieldComparisons.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("scenario")}
                className={`px-3.5 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === "scenario"
                    ? "bg-surface-3 text-white shadow-sm"
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <i className="fa-solid fa-calculator mr-1.5" />
                Scenario Simulator
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
                Contractual Differences
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

          {/* TAB 1: EXECUTIVE BENCHMARK BRIEF */}
          {activeTab === "report" && (
            <Panel
              title="Comparative Loan Benchmark Analysis"
              subtitle="Evidence-backed multi-product evaluation synthesized by FinExplain RAG Engine"
            >
              <div className="prose prose-invert max-w-none">
                <FormattedMarkdown content={getReportMarkdown()} />
              </div>
            </Panel>
          )}

          {/* TAB 2: SIDE-BY-SIDE MATRIX */}
          {activeTab === "matrix" && (
            <div className="space-y-4">
              {/* Category Filter Pills */}
              {categories.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 bg-surface p-2.5 rounded-xl border border-white/10 text-xs">
                  <span className="text-muted-foreground mr-1">Filter by Category:</span>
                  <button
                    type="button"
                    onClick={() => setCategoryFilter("ALL")}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      categoryFilter === "ALL"
                        ? "bg-white text-black font-semibold"
                        : "bg-surface-2 text-white/70 hover:text-white"
                    }`}
                  >
                    All ({fieldComparisons.length})
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategoryFilter(cat)}
                      className={`px-3 py-1 rounded-lg transition-colors ${
                        categoryFilter === cat
                          ? "bg-white text-black font-semibold"
                          : "bg-surface-2 text-white/70 hover:text-white"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              )}

              {/* Comparison Table */}
              <Panel
                title="Structured Contract Parameter Comparison"
                subtitle="Field-by-field verification derived from operative loan documentation"
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-white/10 text-muted-foreground uppercase tracking-wider text-[10px]">
                        <th className="pb-3 pr-4 font-semibold w-1/4">Financial Parameter</th>
                        <th className="pb-3 pr-4 font-semibold text-emerald-400 w-1/3">
                          {comparedProducts[0]?.name || "Product A"}
                          <span className="block font-normal text-muted-foreground text-[10px]">
                            {comparedProducts[0]?.issuer}
                          </span>
                        </th>
                        <th className="pb-3 pr-4 font-semibold text-blue-400 w-1/3">
                          {comparedProducts[1]?.name || "Product B"}
                          <span className="block font-normal text-muted-foreground text-[10px]">
                            {comparedProducts[1]?.issuer}
                          </span>
                        </th>
                        <th className="pb-3 pr-4 font-semibold text-right">Advantage / Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {filteredFields.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-8 text-center text-muted-foreground">
                            No parameters match the selected category filter.
                          </td>
                        </tr>
                      ) : (
                        filteredFields.map((fc, idx) => {
                          const fieldName = (fc.field || "Term").replace(/_/g, " ");
                          const valA = fc.product_a ? `${fc.product_a.value ?? "Mentioned"} ${fc.product_a.unit ?? ""}`.trim() : null;
                          const valB = fc.product_b ? `${fc.product_b.value ?? "Mentioned"} ${fc.product_b.unit ?? ""}`.trim() : null;
                          const condA = fc.product_a?.condition;
                          const condB = fc.product_b?.condition;
                          const winner = fc.winner;

                          return (
                            <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                              <td className="py-3.5 pr-4 font-medium text-white">
                                <span className="capitalize">{fieldName}</span>
                                <span className="block text-[10px] text-muted-foreground uppercase tracking-wider mt-0.5">
                                  {categorizeField(fc.field)}
                                </span>
                              </td>
                              <td className="py-3.5 pr-4">
                                {valA ? (
                                  <div className="space-y-1">
                                    <span className="font-mono font-semibold text-white bg-emerald-950/30 border border-emerald-500/20 px-2 py-0.5 rounded inline-block">
                                      {valA}
                                    </span>
                                    {condA && (
                                      <p className="text-[11px] text-muted-foreground leading-tight">
                                        <i className="fa-solid fa-triangle-exclamation text-amber-400 mr-1" />
                                        {condA}
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-muted-foreground italic">Not specified</span>
                                )}
                              </td>
                              <td className="py-3.5 pr-4">
                                {valB ? (
                                  <div className="space-y-1">
                                    <span className="font-mono font-semibold text-white bg-blue-950/30 border border-blue-500/20 px-2 py-0.5 rounded inline-block">
                                      {valB}
                                    </span>
                                    {condB && (
                                      <p className="text-[11px] text-muted-foreground leading-tight">
                                        <i className="fa-solid fa-triangle-exclamation text-amber-400 mr-1" />
                                        {condB}
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <span className="text-muted-foreground italic">Not specified</span>
                                )}
                              </td>
                              <td className="py-3.5 pr-4 text-right">
                                {(winner === "A" || winner === "product_a") && (
                                  <Badge tone="success">
                                    ✓ {comparedProducts[0]?.name || "Product A"} Better
                                  </Badge>
                                )}
                                {(winner === "B" || winner === "product_b") && (
                                  <Badge tone="info">
                                    ✓ {comparedProducts[1]?.name || "Product B"} Better
                                  </Badge>
                                )}
                                {(winner === "TIE" || winner === "equal") && (
                                  <Badge tone="neutral">Identical</Badge>
                                )}
                                {(!winner || winner === "Comparable" || winner === "non_numeric") && (
                                  <Badge tone="neutral">Comparable</Badge>
                                )}
                              </td>

                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 3: SCENARIO SIMULATOR */}
          {activeTab === "scenario" && (
            <div className="space-y-6">
              <Panel
                title="Scenario Simulation Parameters"
                subtitle="Adjust loan principal and planned repayment horizon to simulate true borrowing expense"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-white">
                      Target Principal Amount (₹)
                    </label>
                    <input
                      type="number"
                      value={scenarioPrincipal}
                      onChange={(e) => setScenarioPrincipal(Number(e.target.value))}
                      className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30"
                      min={10000}
                      step={10000}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-white">
                      Planned Repayment Horizon (Months)
                    </label>
                    <input
                      type="number"
                      value={scenarioTenure}
                      onChange={(e) => setScenarioTenure(Number(e.target.value))}
                      className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30"
                      min={1}
                      max={360}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-white">
                      Early Prepayment Month (Optional)
                    </label>
                    <input
                      type="number"
                      value={scenarioPrepayMonth}
                      onChange={(e) => setScenarioPrepayMonth(Number(e.target.value))}
                      className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30"
                      min={1}
                      max={scenarioTenure}
                    />
                  </div>
                </div>

                <div className="mt-4 flex justify-end">
                  <button
                    type="button"
                    onClick={handleRunComparison}
                    disabled={compareMutation.isPending}
                    className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90 transition-colors"
                  >
                    <i className="fa-solid fa-arrows-rotate text-xs" />
                    <span>Recalculate Scenario Matrix</span>
                  </button>
                </div>
              </Panel>

              {/* Simulation Result Card */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {comparedProducts.slice(0, 2).map((p, idx) => (
                  <div
                    key={p.id}
                    className={`rounded-xl border p-5 space-y-3 ${
                      idx === 0 ? "border-emerald-500/30 bg-emerald-950/10" : "border-blue-500/30 bg-blue-950/10"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold text-white">{p.name}</h4>
                      <Badge tone={idx === 0 ? "success" : "info"}>Option #{idx + 1}</Badge>
                    </div>

                    <div className="space-y-2 text-xs text-white/90">
                      <div className="flex justify-between py-1 border-b border-white/5">
                        <span className="text-muted-foreground">Lending Entity:</span>
                        <span className="font-semibold">{p.issuer}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-white/5">
                        <span className="text-muted-foreground">Scenario Principal:</span>
                        <span className="font-mono font-bold">₹{scenarioPrincipal.toLocaleString("en-IN")}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-white/5">
                        <span className="text-muted-foreground">Repayment Window:</span>
                        <span className="font-mono">{scenarioTenure} Months</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: CONTRACTUAL DIFFERENCES & CAVEATS */}
          {activeTab === "risks" && (
            <div className="space-y-4">
              <Panel
                title="Critical Contractual Discrepancies & Disclosures"
                subtitle="Key differences in borrower covenants, default charges, and legal precedence"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {comparedProducts.slice(0, 2).map((p, idx) => (
                    <div key={p.id} className="rounded-xl border border-white/10 bg-surface-2 p-5 space-y-3">
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        <i className={`fa-solid fa-shield-halved ${idx === 0 ? "text-emerald-400" : "text-blue-400"}`} />
                        {p.name} ({p.issuer})
                      </h4>
                      <div className="text-xs text-muted-foreground space-y-2 leading-relaxed">
                        <p>
                          Operative credit agreement verified by FinExplain's compliance parser. Refer to the side-by-side benchmark matrix and generated brief for specific penalty triggers and prepayment clauses.
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
