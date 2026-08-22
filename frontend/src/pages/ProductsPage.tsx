import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Product } from "@/lib/api";
import { PageHeader, Panel, Badge, EmptyState, ErrorState } from "@/components/finex/primitives";

export function ProductsPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const productsQuery = useQuery({
    queryKey: ["products"],
    queryFn: api.listProducts,
  });

  const createMutation = useMutation({
    mutationFn: async (data: { name: string; issuer: string; effective_date?: string }) => {
      return api.createProduct(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setModalOpen(false);
      setName("");
      setIssuer("");
      setEffectiveDate("");
      setErrorMsg(null);
    },
    onError: (err: any) => {
      setErrorMsg(err.message || "Failed to create product");
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !issuer.trim()) {
      setErrorMsg("Product name and issuer are required.");
      return;
    }
    createMutation.mutate({
      name: name.trim(),
      issuer: issuer.trim(),
      effective_date: effectiveDate || undefined,
    });
  };

  const products = productsQuery.data || [];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Portfolio & Catalog"
        title="Financial Products & Lenders"
        description="Manage financial products, loan agreements, lending institutions, and effective contract terms."
        action={
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2 text-xs font-bold text-black hover:bg-white/90 transition-colors shadow-sm"
          >
            <i className="fa-solid fa-plus text-xs" />
            <span>Add Product</span>
          </button>
        }
      />

      {productsQuery.isError && (
        <ErrorState
          message={(productsQuery.error as any)?.message || "Failed to load products"}
          onRetry={() => productsQuery.refetch()}
        />
      )}

      <Panel
        title="Registered Loan Products"
        subtitle={`${products.length} active products in database`}
      >
        {productsQuery.isLoading ? (
          <div className="py-12 flex justify-center">
            <i className="fa-solid fa-spinner fa-spin text-2xl text-muted-foreground" />
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            icon="fa-solid fa-layer-group"
            title="No products registered yet"
            description="Create a product profile to associate uploaded loan agreements with lender terms."
            action={
              <button
                type="button"
                onClick={() => setModalOpen(true)}
                className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black"
              >
                Create First Product
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-muted-foreground uppercase tracking-wider text-[10px]">
                  <th className="pb-3 font-semibold">Product Name</th>
                  <th className="pb-3 font-semibold">Lender / Issuer</th>
                  <th className="pb-3 font-semibold">Effective Date</th>
                  <th className="pb-3 font-semibold">Product ID</th>
                  <th className="pb-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {products.map((p) => (
                  <tr key={p.id} className="group hover:bg-surface-2/40 transition-colors">
                    <td className="py-3.5 pr-4 font-semibold text-white">
                      <Link to={`/app/products/${p.id}`} className="hover:underline">
                        {p.name}
                      </Link>
                    </td>
                    <td className="py-3.5 pr-4 text-white/90">{p.issuer}</td>
                    <td className="py-3.5 pr-4 text-muted-foreground">
                      {p.effective_date || "Not specified"}
                    </td>
                    <td className="py-3.5 pr-4 font-mono text-[11px] text-muted-foreground">
                      {p.id.slice(0, 8)}...
                    </td>
                    <td className="py-3.5 text-right space-x-2">
                      <Link
                        to={`/app/products/${p.id}`}
                        className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-muted-foreground hover:text-white hover:border-white/20 transition-colors"
                      >
                        Details
                      </Link>
                      <Link
                        to="/app/query"
                        className="rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-black hover:bg-white/90 transition-colors"
                      >
                        Query
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {/* Add Product Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/75 backdrop-blur-sm"
            onClick={() => setModalOpen(false)}
          />
          <div className="relative w-full max-w-md rounded-2xl border border-white/15 bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-white/10">
              <h3 className="text-base font-semibold text-white">Register Financial Product</h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-muted-foreground hover:text-white"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 pt-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Product Name <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. HDFC Commercial Real Estate Term Loan"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-white/30 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Lender / Issuer <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. HDFC Bank Ltd."
                  value={issuer}
                  onChange={(e) => setIssuer(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-white/30 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                  Effective Date (Optional)
                </label>
                <input
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-white/30 focus:outline-none"
                />
              </div>

              {errorMsg && <ErrorState message={errorMsg} />}

              <div className="flex justify-end gap-3 pt-3 border-t border-white/10">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-lg border border-white/10 px-4 py-2 text-xs font-semibold text-muted-foreground hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="rounded-lg bg-white px-5 py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40"
                >
                  {createMutation.isPending ? "Creating..." : "Save Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
