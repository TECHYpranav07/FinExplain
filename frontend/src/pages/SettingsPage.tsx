import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, getApiBaseUrl, setApiBaseUrl } from "@/lib/api";
import { STORAGE_KEY } from "@/lib/documents";
import { PageHeader, Panel, KeyValue, Badge } from "@/components/finex/primitives";

export function SettingsPage() {
  const [baseUrl, setBaseUrl] = useState(getApiBaseUrl());
  const [savedNotice, setSavedNotice] = useState(false);

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10000,
  });

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    setApiBaseUrl(baseUrl);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
    healthQuery.refetch();
  };

  const handleClearSession = () => {
    if (window.confirm("Clear all locally tracked documents and search history?")) {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem("finexplain.documents");
      window.location.reload();
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <PageHeader
        eyebrow="System Configuration"
        title="Settings & Integrations"
        description="Configure your FastAPI backend endpoints, audit connection health, and manage local analyst storage."
      />

      {/* Backend API Configuration */}
      <Panel title="FastAPI Backend Connection">
        <form onSubmit={handleSaveUrl} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              API Base URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                required
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="flex-1 rounded-lg border border-white/10 bg-surface-2 px-3 py-2 text-xs text-white focus:outline-none focus:border-white/30"
              />
              <button
                type="submit"
                className="rounded-lg bg-white px-4 py-2 text-xs font-bold text-black hover:bg-white/90"
              >
                Save
              </button>
            </div>
          </div>

          {savedNotice && (
            <p className="text-xs text-success flex items-center gap-1.5">
              <i className="fa-solid fa-check" /> Base URL updated successfully.
            </p>
          )}

          <div className="rounded-lg border border-white/10 bg-surface-2 p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`h-3 w-3 rounded-full ${
                  healthQuery.data?.status === "ok" ? "bg-success animate-pulse" : "bg-danger"
                }`}
              />
              <div>
                <p className="text-xs font-semibold text-white">
                  {healthQuery.isLoading
                    ? "Testing connection..."
                    : healthQuery.data?.status === "ok"
                    ? "Backend Connected & Operational"
                    : "Unable to reach FastAPI endpoint"}
                </p>
                <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                  GET {baseUrl}/health
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => healthQuery.refetch()}
              className="rounded-md border border-white/10 bg-surface-3 px-2.5 py-1 text-xs text-white hover:bg-white/10"
            >
              Test Now
            </button>
          </div>
        </form>
      </Panel>

      {/* Architecture & Pipeline Info */}
      <Panel title="Architecture Specifications">
        <div className="space-y-1">
          <KeyValue label="Retrieval Engine" value="Hybrid BM25 + Pinecone Dense Embeddings" />
          <KeyValue label="Reasoning Core" value="Groq LLaMA 3.3 70B / Gemini 2.0 Flash" />
          <KeyValue label="Verification Model" value="Deterministic NLI & Citation Extraction" />
          <KeyValue label="Database Layer" value="Supabase PostgreSQL" />
          <KeyValue label="Task Queue" value="Celery + Redis / Sync Fallback" />
          <KeyValue label="Frontend Stack" value="React 18 + Vite + Tailwind CSS + Lucide" />
        </div>
      </Panel>

      {/* Workspace Maintenance */}
      <Panel title="Local Workspace Data">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-white">Reset Local Session Cache</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Clears local document registry and search history stored in your browser.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClearSession}
            className="rounded-lg border border-danger/30 bg-danger/10 px-3.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger/20"
          >
            Clear Data
          </button>
        </div>
      </Panel>
    </div>
  );
}
