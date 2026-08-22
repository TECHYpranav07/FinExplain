import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listDocuments, saveDocument, removeDocument, formatBytes, type DocRecord } from "@/lib/documents";
import { useProducts } from "@/components/finex/ProductSelect";
import { PageHeader, Panel, Badge, EmptyState, ErrorState } from "@/components/finex/primitives";

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const { data: products = [] } = useProducts();
  const [docs, setDocs] = useState<DocRecord[]>(() => listDocuments());
  const [search, setSearch] = useState("");
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async ({ file, productId }: { file: File; productId: string }) => {
      return api.uploadDocument(file, productId);
    },
    onSuccess: (res, vars) => {
      const prod = products.find((p) => p.id === vars.productId);
      const newDoc: DocRecord = {
        id: `doc_${Date.now()}`,
        name: vars.file.name,
        productId: vars.productId,
        productName: prod?.name || "General Product",
        uploadedAt: new Date().toISOString(),
        status: "processed",
        chunks: res.chunks_count || 12,
        sizeBytes: vars.file.size,
        message: res.message || "Document parsed and indexed successfully",
      };
      saveDocument(newDoc);
      setDocs(listDocuments());
      setSelectedFile(null);
      setUploadSuccess(`"${vars.file.name}" ingested successfully with ${newDoc.chunks} chunks.`);
      setUploadError(null);
    },
    onError: (err: any) => {
      setUploadError(err.message || "Failed to upload document");
      setUploadSuccess(null);
    },
  });

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) {
      const f = e.dataTransfer.files[0];
      if (!f.name.endsWith(".pdf")) {
        setUploadError("Only PDF documents are supported for financial ingestion.");
        return;
      }
      setSelectedFile(f);
      setUploadError(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a PDF document to upload.");
      return;
    }
    if (!selectedProduct) {
      setUploadError("Please select an associated Financial Product.");
      return;
    }
    uploadMutation.mutate({ file: selectedFile, productId: selectedProduct });
  };

  const handleDelete = (id: string) => {
    removeDocument(id);
    setDocs(listDocuments());
  };

  const filteredDocs = docs.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      (d.productName && d.productName.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Document Management"
        title="Loan Document Library"
        description="Ingest, chunk, embed, and inspect loan agreements, promissory notes, and sanction letters."
      />

      {/* Upload Zone */}
      <Panel
        title="Ingest New Loan Agreement"
        subtitle="Upload standard PDF documents to trigger deterministic chunking, Pinecone vector indexing, and hybrid retrieval."
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Target Product / Lender <span className="text-danger">*</span>
              </label>
              <select
                aria-label="Target Product / Lender"
                value={selectedProduct}
                onChange={(e) => setSelectedProduct(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:border-white/30 focus:outline-none"
              >
                <option value="">Select a registered product...</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.issuer})
                  </option>
                ))}
              </select>
              {products.length === 0 && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  No products found. <Link to="/app/products" className="text-white underline">Add a product</Link> first.
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Selected File
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileChange}
                  className="text-xs text-muted-foreground file:mr-2 file:rounded-md file:border-0 file:bg-surface-3 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-white/20"
                />
              </div>
            </div>
          </div>

          {/* Drag & Drop Box */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleFileDrop}
            className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
              isDragging
                ? "border-white bg-white/5"
                : "border-white/15 bg-surface-2/40 hover:border-white/30"
            }`}
          >
            <i className="fa-solid fa-cloud-arrow-up text-2xl text-muted-foreground mb-2" />
            <p className="text-sm font-semibold text-white">
              {selectedFile ? selectedFile.name : "Drag & Drop loan agreement PDF here"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {selectedFile
                ? `${formatBytes(selectedFile.size)} · Ready to ingest`
                : "Supports standard PDF formats up to 50MB"}
            </p>
          </div>

          {uploadError && <ErrorState message={uploadError} />}
          {uploadSuccess && (
            <div className="rounded-lg border border-success/30 bg-success/10 p-3 text-xs text-success flex items-center gap-2">
              <i className="fa-solid fa-circle-check" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          <div className="flex justify-end gap-3">
            {selectedFile && (
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className="rounded-lg border border-white/10 px-4 py-2 text-xs font-semibold text-muted-foreground hover:text-white"
              >
                Clear
              </button>
            )}
            <button
              type="submit"
              disabled={uploadMutation.isPending || !selectedFile || !selectedProduct}
              className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2 text-xs font-bold text-black hover:bg-white/90 disabled:opacity-40 transition-colors"
            >
              {uploadMutation.isPending ? (
                <>
                  <i className="fa-solid fa-spinner fa-spin text-xs" />
                  <span>Ingesting PDF...</span>
                </>
              ) : (
                <>
                  <i className="fa-solid fa-bolt text-xs" />
                  <span>Ingest & Index Document</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Panel>

      {/* Document Library Table */}
      <Panel
        title="Document Library"
        subtitle={`${filteredDocs.length} documents tracked`}
        action={
          <div className="relative w-64">
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-[11px] text-muted-foreground" />
            <input
              type="search"
              aria-label="Filter documents by name or product"
              placeholder="Filter documents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-md border border-white/10 bg-surface-2 py-1.5 pl-8 pr-3 text-xs text-white focus:border-white/30 focus:outline-none"
            />
          </div>
        }
      >
        {filteredDocs.length === 0 ? (
          <EmptyState
            title="No matching documents"
            description={
              search ? "No documents match your filter query." : "Upload a loan document above to start building your library."
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-muted-foreground uppercase tracking-wider text-[10px]">
                  <th className="pb-3 font-semibold">Document Name</th>
                  <th className="pb-3 font-semibold">Associated Product</th>
                  <th className="pb-3 font-semibold">Size / Chunks</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Uploaded</th>
                  <th className="pb-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="group hover:bg-surface-2/40 transition-colors">
                    <td className="py-3.5 pr-4 font-medium text-white flex items-center gap-2">
                      <i className="fa-regular fa-file-pdf text-danger" />
                      <span className="truncate max-w-xs">{doc.name}</span>
                    </td>
                    <td className="py-3.5 pr-4 text-muted-foreground">{doc.productName || "General"}</td>
                    <td className="py-3.5 pr-4 text-muted-foreground">
                      {formatBytes(doc.sizeBytes)} · {doc.chunks || 0} chunks
                    </td>
                    <td className="py-3.5 pr-4">
                      <Badge tone={doc.status === "processed" ? "success" : "warning"}>
                        {doc.status}
                      </Badge>
                    </td>
                    <td className="py-3.5 pr-4 text-muted-foreground">
                      {new Date(doc.uploadedAt).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 text-right space-x-2">
                      <Link
                        to={`/app/documents/${doc.id}`}
                        className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-xs text-white hover:bg-surface-3 transition-colors"
                      >
                        Inspect
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDelete(doc.id)}
                        className="rounded-md border border-danger/20 bg-danger/10 px-2 py-1 text-xs text-danger hover:bg-danger/20 transition-colors"
                        title="Remove from session"
                      >
                        <i className="fa-solid fa-trash text-[10px]" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
