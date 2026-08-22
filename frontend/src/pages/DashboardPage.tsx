import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listDocuments } from "@/lib/documents";
import { loadChatSessions } from "@/lib/chatStorage";
import { PageHeader, Panel, Badge, EmptyState } from "@/components/finex/primitives";

export function DashboardPage() {
  const productsQuery = useQuery({
    queryKey: ["products"],
    queryFn: api.listProducts,
  });

  const docs = listDocuments();
  const products = productsQuery.data || [];
  const sessions = loadChatSessions();
  const totalChunks = docs.reduce((acc, d) => acc + (d.chunks || 0), 0);
  const totalQueries = sessions.reduce(
    (acc, s) => acc + (s.messages || []).filter((m) => m.role === "user").length,
    0
  );

  const quickActions = [
    {
      to: "/app/query",
      title: "Evidence-First Q&A",
      description: "Ask questions against loan agreements with claim citations and verification.",
      icon: "fa-solid fa-wand-magic-sparkles",
      tag: "RAG Engine",
    },
    {
      to: "/app/review",
      title: "Proactive Loan Review",
      description: "Auto-extract hidden fees, prepayment penalties, and high-risk terms.",
      icon: "fa-solid fa-shield-halved",
      tag: "Risk Analysis",
    },
    {
      to: "/app/before-confirmation",
      title: "Before You Confirm",
      description: "Generate lender-facing questions and actionable pre-signing checklists.",
      icon: "fa-regular fa-circle-check",
      tag: "Decision Support",
    },
    {
      to: "/app/documents",
      title: "Document Ingestion",
      description: "Upload PDF loan agreements for chunking, vector embedding, and hybrid indexing.",
      icon: "fa-regular fa-file-pdf",
      tag: "Pipeline",
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Financial Intelligence Console"
        title="Good day, Analyst"
        description="Your enterprise evidence-first workspace for loan agreement auditing and financial risk intelligence."
        action={
          <div className="flex items-center gap-3">
            <Link
              to="/app/documents"
              className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-surface-2 px-3.5 py-2 text-xs font-semibold text-white hover:bg-surface-3 transition-colors"
            >
              <i className="fa-solid fa-upload text-[11px]" />
              <span>Upload Document</span>
            </Link>
            <Link
              to="/app/query"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-xs font-semibold text-black hover:bg-white/90 transition-colors shadow-sm"
            >
              <i className="fa-solid fa-wand-magic-sparkles text-[11px]" />
              <span>Ask AI</span>
            </Link>
          </div>
        }
      />

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Panel className="p-4">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Loan Products</span>
            <i className="fa-solid fa-layer-group text-xs" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {productsQuery.isLoading ? "—" : products.length}
            </span>
            <span className="text-[11px] text-muted-foreground">active in system</span>
          </div>
        </Panel>

        <Panel className="p-4">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Documents Ingested</span>
            <i className="fa-regular fa-file-lines text-xs" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {docs.length}
            </span>
            <span className="text-[11px] text-muted-foreground">in workspace</span>
          </div>
        </Panel>

        <Panel className="p-4">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Extracted Clauses</span>
            <i className="fa-solid fa-fingerprint text-xs" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {totalChunks}
            </span>
            <span className="text-[11px] text-muted-foreground">indexed & verified</span>
          </div>
        </Panel>

        <Panel className="p-4">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium uppercase tracking-wider">Audit Inquiries</span>
            <i className="fa-solid fa-magnifying-glass-chart text-xs" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {totalQueries}
            </span>
            <span className="text-[11px] text-muted-foreground">citation-audited</span>
          </div>
        </Panel>
      </div>


      {/* Quick Workflows */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
          Core Analysis Workflows
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {quickActions.map((action) => (
            <Link
              key={action.to}
              to={action.to}
              className="group rounded-xl border border-white/10 bg-surface p-5 transition-all hover:border-white/25 hover:bg-surface-2 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-surface-3 text-white group-hover:scale-105 transition-transform">
                    <i className={action.icon} />
                  </span>
                  <Badge tone="neutral">{action.tag}</Badge>
                </div>
                <h3 className="text-base font-semibold text-white group-hover:text-white transition-colors">
                  {action.title}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  {action.description}
                </p>
              </div>
              <div className="mt-4 flex items-center gap-1 text-xs font-medium text-white/70 group-hover:text-white">
                <span>Launch workflow</span>
                <i className="fa-solid fa-arrow-right text-[10px] group-hover:translate-x-0.5 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent Documents & Products Split */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Recent Documents"
          subtitle="Documents uploaded and tracked in your active session"
          action={
            <Link to="/app/documents" className="text-xs font-medium text-white hover:underline">
              View all
            </Link>
          }
        >
          {docs.length === 0 ? (
            <EmptyState
              title="No documents yet"
              description="Upload your first loan agreement to begin evidence-first extraction."
              action={
                <Link
                  to="/app/documents"
                  className="rounded-md border border-white/20 bg-surface-2 px-3 py-1.5 text-xs font-medium text-white hover:bg-surface-3"
                >
                  Upload PDF
                </Link>
              }
            />
          ) : (
            <div className="divide-y divide-white/5">
              {docs.slice(0, 4).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <i className="fa-regular fa-file-pdf text-danger text-lg" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{doc.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(doc.uploadedAt).toLocaleDateString()} · {doc.chunks || 0} chunks
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/app/documents/${doc.id}`}
                    className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-muted-foreground hover:text-white hover:border-white/20 transition-colors"
                  >
                    Inspect
                  </Link>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          title="Financial Products"
          subtitle="Entities registered in the Supabase backend"
          action={
            <Link to="/app/products" className="text-xs font-medium text-white hover:underline">
              Manage
            </Link>
          }
        >
          {products.length === 0 ? (
            <EmptyState
              icon="fa-solid fa-layer-group"
              title="No products registered"
              description="Register a financial product or lender to associate loan documents."
              action={
                <Link
                  to="/app/products"
                  className="rounded-md border border-white/20 bg-surface-2 px-3 py-1.5 text-xs font-medium text-white hover:bg-surface-3"
                >
                  Add Product
                </Link>
              }
            />
          ) : (
            <div className="divide-y divide-white/5">
              {products.slice(0, 4).map((prod) => (
                <div key={prod.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-white">{prod.name}</p>
                    <p className="text-xs text-muted-foreground">{prod.issuer}</p>
                  </div>
                  <Link
                    to="/app/query"
                    className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-muted-foreground hover:text-white hover:border-white/20 transition-colors"
                  >
                    Query Product
                  </Link>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
