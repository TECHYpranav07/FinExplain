import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/lib/authContext";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ─────────────── Tab definitions ─────────────── */
const TABS = [
  { key: "overview", label: "Overview", icon: "fa-solid fa-chart-pie" },
  { key: "users", label: "Users", icon: "fa-solid fa-users" },
  { key: "documents", label: "Documents", icon: "fa-regular fa-file-lines" },
  { key: "products", label: "Products", icon: "fa-solid fa-layer-group" },
  { key: "hitl", label: "HITL Tasks", icon: "fa-solid fa-user-check" },
  { key: "feedback", label: "Feedback", icon: "fa-regular fa-comment-dots" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

/* ─────────────── Helpers ─────────────── */
function StatusDot({ status }: { status: string }) {
  const color =
    status === "ok" || status === "configured"
      ? "bg-emerald-400"
      : status === "degraded" || status === "local" || status === "unavailable"
        ? "bg-amber-400"
        : "bg-rose-400";
  return <span className={cn("inline-block h-2 w-2 rounded-full", color)} />;
}

function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: "default" | "admin" | "pending" | "resolved" | "processing" | "completed" | "destructive" }) {
  const cls: Record<string, string> = {
    default: "bg-white/10 text-white/70 border-white/10",
    admin: "bg-violet-500/20 text-violet-300 border-violet-500/30",
    pending: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    resolved: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    processing: "bg-sky-500/20 text-sky-300 border-sky-500/30",
    completed: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    destructive: "bg-rose-500/20 text-rose-300 border-rose-500/30",
  };
  return (
    <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium", cls[variant] || cls.default)}>
      {children}
    </span>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number | string; icon: string; color: string }) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/10 bg-surface p-5 transition-all hover:border-white/20 hover:bg-surface-2">
      <div className={cn("absolute -right-3 -top-3 h-16 w-16 rounded-full opacity-10 blur-lg transition-opacity group-hover:opacity-20", color)} />
      <div className="flex items-center gap-4">
        <div className={cn("flex h-11 w-11 items-center justify-center rounded-xl text-sm", color.replace("bg-", "bg-").replace("500", "500/15"))}>
          <i className={cn(icon, color.replace("bg-", "text-"))} />
        </div>
        <div>
          <p className="text-2xl font-bold text-white tracking-tight">{typeof value === "number" ? value.toLocaleString() : value}</p>
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  );
}

function ConfirmModal({ title, message, onConfirm, onCancel }: { title: string; message: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-xl border border-white/15 bg-[#141418] p-6 shadow-2xl">
        <h3 className="text-sm font-semibold text-white mb-2">{title}</h3>
        <p className="text-xs text-muted-foreground mb-5">{message}</p>
        <div className="flex items-center justify-end gap-2">
          <button onClick={onCancel} className="rounded-lg border border-white/10 bg-surface px-4 py-2 text-xs font-medium text-white/70 hover:bg-surface-2 transition-colors">
            Cancel
          </button>
          <button onClick={onConfirm} className="rounded-lg border border-rose-500/30 bg-rose-500/15 px-4 py-2 text-xs font-medium text-rose-300 hover:bg-rose-500/25 transition-colors">
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── Overview Tab ─────────────── */
function OverviewTab({ stats, health }: { stats: Record<string, number> | null; health: any }) {
  const statItems = [
    { label: "Total Users", value: stats?.total_users ?? 0, icon: "fa-solid fa-users", color: "bg-violet-500" },
    { label: "Products", value: stats?.total_products ?? 0, icon: "fa-solid fa-layer-group", color: "bg-sky-500" },
    { label: "Documents", value: stats?.total_documents ?? 0, icon: "fa-regular fa-file-lines", color: "bg-emerald-500" },
    { label: "Chunks", value: stats?.total_chunks ?? 0, icon: "fa-solid fa-puzzle-piece", color: "bg-amber-500" },
    { label: "HITL Pending", value: stats?.pending_hitl_tasks ?? 0, icon: "fa-solid fa-clock", color: "bg-orange-500" },
    { label: "HITL Resolved", value: stats?.resolved_hitl_tasks ?? 0, icon: "fa-solid fa-circle-check", color: "bg-teal-500" },
    { label: "Feedback", value: stats?.total_feedback ?? 0, icon: "fa-regular fa-comment-dots", color: "bg-pink-500" },
    { label: "Scenarios", value: stats?.total_scenarios ?? 0, icon: "fa-solid fa-calculator", color: "bg-indigo-500" },
  ];

  return (
    <div className="space-y-8">
      {/* Stat Cards Grid */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-4">Platform Statistics</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statItems.map((s) => (
            <StatCard key={s.label} {...s} />
          ))}
        </div>
      </div>

      {/* System Health */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-4">System Health</h3>
        {health ? (
          <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
            <div className="flex items-center gap-3 border-b border-white/10 px-5 py-3">
              <StatusDot status={health.status} />
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                {health.status === "ok" ? "All Systems Operational" : "Degraded Performance"}
              </span>
              <span className="text-[10px] text-muted-foreground ml-auto">
                Env: {health.environment}
              </span>
            </div>
            <div className="divide-y divide-white/5">
              {health.checks &&
                Object.entries(health.checks).map(([name, check]: [string, any]) => (
                  <div key={name} className="flex items-center justify-between px-5 py-3 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3">
                      <StatusDot status={check.status} />
                      <span className="text-xs font-medium text-white capitalize">{name}</span>
                    </div>
                    <span className="text-[11px] text-muted-foreground max-w-xs truncate">{check.detail}</span>
                  </div>
                ))}
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 bg-surface p-6 text-center text-xs text-muted-foreground">
            Loading health status...
          </div>
        )}
      </div>
    </div>
  );
}

/* ─────────────── Users Tab ─────────────── */
function UsersTab() {
  const [users, setUsers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState<{ type: "delete" | "role"; userId: string; newRole?: string } | null>(null);

  const fetchUsers = useCallback(async (s?: string) => {
    setLoading(true);
    try {
      const res = await api.adminUsers({ limit: 100, search: s || undefined });
      setUsers(res.users || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      console.error("Failed to load users", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleSearch = () => fetchUsers(search);

  const handleAction = async () => {
    if (!confirm) return;
    try {
      if (confirm.type === "delete") {
        await api.adminDeleteUser(confirm.userId);
      } else if (confirm.type === "role" && confirm.newRole) {
        await api.adminUpdateRole(confirm.userId, confirm.newRole);
      }
      setConfirm(null);
      fetchUsers(search);
    } catch (e: any) {
      alert(e.message || "Action failed");
      setConfirm(null);
    }
  };

  return (
    <div className="space-y-4">
      {confirm && (
        <ConfirmModal
          title={confirm.type === "delete" ? "Delete User" : "Change Role"}
          message={
            confirm.type === "delete"
              ? "This will permanently delete this user account. This cannot be undone."
              : `Change this user's role to "${confirm.newRole}"?`
          }
          onConfirm={handleAction}
          onCancel={() => setConfirm(null)}
        />
      )}

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <i className="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-[11px]" />
          <input
            type="text"
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-full rounded-lg border border-white/10 bg-surface py-2 pl-9 pr-3 text-xs text-white placeholder:text-muted-foreground focus:border-white/20 focus:outline-none"
          />
        </div>
        <button onClick={handleSearch} className="rounded-lg border border-white/10 bg-surface px-4 py-2 text-xs font-medium text-white hover:bg-surface-2 transition-colors">
          Search
        </button>
        <span className="text-[11px] text-muted-foreground ml-auto">{total} total users</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Email</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Name</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Role</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Created</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-xs text-muted-foreground">Loading users...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-xs text-muted-foreground">No users found</td></tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-white font-medium">{u.email}</td>
                    <td className="px-4 py-3 text-xs text-white/70">{u.full_name || "—"}</td>
                    <td className="px-4 py-3">
                      <Badge variant={u.role === "admin" ? "admin" : "default"}>
                        {u.role || "user"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[11px] text-muted-foreground">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() =>
                            setConfirm({
                              type: "role",
                              userId: u.id,
                              newRole: u.role === "admin" ? "user" : "admin",
                            })
                          }
                          className="rounded-md border border-white/10 bg-surface-2 px-2.5 py-1 text-[10px] font-medium text-white/60 hover:text-white hover:border-white/20 transition-colors"
                          title={u.role === "admin" ? "Demote to user" : "Promote to admin"}
                        >
                          <i className={cn("fa-solid mr-1", u.role === "admin" ? "fa-arrow-down" : "fa-arrow-up")} />
                          {u.role === "admin" ? "Demote" : "Promote"}
                        </button>
                        <button
                          onClick={() => setConfirm({ type: "delete", userId: u.id })}
                          className="rounded-md border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-[10px] font-medium text-rose-400 hover:bg-rose-500/20 transition-colors"
                        >
                          <i className="fa-solid fa-trash mr-1" />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── Documents Tab ─────────────── */
function DocumentsTab() {
  const [docs, setDocs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.adminDocuments({ limit: 100 });
      setDocs(res.documents || []);
      setTotal(res.total || 0);
    } catch (e) {
      console.error("Failed to load documents", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  const handleDelete = async () => {
    if (!confirm) return;
    try {
      await api.adminDeleteDocument(confirm);
      setConfirm(null);
      fetchDocs();
    } catch (e: any) {
      alert(e.message);
      setConfirm(null);
    }
  };

  const statusVariant = (s: string) => {
    if (s === "completed" || s === "processed") return "completed";
    if (s === "processing") return "processing";
    if (s === "failed") return "destructive";
    return "default";
  };

  return (
    <div className="space-y-4">
      {confirm && (
        <ConfirmModal
          title="Delete Document"
          message="This will permanently delete this document and all its chunks. This cannot be undone."
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">All Documents</h3>
        <span className="text-[11px] text-muted-foreground">{total} total</span>
      </div>

      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">File Name</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Product</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Pages</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Uploaded</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-xs text-muted-foreground">Loading documents...</td></tr>
              ) : docs.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-xs text-muted-foreground">No documents found</td></tr>
              ) : (
                docs.map((d) => (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-white font-medium max-w-[200px] truncate" title={d.file_name}>
                      <i className="fa-regular fa-file-pdf text-rose-400 mr-2" />
                      {d.file_name}
                    </td>
                    <td className="px-4 py-3 text-xs text-white/70">{d.product_name || d.product_id?.slice(0, 8) || "—"}</td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{d.total_pages || 0}</td>
                    <td className="px-4 py-3 text-[11px] text-muted-foreground">
                      {d.upload_date ? new Date(d.upload_date).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setConfirm(d.id)}
                        className="rounded-md border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-[10px] font-medium text-rose-400 hover:bg-rose-500/20 transition-colors"
                      >
                        <i className="fa-solid fa-trash mr-1" />Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── Products Tab ─────────────── */
function ProductsTab() {
  const [products, setProducts] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [confirm, setConfirm] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.adminProducts({ limit: 100 });
      setProducts(res.products || []);
      setTotal(res.total || 0);
    } catch (e) {
      console.error("Failed to load products", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const handleDelete = async () => {
    if (!confirm) return;
    try {
      await api.adminDeleteProduct(confirm);
      setConfirm(null);
      fetchProducts();
    } catch (e: any) {
      alert(e.message);
      setConfirm(null);
    }
  };

  return (
    <div className="space-y-4">
      {confirm && (
        <ConfirmModal
          title="Delete Product"
          message="This will permanently delete this product and all its documents/chunks. This cannot be undone."
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">All Products</h3>
        <span className="text-[11px] text-muted-foreground">{total} total</span>
      </div>

      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Product Name</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Issuer</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Owner</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Documents</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Created</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-xs text-muted-foreground">Loading products...</td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-xs text-muted-foreground">No products found</td></tr>
              ) : (
                products.map((p) => (
                  <tr key={p.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-white font-medium">{p.name}</td>
                    <td className="px-4 py-3 text-xs text-white/70">{p.issuer || "—"}</td>
                    <td className="px-4 py-3 text-xs text-white/70">{p.owner_email || p.user_id?.slice(0, 8) || "—"}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{p.document_count ?? 0}</td>
                    <td className="px-4 py-3 text-[11px] text-muted-foreground">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setConfirm(p.id)}
                        className="rounded-md border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-[10px] font-medium text-rose-400 hover:bg-rose-500/20 transition-colors"
                      >
                        <i className="fa-solid fa-trash mr-1" />Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── HITL Tasks Tab ─────────────── */
function HitlTab() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");
  const [resolveId, setResolveId] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.adminHitlTasks({ limit: 100, status: filter || undefined });
      setTasks(res.tasks || []);
      setTotal(res.total || 0);
    } catch (e) {
      console.error("Failed to load HITL tasks", e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const handleResolve = async () => {
    if (!resolveId || !resolution.trim()) return;
    try {
      await api.adminResolveHitl(resolveId, { resolution, notes: "Resolved by admin" });
      setResolveId(null);
      setResolution("");
      fetchTasks();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-4">
      {/* Resolve modal */}
      {resolveId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-white/15 bg-[#141418] p-6 shadow-2xl">
            <h3 className="text-sm font-semibold text-white mb-3">Resolve HITL Task</h3>
            <textarea
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="Enter resolution details..."
              rows={4}
              className="w-full rounded-lg border border-white/10 bg-surface p-3 text-xs text-white placeholder:text-muted-foreground focus:border-white/20 focus:outline-none resize-none mb-4"
            />
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => { setResolveId(null); setResolution(""); }} className="rounded-lg border border-white/10 bg-surface px-4 py-2 text-xs font-medium text-white/70 hover:bg-surface-2 transition-colors">
                Cancel
              </button>
              <button
                onClick={handleResolve}
                disabled={!resolution.trim()}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/15 px-4 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/25 transition-colors disabled:opacity-50"
              >
                Resolve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface p-1">
          {["", "pending", "resolved"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-md px-3 py-1.5 text-[11px] font-medium transition-colors",
                filter === f ? "bg-white/10 text-white" : "text-muted-foreground hover:text-white"
              )}
            >
              {f === "" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-muted-foreground ml-auto">{total} tasks</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/10 bg-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Created</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Resolved</th>
                <th className="px-4 py-3 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-xs text-muted-foreground">Loading tasks...</td></tr>
              ) : tasks.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-xs text-muted-foreground">No HITL tasks found</td></tr>
              ) : (
                tasks.map((t) => (
                  <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-xs text-white font-medium">{t.task_type}</td>
                    <td className="px-4 py-3">
                      <Badge variant={t.status === "pending" ? "pending" : "resolved"}>
                        {t.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[11px] text-muted-foreground">
                      {t.created_at ? new Date(t.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-[11px] text-muted-foreground">
                      {t.resolved_at ? new Date(t.resolved_at).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {t.status === "pending" && (
                        <button
                          onClick={() => setResolveId(t.id)}
                          className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                        >
                          <i className="fa-solid fa-check mr-1" />Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─────────────── Feedback Tab ─────────────── */
function FeedbackTab() {
  const [feedback, setFeedback] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api.adminFeedback({ limit: 100 });
        setFeedback(res.feedback || []);
        setTotal(res.total || 0);
      } catch (e) {
        console.error("Failed to load feedback", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">User Feedback</h3>
        <span className="text-[11px] text-muted-foreground">{total} entries</span>
      </div>

      {loading ? (
        <div className="rounded-xl border border-white/10 bg-surface p-8 text-center text-xs text-muted-foreground">
          Loading feedback...
        </div>
      ) : feedback.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-surface p-8 text-center text-xs text-muted-foreground">
          No feedback submitted yet
        </div>
      ) : (
        <div className="space-y-3">
          {feedback.map((f) => (
            <div key={f.id} className="rounded-xl border border-white/10 bg-surface p-4 hover:border-white/15 transition-colors">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-white mb-1">Q: {f.user_query}</p>
                  <p className="text-[11px] text-muted-foreground line-clamp-2">A: {f.final_answer}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {f.confidence_score !== null && f.confidence_score !== undefined && (
                    <Badge variant={f.confidence_score >= 0.7 ? "completed" : f.confidence_score >= 0.4 ? "pending" : "destructive"}>
                      {f.confidence_score >= 0.7 ? "Correct" : f.confidence_score >= 0.4 ? "Partial" : "Incorrect"}
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                <span>{f.created_at ? new Date(f.created_at).toLocaleDateString() : "—"}</span>
                {f.source_citations?.user_feedback && (
                  <span className="text-amber-400">Correction: {f.source_citations.user_feedback}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Main Admin Page
   ═══════════════════════════════════════════════════ */

export function AdminPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [stats, setStats] = useState<Record<string, number> | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, h] = await Promise.all([api.adminStats(), api.adminHealth()]);
        setStats(s);
        setHealth(h);
      } catch (e: any) {
        console.error("Admin data load error:", e);
        setLoadError(e.message || "Failed to load admin data. You may not have admin privileges.");
      }
    })();
  }, []);

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10 mb-5">
          <i className="fa-solid fa-shield-halved text-2xl text-rose-400" />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">Access Denied</h2>
        <p className="text-sm text-muted-foreground max-w-md">{loadError}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-600/20 border border-violet-500/20">
          <i className="fa-solid fa-shield-halved text-lg text-violet-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Admin Panel</h1>
          <p className="text-xs text-muted-foreground">
            Platform administration &middot; Logged in as{" "}
            <span className="text-violet-400 font-medium">{user?.email || "admin"}</span>
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-surface p-1.5 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-xs font-medium transition-all",
              activeTab === tab.key
                ? "bg-white/10 text-white shadow-sm"
                : "text-muted-foreground hover:text-white hover:bg-white/[0.04]"
            )}
          >
            <i className={cn(tab.icon, "text-[11px]")} />
            {tab.label}
            {tab.key === "hitl" && stats && (stats.pending_hitl_tasks || 0) > 0 && (
              <span className="flex h-4 min-w-[16px] items-center justify-center rounded-full bg-amber-500/20 px-1 text-[9px] font-bold text-amber-300">
                {stats.pending_hitl_tasks}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "overview" && <OverviewTab stats={stats} health={health} />}
        {activeTab === "users" && <UsersTab />}
        {activeTab === "documents" && <DocumentsTab />}
        {activeTab === "products" && <ProductsTab />}
        {activeTab === "hitl" && <HitlTab />}
        {activeTab === "feedback" && <FeedbackTab />}
      </div>
    </div>
  );
}
