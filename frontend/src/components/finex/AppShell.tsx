import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/app", label: "Dashboard", icon: "fa-solid fa-gauge-high", exact: true },
  { to: "/app/documents", label: "Documents", icon: "fa-regular fa-file-lines" },
  { to: "/app/query", label: "Ask AI", icon: "fa-solid fa-magnifying-glass" },
  { to: "/app/review", label: "Review", icon: "fa-solid fa-shield-halved" },
  { to: "/app/before-confirmation", label: "Before Confirm", icon: "fa-regular fa-circle-check" },
  { to: "/app/products", label: "Products", icon: "fa-solid fa-layer-group" },
  { to: "/app/compare", label: "Compare", icon: "fa-solid fa-code-compare" },
  { to: "/app/hitl", label: "HITL Review", icon: "fa-solid fa-user-check" },
  { to: "/app/feedback", label: "Feedback", icon: "fa-regular fa-comment-dots" },
  { to: "/app/settings", label: "Settings", icon: "fa-solid fa-sliders" },
];

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  return (
    <nav className="flex flex-col gap-1 p-3" aria-label="Application Navigation">
      {NAV.map((item) => {
        const active = item.exact
          ? location.pathname === item.to
          : location.pathname.startsWith(item.to);
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              active
                ? "bg-surface-3 text-white shadow-sm font-semibold"
                : "text-muted-foreground hover:bg-surface-2 hover:text-white"
            )}
          >
            <i className={cn(item.icon, "w-4 text-center text-[12px]", active ? "text-white" : "text-muted-foreground")} aria-hidden="true" />
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}

export function AppShell() {
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();

  useEffect(() => setDrawer(false), [location.pathname]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  return (
    <div className="flex min-h-screen bg-black text-white">
      {/* Sidebar (Desktop) */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-white/10 bg-sidebar lg:flex">
        <Link to="/" className="flex items-center gap-2.5 px-5 py-5 group">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-xs font-bold text-black tracking-tight group-hover:scale-105 transition-transform">
            Fx
          </span>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight text-white">FinExplain</span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Enterprise</span>
          </div>
        </Link>

        <div className="border-t border-white/10" />

        <div className="flex-1 overflow-y-auto py-2">
          <NavList />
        </div>

        <div className="border-t border-white/10 p-4">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              API Connected
            </span>
            <Link to="/app/settings" className="hover:text-white transition-colors">v1.0</Link>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-white/10 bg-black/80 px-4 py-3 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Open navigation"
              onClick={() => setDrawer(true)}
              className="flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-surface text-white lg:hidden"
            >
              <i className="fa-solid fa-bars text-xs" aria-hidden="true" />
            </button>
            <Link to="/" className="flex items-center gap-2 lg:hidden">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-[11px] font-bold text-black">
                Fx
              </span>
              <span className="text-sm font-semibold text-white">FinExplain</span>
            </Link>
          </div>

          <div className="relative hidden max-w-sm flex-1 md:block">
            <i
              className="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[11px] text-muted-foreground"
              aria-hidden="true"
            />
            <input
              type="search"
              aria-label="Search workspace"
              placeholder="Search documents, products, terms..."
              className="w-full rounded-md border border-white/10 bg-surface py-1.5 pl-8 pr-3 text-xs text-white placeholder:text-muted-foreground focus:border-white/30 focus:outline-none transition-colors"
            />
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              to="/app/query"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-white text-black px-3.5 py-1.5 text-xs font-semibold hover:bg-white/90 transition-colors"
            >
              <i className="fa-solid fa-sparkles text-[10px]" />
              <span>Ask AI</span>
            </Link>
            
            <Link
              to="/app/settings"
              aria-label="Settings"
              className="flex h-8 w-8 items-center justify-center rounded-md border border-white/10 bg-surface text-muted-foreground transition-colors hover:text-white"
            >
              <i className="fa-solid fa-sliders text-xs" aria-hidden="true" />
            </Link>

            <div className="flex items-center gap-2 rounded-md border border-white/10 bg-surface px-2.5 py-1">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-surface-3 text-[10px] font-semibold text-white">
                CR
              </span>
              <span className="hidden text-xs text-muted-foreground sm:block">Credit Analyst</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setDrawer(false)}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="absolute inset-y-0 left-0 w-64 border-r border-white/10 bg-sidebar flex flex-col"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-[11px] font-bold text-black">
                  Fx
                </span>
                <span className="text-sm font-semibold text-white">FinExplain</span>
              </div>
              <button
                type="button"
                aria-label="Close navigation"
                onClick={() => setDrawer(false)}
                className="flex h-8 w-8 items-center justify-center rounded-md border border-white/10 text-muted-foreground hover:text-white"
              >
                <i className="fa-solid fa-xmark text-xs" aria-hidden="true" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <NavList onNavigate={() => setDrawer(false)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
