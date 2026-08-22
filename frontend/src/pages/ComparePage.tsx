import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Product } from "@/lib/api";
import { PageHeader, Panel, Badge, EmptyState } from "@/components/finex/primitives";

export function ComparePage() {
  const { data: products = [], isLoading } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: api.listProducts,
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectedProducts = products.filter((p) => selectedIds.includes(p.id));

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <PageHeader
        eyebrow="Comparative Analytics"
        title="Product & Loan Comparison"
        description="Benchmark lending terms, interest schedules, prepayment restrictions, and cost structures across multiple financial institutions."
      />

      {/* Product Selector Bar */}
      <Panel title="Select Products to Compare" subtitle="Choose 2 or more products to view comparison matrix">
        {isLoading ? (
          <div className="py-6 flex justify-center">
            <i className="fa-solid fa-spinner fa-spin text-muted-foreground" />
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            title="No products available"
            description="Create products first to enable side-by-side comparison."
          />
        ) : (
          <div className="flex flex-wrap gap-2">
            {products.map((p) => {
              const active = selectedIds.includes(p.id);
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => toggleSelect(p.id)}
                  className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                    active
                      ? "border-transparent bg-white text-black shadow-sm"
                      : "border-white/10 bg-surface-2 text-muted-foreground hover:text-white"
                  }`}
                >
                  {p.name} ({p.issuer})
                </button>
              );
            })}
          </div>
        )}
      </Panel>

      {selectedProducts.length === 0 ? (
        <EmptyState
          icon="fa-solid fa-code-compare"
          title="Select products to generate matrix"
          description="Click on one or more products above to view comparison attributes, interest structures, and risk ratings."
        />
      ) : (
        <Panel title="Comparative Analysis Matrix">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-muted-foreground uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pr-4 font-semibold w-1/4">Evaluation Metric</th>
                  {selectedProducts.map((p) => (
                    <th key={p.id} className="pb-3 pr-4 font-semibold text-white">
                      {p.name}
                      <span className="block font-normal text-muted-foreground text-[10px]">
                        {p.issuer}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Issuing Entity</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4 text-white font-semibold">
                      {p.issuer}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Effective Date</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4 text-white">
                      {p.effective_date || "Standard Schedule"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Audit Status</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4">
                      <Badge tone="success">Active Catalog</Badge>
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Prepayment Terms</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4 text-muted-foreground text-xs italic">
                      Run document analysis to extract verified prepayment terms
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Rate Structure</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4 text-muted-foreground text-xs italic">
                      Run document analysis to extract verified interest rates
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium text-muted-foreground">Verification Status</td>
                  {selectedProducts.map((p) => (
                    <td key={p.id} className="py-3 pr-4">
                      <Badge tone="neutral">Pending Extraction</Badge>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
