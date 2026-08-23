import React, { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { listDocuments, type DocRecord } from "@/lib/documents";
import {
  Search,
  FileText,
  Building2,
  Sparkles,
  ArrowRight,
  Sliders,
  Scale,
  ShieldCheck,
  X,
  CornerDownLeft,
} from "lucide-react";

interface SearchResultItem {
  id: string;
  title: string;
  subtitle?: string;
  category: "documents" | "products" | "ask" | "pages";
  icon: React.ElementType;
  url: string;
  badge?: string;
}

const STATIC_PAGE_ACTIONS: SearchResultItem[] = [
  {
    id: "nav-ask",
    title: "Ask AI Precision Chat",
    subtitle: "Ask questions and verify loan clauses against evidence",
    category: "pages",
    icon: Sparkles,
    url: "/app/query",
    badge: "AI Tool",
  },
  {
    id: "nav-documents",
    title: "Documents Library",
    subtitle: "Upload, chunk, inspect, and analyze loan agreements",
    category: "pages",
    icon: FileText,
    url: "/app/documents",
    badge: "Library",
  },
  {
    id: "nav-compare",
    title: "Scenario Simulator & Loan Compare",
    subtitle: "Side-by-side term matrix & live amortization simulator",
    category: "pages",
    icon: Scale,
    url: "/app/compare",
    badge: "Simulator",
  },
  {
    id: "nav-before-confirm",
    title: "Before Confirmation Action Brief",
    subtitle: "Pre-signing borrower checklist and lender negotiation questions",
    category: "pages",
    icon: ShieldCheck,
    url: "/app/before-confirmation",
    badge: "Audit",
  },
  {
    id: "nav-products",
    title: "Products & Lenders Catalog",
    subtitle: "Manage credit facilities, issuers, and effective dates",
    category: "pages",
    icon: Building2,
    url: "/app/products",
    badge: "Catalog",
  },
  {
    id: "nav-settings",
    title: "Settings & Configuration",
    subtitle: "Manage tenant preferences, API tokens, and local cache",
    category: "pages",
    icon: Sliders,
    url: "/app/settings",
    badge: "System",
  },
];

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fetch live products
  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: api.listProducts,
    staleTime: 30_000,
  });

  // Fetch local document records
  const documents: DocRecord[] = useMemo(() => {
    return listDocuments();
  }, [isOpen]);

  // Compute matched items
  const results: SearchResultItem[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return STATIC_PAGE_ACTIONS.slice(0, 4);
    }

    const items: SearchResultItem[] = [];

    // 1. Direct Ask AI Prompt Action
    items.push({
      id: `ask-${q}`,
      title: `Ask AI: "${query.trim()}"`,
      subtitle: "Query credit documents with evidence grounding & citation verification",
      category: "ask",
      icon: Sparkles,
      url: `/app/query?q=${encodeURIComponent(query.trim())}`,
      badge: "AI Action",
    });

    // 2. Filter Documents
    const matchedDocs = documents.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        (d.productName && d.productName.toLowerCase().includes(q))
    );
    matchedDocs.slice(0, 3).forEach((d) => {
      items.push({
        id: `doc-${d.id}`,
        title: d.name,
        subtitle: `${d.productName || "Document"} · ${d.chunks || 0} chunks · ${d.status}`,
        category: "documents",
        icon: FileText,
        url: `/app/documents/${d.id}`,
        badge: "Document",
      });
    });

    // 3. Filter Products
    const matchedProducts = products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.issuer && p.issuer.toLowerCase().includes(q))
    );
    matchedProducts.slice(0, 3).forEach((p) => {
      items.push({
        id: `prod-${p.id}`,
        title: p.name,
        subtitle: p.issuer ? `${p.issuer} · Product Offer` : "Financial Product",
        category: "products",
        icon: Building2,
        url: `/app/products/${p.id}`,
        badge: "Product",
      });
    });

    // 4. Filter Pages & Tools
    const matchedPages = STATIC_PAGE_ACTIONS.filter(
      (page) =>
        page.title.toLowerCase().includes(q) ||
        (page.subtitle && page.subtitle.toLowerCase().includes(q))
    );
    matchedPages.forEach((p) => items.push(p));

    return items;
  }, [query, documents, products]);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen(true);
        setTimeout(() => inputRef.current?.focus(), 50);
      } else if (e.key === "Escape") {
        setIsOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Reset selection index when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  const handleSelect = (item: SearchResultItem) => {
    setIsOpen(false);
    setQuery("");
    navigate(item.url);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + results.length) % results.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[selectedIndex]) {
        handleSelect(results[selectedIndex]);
      } else if (query.trim()) {
        handleSelect({
          id: "enter-ask",
          title: query.trim(),
          category: "ask",
          icon: Sparkles,
          url: `/app/query?q=${encodeURIComponent(query.trim())}`,
        });
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      {/* Search Input Box */}
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          ref={inputRef}
          type="search"
          aria-label="Search workspace"
          value={query}
          onFocus={() => setIsOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onKeyDown={handleInputKeyDown}
          placeholder="Search documents, products, or ask AI..."
          className="w-full rounded-xl border border-white/15 bg-[#171717] py-2 pl-9 pr-14 text-xs text-white placeholder:text-muted-foreground focus:border-white/40 focus:bg-[#1a1a1a] focus:outline-none transition-all shadow-md"
        />
        
        {/* Clear or Shortcut Badge */}
        {query ? (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white p-0.5 rounded"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : (
          <kbd className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:inline-flex items-center gap-0.5 rounded border border-white/15 bg-white/10 px-1.5 py-0.5 text-[10px] font-mono text-white/60">
            <span>⌘</span>K
          </kbd>
        )}
      </div>

      {/* Floating Results Dropdown Popover (Solid Opaque Background) */}
      {isOpen && (
        <div className="absolute left-0 right-0 top-full mt-2 rounded-2xl border border-white/20 bg-[#141414] p-2.5 shadow-[0_20px_60px_rgba(0,0,0,0.95)] z-50 animate-in fade-in zoom-in-95 duration-150 max-h-96 overflow-y-auto">
          {results.length > 0 ? (
            <div className="space-y-1">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between border-b border-white/10 pb-1.5 mb-1.5">
                <span>{query ? "Matching Results" : "Quick Actions & Navigation"}</span>
                <span className="text-[9px] text-white/50 lowercase">press ↵ to open</span>
              </div>

              {results.map((item, index) => {
                const Icon = item.icon;
                const isSelected = index === selectedIndex;

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelect(item)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`w-full flex items-center justify-between gap-3 rounded-xl p-2.5 text-left transition-all ${
                      isSelected
                        ? "bg-white/15 text-white shadow-sm border border-white/10"
                        : "hover:bg-white/10 text-white/80 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <div
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                          item.category === "ask"
                            ? "bg-primary/25 text-primary-light border border-primary/30"
                            : item.category === "documents"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : item.category === "products"
                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                : "bg-white/10 text-white/90"
                        }`}
                      >
                        <Icon className="h-3.5 w-3.5" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-white truncate">
                            {item.title}
                          </span>
                          {item.badge && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded font-medium bg-white/10 text-white/70">
                              {item.badge}
                            </span>
                          )}
                        </div>
                        {item.subtitle && (
                          <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                            {item.subtitle}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 text-muted-foreground shrink-0">
                      {isSelected ? (
                        <CornerDownLeft className="h-3 w-3 text-white" />
                      ) : (
                        <ArrowRight className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-muted-foreground">
              No matching documents, products, or actions found for "{query}".
            </div>
          )}
        </div>
      )}
    </div>
  );
}
