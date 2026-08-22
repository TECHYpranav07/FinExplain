import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listDocuments } from "@/lib/documents";
import { PageHeader, Panel, KeyValue, Badge, EmptyState } from "@/components/finex/primitives";

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();

  const productQuery = useQuery({
    queryKey: ["product", id],
    queryFn: () => (id ? api.getProduct(id) : Promise.reject("No ID")),
    enabled: Boolean(id),
  });

  const allDocs = listDocuments();
  const associatedDocs = allDocs.filter((d) => d.productId === id);

  const product = productQuery.data;

  if (productQuery.isLoading) {
    return (
      <div className="py-20 flex justify-center">
        <i className="fa-solid fa-spinner fa-spin text-3xl text-white" />
      </div>
    );
  }

  if (productQuery.isError || !product) {
    return (
      <EmptyState
        title="Product Not Found"
        description="Could not find the requested financial product record."
        action={
          <Link to="/app/products" className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black">
            Back to Products
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Financial Product Detail"
        title={product.name}
        description={`Issuer: ${product.issuer} · Product ID: ${product.id}`}
        action={
          <div className="flex items-center gap-3">
            <Link
              to="/app/products"
              className="rounded-lg border border-white/10 bg-surface-2 px-3.5 py-2 text-xs font-semibold text-muted-foreground hover:text-white"
            >
              <i className="fa-solid fa-arrow-left mr-1.5" /> Back
            </Link>
            <Link
              to="/app/query"
              className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90"
            >
              Query This Product
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Panel title="Contract Metadata">
          <div className="space-y-1">
            <KeyValue label="Product Name" value={product.name} />
            <KeyValue label="Issuing Bank / Lender" value={product.issuer} />
            <KeyValue label="Effective Date" value={product.effective_date || "Not specified"} />
            <KeyValue label="Registered On" value={product.created_at ? new Date(product.created_at).toLocaleDateString() : "Active"} />
            <KeyValue label="Product UUID" value={<span className="font-mono text-[11px]">{product.id}</span>} />
          </div>
        </Panel>

        <Panel title="Analysis Actions">
          <div className="space-y-2.5">
            <Link
              to="/app/query"
              className="block rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white hover:border-white/20 transition-colors"
            >
              <div className="font-semibold mb-1 flex items-center gap-2">
                <i className="fa-solid fa-wand-magic-sparkles text-white" />
                <span>Evidence-First Q&A</span>
              </div>
              <p className="text-muted-foreground">Ask questions directly against this contract's ingested clauses.</p>
            </Link>

            <Link
              to="/app/review"
              className="block rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white hover:border-white/20 transition-colors"
            >
              <div className="font-semibold mb-1 flex items-center gap-2">
                <i className="fa-solid fa-shield-halved text-warning" />
                <span>Proactive Risk Review</span>
              </div>
              <p className="text-muted-foreground">Extract cost drivers, penalty conditions, and hazard ratings.</p>
            </Link>

            <Link
              to="/app/before-confirmation"
              className="block rounded-lg border border-white/10 bg-surface-2 p-3 text-xs text-white hover:border-white/20 transition-colors"
            >
              <div className="font-semibold mb-1 flex items-center gap-2">
                <i className="fa-regular fa-circle-check text-success" />
                <span>Before You Confirm</span>
              </div>
              <p className="text-muted-foreground">Generate lender question checklist and verify floating rate risks.</p>
            </Link>
          </div>
        </Panel>
      </div>

      {/* Associated Documents */}
      <Panel
        title="Associated Documents"
        subtitle={`${associatedDocs.length} documents uploaded for this product`}
        action={
          <Link to="/app/documents" className="text-xs text-white underline">
            Upload new
          </Link>
        }
      >
        {associatedDocs.length === 0 ? (
          <EmptyState
            title="No documents linked"
            description="Upload a loan agreement or PDF contract associated with this product."
            action={
              <Link
                to="/app/documents"
                className="rounded-lg bg-white px-3.5 py-1.5 text-xs font-bold text-black"
              >
                Upload Document
              </Link>
            }
          />
        ) : (
          <div className="divide-y divide-white/5">
            {associatedDocs.map((d) => (
              <div key={d.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <i className="fa-regular fa-file-pdf text-danger" />
                  <div>
                    <p className="text-xs font-medium text-white">{d.name}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {new Date(d.uploadedAt).toLocaleDateString()} · {d.chunks || 0} chunks
                    </p>
                  </div>
                </div>
                <Link
                  to={`/app/documents/${d.id}`}
                  className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-white hover:bg-surface-3"
                >
                  Inspect
                </Link>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
