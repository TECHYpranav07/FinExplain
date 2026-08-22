import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type Product } from "@/lib/api";
import { cn } from "@/lib/utils";

export function useProducts() {
  return useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: api.listProducts,
    retry: 1,
  });
}

export function ProductPicker({
  selected,
  onChange,
  multiple = true,
}: {
  selected: string[];
  onChange: (ids: string[]) => void;
  multiple?: boolean;
}) {
  const { data, isLoading, error } = useProducts();

  if (isLoading) return <div className="fx-skeleton h-9 w-full rounded-md" aria-hidden="true" />;
  if (error)
    return (
      <div className="rounded-md border border-danger/20 bg-danger/5 p-3 text-xs text-danger flex items-center justify-between">
        <span>Products unavailable — check backend connection</span>
        <a href="/app/settings" className="underline font-medium hover:text-white">Settings</a>
      </div>
    );
  if (!data?.length)
    return (
      <div className="rounded-md border border-white/10 bg-surface-2 p-3 text-xs text-muted-foreground flex items-center justify-between">
        <span>No products created yet. Create a product first to analyze documents.</span>
        <a href="/app/products" className="text-white underline font-medium">Create Product</a>
      </div>
    );

  const toggle = (id: string) => {
    if (!multiple) return onChange([id]);
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  };

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Select products">
      {data.map((p) => {
        const active = selected.includes(p.id);
        return (
          <button
            key={p.id}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(p.id)}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              active
                ? "border-transparent bg-white text-black font-semibold shadow-sm"
                : "border-white/10 bg-surface-2 text-muted-foreground hover:text-white hover:border-white/20"
            )}
          >
            <span>{p.name}</span>
            <span className={cn("text-[10px]", active ? "text-black/60" : "text-muted-foreground/60")}>
              ({p.issuer})
            </span>
          </button>
        );
      })}
    </div>
  );
}
