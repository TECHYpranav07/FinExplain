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
import { downloadPdf, type PdfSection } from "@/lib/pdfExporter";

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
      // Keep current active tab if user is already exploring scenario simulator or risks
      setActiveTab((prev) => (prev === "scenario" || prev === "matrix" || prev === "risks" ? prev : "report"));
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
    const rawMd = getReportMarkdown();
    if (!rawMd && !compareResult) return;

    const sections: PdfSection[] = [];

    // 1. Executive Tradeoff Summary
    const summaryText = compareResult?.summary?.comparison_summary || compareResult?.comparison_text;
    if (summaryText) {
      sections.push({
        title: "1. Executive Trade-off & Benchmark Analysis",
        content: summaryText.slice(0, 500),
      });
    }

    // 2. Side-by-Side Matrix Table
    const fields = compareResult?.field_comparisons || [];
    if (fields.length > 0) {
      const prodA = comparedProducts[0]?.name || "Product A";
      const prodB = comparedProducts[1]?.name || "Product B";
      const headers = ["Parameter", prodA.slice(0, 20), prodB.slice(0, 20)];
      const rows = fields.slice(0, 15).map((item) => [
        String(item.field || "Term"),
        String(item.product_a?.value || item.values?.[comparedProducts[0]?.id]?.value || "N/A"),
        String(item.product_b?.value || item.values?.[comparedProducts[1]?.id]?.value || "N/A"),
      ]);

      sections.push({
        title: "2. Side-by-Side Financial Comparison Matrix",
        table: {
          headers,
          rows,
        },
      });
    }

    downloadPdf({
      filename: `FinExplain_Comparative_Benchmark_${Date.now()}.pdf`,
      title: "FinExplain Side-by-Side Loan Comparison",
      subtitle:
        "Multi-Product Financial Terms Benchmark & Amortization Matrix",
      metadata: {
        "Compared Facilities":
          comparedProducts.map((p) => p.name).join(" vs ") || "Loan Products",
        "Comparison Date": new Date().toLocaleDateString("en-IN"),
      },
      sections,
    });
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
                <i className="fa-solid fa-file-pdf text-[11px] text-rose-400" />
                <span>Download PDF</span>
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
          {activeTab === "scenario" && (() => {
            // Helper to extract rates and compute exact financial amortization for each product
            const getSimulatedProductStats = (productIdx: number) => {
              let rate = productIdx === 0 ? 10.5 : 12.0;
              let processingFee = productIdx === 0 ? 8000 : 1500;
              let prepayPenaltyPct = productIdx === 0 ? 2.0 : 0.0;

              for (const fc of fieldComparisons) {
                const fLower = (fc.field || "").toLowerCase();
                const productData = productIdx === 0 ? fc.product_a : fc.product_b;
                if (!productData?.value) continue;

                const numVal = parseFloat(String(productData.value).replace(/[^0-9.]/g, ""));
                if (!isNaN(numVal)) {
                  if (fLower.includes("interest") || fLower.includes("rate") || fLower.includes("roi")) {
                    if (numVal > 0 && numVal < 40) rate = numVal;
                  } else if (fLower.includes("processing") || fLower.includes("fee")) {
                    processingFee = numVal < 100 ? (numVal / 100) * scenarioPrincipal : numVal;
                  } else if (fLower.includes("prepay") || fLower.includes("foreclosure")) {
                    prepayPenaltyPct = numVal;
                  }
                }
              }

              // Monthly reducing amortization
              const monthlyRate = rate / (12 * 100);
              const n = Math.max(1, scenarioTenure);
              const P = Math.max(1000, scenarioPrincipal);
              const emi = Math.round((P * monthlyRate * Math.pow(1 + monthlyRate, n)) / (Math.pow(1 + monthlyRate, n) - 1));
              const totalRepayment = emi * n;
              const totalInterest = totalRepayment - P;
              const netDisbursal = Math.max(0, P - processingFee);
              const totalBorrowingCost = totalInterest + processingFee;

              return {
                rate,
                processingFee: Math.round(processingFee),
                emi,
                totalInterest,
                totalRepayment,
                netDisbursal,
                totalBorrowingCost,
                prepayPenaltyPct,
              };
            };

            const statsA = getSimulatedProductStats(0);
            const statsB = comparedProducts.length > 1 ? getSimulatedProductStats(1) : null;
            const costDiff = statsB ? Math.abs(statsA.totalBorrowingCost - statsB.totalBorrowingCost) : 0;
            const isAWinner = statsB ? statsA.totalBorrowingCost <= statsB.totalBorrowingCost : true;
            const winnerName = isAWinner ? (comparedProducts[0]?.name || "Option 1") : (comparedProducts[1]?.name || "Option 2");

            return (
              <div className="space-y-6">
                {/* Simulator Inputs Panel */}
                <Panel
                  title="Scenario Simulation Parameters"
                  subtitle="Adjust principal amount, planned repayment window, and exit timeline to simulate total borrowing liability"
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
                        className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30 font-mono"
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
                        className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30 font-mono"
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
                        className="w-full rounded-lg border border-white/10 bg-surface-2 p-2.5 text-xs text-white focus:outline-none focus:border-white/30 font-mono"
                        min={1}
                        max={scenarioTenure}
                      />
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
                    <span className="text-xs text-muted-foreground">
                      * Calculates standard monthly reducing amortization using extracted contract rates and upfront fees.
                    </span>
                    <button
                      type="button"
                      onClick={handleRunComparison}
                      disabled={compareMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90 transition-colors shadow-sm"
                    >
                      <i className={`fa-solid ${compareMutation.isPending ? "fa-spinner fa-spin" : "fa-arrows-rotate"} text-xs`} />
                      <span>{compareMutation.isPending ? "Calculating..." : "Recalculate Scenario Matrix"}</span>
                    </button>
                  </div>
                </Panel>

                {/* Scenario Decision Recommendation Banner */}
                {statsB && (
                  <div className={`rounded-2xl border p-4.5 sm:p-5 ${
                    isAWinner ? "border-emerald-500/30 bg-emerald-500/10" : "border-blue-500/30 bg-blue-500/10"
                  }`}>
                    <div className="flex items-start gap-3.5">
                      <i className={`fa-solid fa-trophy text-lg mt-0.5 ${isAWinner ? "text-emerald-400" : "text-blue-400"}`} />
                      <div className="space-y-1 flex-1">
                        <h4 className="text-sm font-bold text-white">
                          Scenario Verdict: {winnerName} saves you ₹{costDiff.toLocaleString("en-IN")}
                        </h4>
                        <p className="text-xs text-white/85 leading-relaxed">
                          For a borrowing principal of <strong className="text-white">₹{scenarioPrincipal.toLocaleString("en-IN")}</strong> over <strong className="text-white">{scenarioTenure} months</strong>, {winnerName} results in a lower overall financial cash outflow (interest + upfront fee deductions) compared to the competing option.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Side-by-Side Financial Simulation Result Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {comparedProducts.slice(0, 2).map((p, idx) => {
                    const stats = idx === 0 ? statsA : statsB;
                    if (!stats) return null;
                    const isOptionWinner = statsB ? (idx === 0 ? isAWinner : !isAWinner) : true;

                    return (
                      <div
                        key={p.id}
                        className={`rounded-2xl border p-5 space-y-4 transition-all shadow-sm ${
                          isOptionWinner
                            ? "border-emerald-500/30 bg-surface-2 ring-1 ring-emerald-500/20"
                            : "border-white/10 bg-surface"
                        }`}
                      >
                        {/* Option Header */}
                        <div className="flex items-center justify-between border-b border-white/10 pb-3">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
                              Option #{idx + 1}
                            </span>
                            <h4 className="text-sm font-bold text-white mt-0.5">
                              {p.name}
                            </h4>
                            <span className="text-xs text-muted-foreground">{p.issuer}</span>
                          </div>
                          {isOptionWinner ? (
                            <Badge tone="success">✓ Recommended</Badge>
                          ) : (
                            <Badge tone="neutral">Alternative</Badge>
                          )}
                        </div>

                        {/* Financial Metrics Table */}
                        <div className="space-y-2.5 text-xs">
                          <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                            <span className="text-muted-foreground">Contractual Interest Rate:</span>
                            <span className="font-mono font-bold text-white bg-white/5 px-2 py-0.5 rounded border border-white/10">
                              {stats.rate}% p.a.
                            </span>
                          </div>

                          <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                            <span className="text-muted-foreground">Monthly EMI Payment:</span>
                            <span className="font-mono font-bold text-lg text-emerald-400">
                              ₹{stats.emi.toLocaleString("en-IN")} <span className="text-[10px] text-muted-foreground font-normal">/ mo</span>
                            </span>
                          </div>

                          <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                            <span className="text-muted-foreground">Total Interest Payable ({scenarioTenure}m):</span>
                            <span className="font-mono font-semibold text-white">
                              ₹{stats.totalInterest.toLocaleString("en-IN")}
                            </span>
                          </div>

                          <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                            <span className="text-muted-foreground">Upfront Processing Fee:</span>
                            <span className="font-mono font-semibold text-white/90">
                              ₹{stats.processingFee.toLocaleString("en-IN")}
                            </span>
                          </div>

                          <div className="flex justify-between items-center py-1.5 border-b border-white/5">
                            <span className="text-muted-foreground">Net In-Pocket Disbursal:</span>
                            <span className="font-mono font-semibold text-white/90">
                              ₹{stats.netDisbursal.toLocaleString("en-IN")}
                            </span>
                          </div>

                          <div className="flex justify-between items-center pt-2 text-sm font-bold border-t border-white/10">
                            <span className="text-white">Total Outflow & Liability:</span>
                            <span className="font-mono text-primary-light">
                              ₹{(stats.totalRepayment + stats.processingFee).toLocaleString("en-IN")}
                            </span>
                          </div>
                        </div>

                        {/* Visual Cost Distribution Bar */}
                        <div className="space-y-1.5 pt-2 border-t border-white/10">
                          <div className="flex justify-between text-[10px] text-muted-foreground uppercase font-semibold">
                            <span>Principal: ₹{scenarioPrincipal.toLocaleString("en-IN")}</span>
                            <span>Interest: ₹{stats.totalInterest.toLocaleString("en-IN")}</span>
                          </div>
                          <div className="w-full bg-surface-3 rounded-full h-2 flex overflow-hidden">
                            <div
                              className="bg-primary h-2"
                              style={{ width: `${(scenarioPrincipal / (stats.totalRepayment + stats.processingFee)) * 100}%` }}
                              title="Principal Portion"
                            />
                            <div
                              className="bg-amber-400 h-2"
                              style={{ width: `${(stats.totalInterest / (stats.totalRepayment + stats.processingFee)) * 100}%` }}
                              title="Interest Portion"
                            />
                            <div
                              className="bg-rose-400 h-2"
                              style={{ width: `${(stats.processingFee / (stats.totalRepayment + stats.processingFee)) * 100}%` }}
                              title="Fees Portion"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {/* TAB 4: CONTRACTUAL DIFFERENCES & CAVEATS */}
          {activeTab === "risks" && (() => {
            // Find fields with specific conditions, discrepancies, or disclosure gaps
            const conditionalDiscrepancies = fieldComparisons.filter(
              (fc) => (fc.product_a?.condition || fc.product_b?.condition) ||
                      (fc.product_a && !fc.product_b) ||
                      (!fc.product_a && fc.product_b) ||
                      (fc.winner && fc.winner !== "equal" && fc.winner !== "TIE")
            );

            // Separate into Prepayment, Penalties, and Fees
            const exitDiscrepancies = fieldComparisons.filter(
              (fc) => (fc.field || "").toLowerCase().includes("prepay") || (fc.field || "").toLowerCase().includes("foreclosure")
            );
            const penaltyDiscrepancies = fieldComparisons.filter(
              (fc) => (fc.field || "").toLowerCase().includes("penal") || (fc.field || "").toLowerCase().includes("bounce") || (fc.field || "").toLowerCase().includes("default")
            );
            const feeDiscrepancies = fieldComparisons.filter(
              (fc) => (fc.field || "").toLowerCase().includes("fee") || (fc.field || "").toLowerCase().includes("charge") || (fc.field || "").toLowerCase().includes("processing")
            );

            return (
              <div className="space-y-6">
                {/* Discrepancy Overview Header */}
                <Panel
                  title="Critical Contractual Discrepancies & Disclosures"
                  subtitle="Evidence-backed legal comparison of borrower covenants, penalty triggers, and unilateral lender rights"
                >
                  {conditionalDiscrepancies.length === 0 ? (
                    <div className="py-8 text-center text-muted-foreground text-xs">
                      No significant contractual differences detected across standard operative schedules.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Top Highlights Table */}
                      <div className="w-full overflow-x-auto rounded-xl border border-white/10 bg-surface shadow-sm">
                        <table className="w-full text-xs text-left border-collapse min-w-[500px]">
                          <thead className="bg-white/5 border-b border-white/10 text-white font-semibold">
                            <tr>
                              <th className="py-3 px-4 uppercase tracking-wider text-[11px] text-muted-foreground">Contractual Clause</th>
                              <th className="py-3 px-4">{comparedProducts[0]?.name || "Option 1"} Terms</th>
                              <th className="py-3 px-4">{comparedProducts[1]?.name || "Option 2"} Terms</th>
                              <th className="py-3 px-4 text-right">Legal Assessment</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5">
                            {conditionalDiscrepancies.map((fc, idx) => {
                              const title = (fc.field || "Clause").replace(/_/g, " ");
                              const valA = fc.product_a ? `${fc.product_a.value ?? "Specified"} ${fc.product_a.unit ?? ""}`.trim() : "Not Disclosed";
                              const valB = fc.product_b ? `${fc.product_b.value ?? "Specified"} ${fc.product_b.unit ?? ""}`.trim() : "Not Disclosed";
                              const condA = fc.product_a?.condition;
                              const condB = fc.product_b?.condition;

                              return (
                                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                                  <td className="py-3 px-4 font-semibold text-white capitalize">
                                    {title}
                                    <span className="block text-[10px] text-muted-foreground uppercase mt-0.5">
                                      {categorizeField(fc.field)}
                                    </span>
                                  </td>
                                  <td className="py-3 px-4">
                                    <div className="space-y-1">
                                      <span className={`font-mono text-xs font-semibold px-2 py-0.5 rounded inline-block ${
                                        valA !== "Not Disclosed" ? "text-emerald-300 bg-emerald-950/40 border border-emerald-500/20" : "text-muted-foreground italic bg-surface-2"
                                      }`}>
                                        {valA}
                                      </span>
                                      {condA && (
                                        <p className="text-[11px] text-amber-300/90 leading-tight">
                                          <i className="fa-solid fa-triangle-exclamation mr-1 text-[10px]" />
                                          {condA}
                                        </p>
                                      )}
                                    </div>
                                  </td>
                                  <td className="py-3 px-4">
                                    <div className="space-y-1">
                                      <span className={`font-mono text-xs font-semibold px-2 py-0.5 rounded inline-block ${
                                        valB !== "Not Disclosed" ? "text-blue-300 bg-blue-950/40 border border-blue-500/20" : "text-muted-foreground italic bg-surface-2"
                                      }`}>
                                        {valB}
                                      </span>
                                      {condB && (
                                        <p className="text-[11px] text-amber-300/90 leading-tight">
                                          <i className="fa-solid fa-triangle-exclamation mr-1 text-[10px]" />
                                          {condB}
                                        </p>
                                      )}
                                    </div>
                                  </td>
                                  <td className="py-3 px-4 text-right">
                                    {fc.winner === "product_a" || fc.winner === "A" ? (
                                      <Badge tone="success">✓ {comparedProducts[0]?.name || "Option 1"} More Favorable</Badge>
                                    ) : fc.winner === "product_b" || fc.winner === "B" ? (
                                      <Badge tone="info">✓ {comparedProducts[1]?.name || "Option 2"} More Favorable</Badge>
                                    ) : valA === "Not Disclosed" || valB === "Not Disclosed" ? (
                                      <Badge tone="warning">⚠ Disclosure Gap</Badge>
                                    ) : (
                                      <Badge tone="neutral">Different Terms</Badge>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </Panel>

                {/* Side-by-Side In-Depth Contract Profiles */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {comparedProducts.slice(0, 2).map((p, idx) => {
                    const productFields = fieldComparisons.filter((fc) => (idx === 0 ? fc.product_a : fc.product_b));
                    const conditionsList = productFields
                      .map((fc) => (idx === 0 ? fc.product_a?.condition : fc.product_b?.condition))
                      .filter(Boolean);

                    return (
                      <div
                        key={p.id}
                        className={`rounded-2xl border p-5 space-y-4 shadow-sm ${
                          idx === 0 ? "border-emerald-500/30 bg-surface-2" : "border-blue-500/30 bg-surface-2"
                        }`}
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between border-b border-white/10 pb-3">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
                              Option #{idx + 1} Contract Profile
                            </span>
                            <h4 className="text-base font-bold text-white mt-0.5 flex items-center gap-2">
                              <i className={`fa-solid fa-file-contract text-sm ${idx === 0 ? "text-emerald-400" : "text-blue-400"}`} />
                              {p.name}
                            </h4>
                            <span className="text-xs text-muted-foreground">{p.issuer}</span>
                          </div>
                          <Badge tone={idx === 0 ? "success" : "info"}>
                            {productFields.length} Verified Terms
                          </Badge>
                        </div>

                        {/* Operative Clauses & Active Conditions */}
                        <div className="space-y-3 text-xs">
                          <h5 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            Active Conditions & Exit Rules
                          </h5>

                          {conditionsList.length > 0 ? (
                            <div className="space-y-2">
                              {conditionsList.map((cond, cIdx) => (
                                <div key={cIdx} className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-2.5 text-white/90 leading-relaxed flex items-start gap-2">
                                  <i className="fa-solid fa-triangle-exclamation text-amber-400 text-xs mt-0.5 shrink-0" />
                                  <span>{cond}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-white/70 italic bg-white/[0.02] p-3 rounded-lg border border-white/5">
                              No restrictive conditional riders detected in the verified sections.
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
