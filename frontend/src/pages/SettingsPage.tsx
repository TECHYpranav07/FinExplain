import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/authContext";
import { listDocuments, STORAGE_KEY } from "@/lib/documents";
import { loadChatSessions, clearAllSessions } from "@/lib/chatStorage";
import {
  User,
  Sliders,
  Trash2,
  Download,
  Check,
  CheckCircle2,
  Coins,
  Copy,
  LogOut,
  Save,
  Lock,
  Database,
  Shield,
} from "lucide-react";

export function SettingsPage() {
  const { user, logout } = useAuth();
  const userId = user?.id;

  // Profile Settings State
  const [displayName, setDisplayName] = useState(user?.name || "Credit Analyst");
  const [currency, setCurrency] = useState("INR");
  const [profileSaved, setProfileSaved] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  // Load User Preferences from LocalStorage on mount
  useEffect(() => {
    try {
      const savedPrefs = localStorage.getItem("finexplain_user_preferences");
      if (savedPrefs) {
        const p = JSON.parse(savedPrefs);
        if (p.displayName) setDisplayName(p.displayName);
        if (p.currency) setCurrency(p.currency);
      }
    } catch {
      // Ignore
    }
  }, []);

  const savePreferences = (updated: Record<string, any>) => {
    try {
      const current = JSON.parse(localStorage.getItem("finexplain_user_preferences") || "{}");
      localStorage.setItem("finexplain_user_preferences", JSON.stringify({ ...current, ...updated }));
    } catch {
      // Ignore
    }
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    savePreferences({ displayName, currency });
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2500);
  };

  const handleCopySessionToken = () => {
    const token = localStorage.getItem("finexplain_auth_token") || "anon-session-active";
    navigator.clipboard.writeText(token);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  const handleExportWorkspaceData = () => {
    const docs = listDocuments();
    const chats = loadChatSessions(userId);
    const exportBundle = {
      exportTimestamp: new Date().toISOString(),
      user: { id: user?.id, email: user?.email, name: displayName },
      currency,
      documentsCount: docs.length,
      documents: docs,
      conversationsCount: chats.length,
      conversations: chats,
    };

    const blob = new Blob([JSON.stringify(exportBundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `finexplain_audit_export_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClearLocalSession = () => {
    if (window.confirm("Are you sure you want to delete all local document records, chat history, and cache? This action cannot be undone.")) {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem("finexplain.documents");
      clearAllSessions(userId);
      window.location.reload();
    }
  };

  const docs = listDocuments();
  const chats = loadChatSessions(userId);
  const totalChunks = docs.reduce((acc, d) => acc + (d.chunks || 0), 0);

  return (
    <div className="space-y-8 max-w-4xl pb-16">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Sliders className="h-3.5 w-3.5 text-primary-light" />
          <span>Account Preferences</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
          Settings & Profile
        </h1>
        <p className="text-xs sm:text-sm text-white/70 mt-1 max-w-xl">
          Manage your personal account profile, primary currency preferences, and local document audit data.
        </p>
      </div>

      {/* SECTION 1: USER PROFILE & PREFERENCES */}
      <div className="rounded-2xl border border-white/15 bg-surface-2 p-6 sm:p-7 space-y-6 shadow-sm">
        {/* User Card Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-white/10 border border-white/15 text-xl font-bold text-white shadow-inner">
              {user?.picture ? (
                <img src={user.picture} alt="Profile" className="h-full w-full rounded-2xl object-cover" />
              ) : (
                displayName.charAt(0).toUpperCase() || "U"
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">{displayName}</h3>
                <span className="rounded-md bg-emerald-500/20 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                  Active Session
                </span>
              </div>
              <p className="text-xs text-white/60 mt-0.5">{user?.email || "anonymous@borrower.local"}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-bold text-rose-300 hover:bg-rose-500/20 transition-all"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Sign Out</span>
          </button>
        </div>

        {/* Profile Edit Form */}
        <form onSubmit={handleSaveProfile} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Full Name / Display Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  placeholder="Enter your name"
                  className="w-full rounded-xl border border-white/15 bg-surface py-2.5 pl-9 pr-3 text-xs text-white focus:border-white/40 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Primary Currency
              </label>
              <div className="relative">
                <Coins className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-surface py-2.5 pl-9 pr-3 text-xs text-white focus:border-white/40 focus:outline-none transition-colors"
                >
                  <option value="INR">₹ INR (Indian Rupee - Standard)</option>
                  <option value="USD">$ USD (US Dollar)</option>
                  <option value="EUR">€ EUR (Euro)</option>
                  <option value="GBP">£ GBP (British Pound)</option>
                </select>
              </div>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Workspace Tenant / Session Identifier
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={user?.id || "public-user-workspace"}
                  className="w-full rounded-xl border border-white/15 bg-black/40 p-2.5 text-xs text-white/70 font-mono focus:outline-none cursor-default"
                />
                <button
                  type="button"
                  onClick={handleCopySessionToken}
                  className="rounded-xl border border-white/15 bg-surface px-3 py-2.5 text-xs font-medium text-white hover:bg-white/10 shrink-0 flex items-center gap-1.5 transition-colors"
                  title="Copy Session Token"
                >
                  {copiedToken ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy ID</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            {profileSaved ? (
              <span className="text-xs text-emerald-400 flex items-center gap-1.5 font-medium animate-in fade-in">
                <CheckCircle2 className="h-3.5 w-3.5" /> Preferences saved successfully.
              </span>
            ) : (
              <span className="text-[11px] text-white/50">Preferences are saved to your local workspace.</span>
            )}
            <button
              type="submit"
              className="rounded-xl bg-white px-5 py-2.5 text-xs font-bold text-black hover:bg-white/90 transition-all shadow-sm flex items-center gap-1.5"
            >
              <Save className="h-3.5 w-3.5" />
              <span>Save Preferences</span>
            </button>
          </div>
        </form>
      </div>

      {/* SECTION 2: DATA INVENTORY & PRIVACY */}
      <div className="rounded-2xl border border-white/15 bg-surface-2 p-6 sm:p-7 space-y-6 shadow-sm">
        <div className="border-b border-white/10 pb-4">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary-light" />
            <h3 className="text-base font-bold text-white">Data Storage & Workspace Privacy</h3>
          </div>
          <p className="text-xs text-white/70 mt-0.5">
            Overview of stored documents, conversation histories, and export tools.
          </p>
        </div>

        {/* Inventory Statistics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-white/10 bg-surface p-4">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground block">
              Tracked Documents
            </span>
            <span className="text-2xl font-extrabold text-white mt-1 block">{docs.length}</span>
            <span className="text-[10px] text-white/50">{totalChunks} indexed chunks</span>
          </div>

          <div className="rounded-xl border border-white/10 bg-surface p-4">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground block">
              Chat Conversations
            </span>
            <span className="text-2xl font-extrabold text-white mt-1 block">{chats.length}</span>
            <span className="text-[10px] text-white/50">Stored locally in browser</span>
          </div>

          <div className="rounded-xl border border-white/10 bg-surface p-4">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground block">
              Privacy Mode
            </span>
            <span className="text-2xl font-extrabold text-emerald-400 mt-1 block">Local Vault</span>
            <span className="text-[10px] text-white/50">Client-side isolation</span>
          </div>
        </div>

        {/* Export & Reset Action Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          {/* Export JSON Bundle */}
          <div className="rounded-xl border border-white/15 bg-surface p-5 space-y-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-white font-bold text-xs">
                <Download className="h-4 w-4 text-primary-light" />
                <span>Export Audit History</span>
              </div>
              <p className="text-[11px] text-white/70 mt-1.5 leading-relaxed">
                Download a JSON archive containing all your analyzed agreements, verified loan terms, and chat sessions.
              </p>
            </div>
            <button
              type="button"
              onClick={handleExportWorkspaceData}
              className="w-full rounded-xl border border-white/15 bg-surface-2 p-2.5 text-xs font-bold text-white hover:bg-white/10 transition-all flex items-center justify-center gap-2"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export JSON Archive</span>
            </button>
          </div>

          {/* Reset Workspace Data */}
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-5 space-y-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 text-rose-400 font-bold text-xs">
                <Trash2 className="h-4 w-4" />
                <span>Reset Local Data</span>
              </div>
              <p className="text-[11px] text-white/70 mt-1.5 leading-relaxed">
                Wipe all locally stored documents, conversation history, and temporary cache from this browser.
              </p>
            </div>
            <button
              type="button"
              onClick={handleClearLocalSession}
              className="w-full rounded-xl border border-rose-500/40 bg-rose-500/20 p-2.5 text-xs font-bold text-rose-300 hover:bg-rose-500/30 transition-all flex items-center justify-center gap-2"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Reset All Local Data</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
