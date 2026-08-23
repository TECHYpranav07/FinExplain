import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/authContext";
import { GlobalSearch } from "@/components/finex/GlobalSearch";

const NAV = [
  { to: "/app", label: "Dashboard", icon: "fa-solid fa-gauge-high", exact: true },
  { to: "/app/documents", label: "Documents", icon: "fa-regular fa-file-lines" },
  { to: "/app/query", label: "Ask AI", icon: "fa-solid fa-magnifying-glass" },
  { to: "/app/review", label: "Review", icon: "fa-solid fa-shield-halved" },
  { to: "/app/before-confirmation", label: "Before Confirm", icon: "fa-regular fa-circle-check" },
  { to: "/app/products", label: "Products", icon: "fa-solid fa-layer-group" },
  { to: "/app/compare", label: "Compare", icon: "fa-solid fa-code-compare" },
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

function UserAvatar({
  user,
  size = "md",
  className,
}: {
  user: any;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const [imgError, setImgError] = useState(false);

  const displayName = user?.name || user?.email?.split("@")[0] || "User";
  const initials = (() => {
    if (user?.name) {
      const parts = user.name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
      }
      return user.name.slice(0, 2).toUpperCase();
    }
    if (user?.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    return "U";
  })();

  const sizeClasses = {
    sm: "h-6 w-6 text-[10px]",
    md: "h-8 w-8 text-xs",
    lg: "h-10 w-10 text-sm",
  }[size];

  if (user?.picture && !imgError) {
    return (
      <img
        src={user.picture}
        alt={displayName}
        onError={() => setImgError(true)}
        className={cn(
          sizeClasses,
          "rounded-full object-cover border border-white/20 shrink-0",
          className
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        sizeClasses,
        "flex items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/30 to-purple-600/30 border border-white/15 text-white font-semibold shrink-0 select-none shadow-sm",
        className
      )}
      title={displayName}
    >
      {initials}
    </div>
  );
}

export function AppShell() {
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  const displayName = user?.name || (user?.email ? user.email.split("@")[0] : "User");
  const displayEmail = user?.email || "";

  useEffect(() => setDrawer(false), [location.pathname]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  return (
    <div className="min-h-screen bg-black text-white selection:bg-white/20">
      {/* Sidebar (Desktop - Fixed 256px Full Viewport Height) */}
      <aside className="fixed inset-y-0 left-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/10 bg-sidebar lg:flex z-30">
        {/* Brand Header with fixed h-16 aligned with Top Navbar */}
        <div className="h-16 flex items-center px-5 border-b border-white/10 shrink-0">
          <Link to="/" className="flex items-center gap-3 group">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-xs font-bold text-black tracking-tight group-hover:scale-105 transition-transform shadow-sm">
              Fx
            </span>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight text-white leading-tight">FinExplain</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest leading-tight">Enterprise</span>
            </div>
          </Link>
        </div>

        {/* Scrollable Navigation */}
        <div className="flex-1 overflow-y-auto py-3">
          <NavList />
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="border-t border-white/10 p-4 space-y-3 bg-surface/40 shrink-0">
          {/* User Preview */}
          <div className="flex items-center gap-2.5 px-1">
            <UserAvatar user={user} size="md" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">
                {displayName}
              </p>
              {displayEmail && (
                <p className="truncate text-[10px] text-muted-foreground">
                  {displayEmail}
                </p>
              )}
            </div>
          </div>

          {/* Logout Button */}
          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-400 hover:bg-rose-500/20 hover:border-rose-500/40 hover:text-rose-300 transition-all shadow-sm group"
          >
            <i className="fa-solid fa-arrow-right-from-bracket text-[11px] group-hover:-translate-x-0.5 transition-transform" aria-hidden="true" />
            <span>Sign Out</span>
          </button>

          {/* Status & Version */}
          <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground pt-1 border-t border-white/5">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              API Connected
            </span>
            <Link to="/app/settings" className="text-white/40 hover:text-white transition-colors">v1.0</Link>
          </div>
        </div>
      </aside>

      {/* Main Content Area (Offset by fixed sidebar on large screens) */}
      <div className="flex min-w-0 flex-1 flex-col min-h-screen lg:pl-64 bg-black">
        {/* Top Navbar with fixed h-16 and identical content grid alignment */}
        <header className="sticky top-0 z-20 h-16 w-full border-b border-white/10 bg-black/90 backdrop-blur-md shrink-0">
          <div className="mx-auto flex h-full w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-3 lg:hidden">
              <button
                type="button"
                aria-label="Open navigation"
                onClick={() => setDrawer(true)}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-surface text-white"
              >
                <i className="fa-solid fa-bars text-xs" aria-hidden="true" />
              </button>
              <Link to="/" className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white text-[11px] font-bold text-black">
                  Fx
                </span>
                <span className="text-sm font-semibold text-white">FinExplain</span>
              </Link>
            </div>

            <div className="hidden max-w-md flex-1 md:block">
              <GlobalSearch />
            </div>

            <div className="flex items-center gap-3">
              <Link
                to="/app/settings"
                aria-label="Settings"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-surface text-muted-foreground transition-colors hover:text-white hover:border-white/20"
              >
                <i className="fa-solid fa-sliders text-xs" aria-hidden="true" />
              </Link>

              {/* User Profile Header Chip */}
              <div className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-surface px-3 py-1.5 shadow-sm">
                <UserAvatar user={user} size="sm" />
                <span className="hidden text-xs font-medium text-white/90 sm:block truncate max-w-[150px]">
                  {displayName}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content sharing the exact same max-w-7xl px-4 sm:px-6 lg:px-8 grid */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
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

            {/* Mobile Drawer Logout & User Profile */}
            <div className="border-t border-white/10 p-4 space-y-3 bg-surface/40">
              <div className="flex items-center gap-2.5">
                <UserAvatar user={user} size="md" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-white">
                    {displayName}
                  </p>
                  {displayEmail && (
                    <p className="truncate text-[10px] text-muted-foreground">
                      {displayEmail}
                    </p>
                  )}
                </div>
              </div>


              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-400 hover:bg-rose-500/20 hover:border-rose-500/40 hover:text-rose-300 transition-all shadow-sm"
              >
                <i className="fa-solid fa-arrow-right-from-bracket text-[11px]" aria-hidden="true" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
